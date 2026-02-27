import os
import re
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

import structlog

from med_paper_assistant.infrastructure.persistence.draft_snapshot_manager import (
    DraftSnapshotManager,
)
from med_paper_assistant.infrastructure.persistence.git_auto_committer import GitAutoCommitter
from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager

if TYPE_CHECKING:
    from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager

logger = structlog.get_logger()


class CitationStyle(Enum):
    VANCOUVER = "vancouver"  # [1] Author. Title. Journal (Year).
    APA = "apa"  # Author (Year). Title. Journal.
    HARVARD = "harvard"  # Author (Year) 'Title', Journal.
    NATURE = "nature"  # 1. Author. Title. Journal Year.
    AMA = "ama"  # 1. Author. Title. Journal. Year.
    MDPI = "mdpi"  # 1. Author. Title. Journal Year, Volume, Page.
    NLM = "nlm"  # National Library of Medicine style


# Journal-specific citation format configurations
JOURNAL_CITATION_CONFIGS = {
    "sensors": {
        "style": "mdpi",
        "format": "{number}. {authors}. {title}. {journal} {year}, {volume}, {pages}.",
        "author_format": "last_initials",  # "Kim, S.H.; Lee, J.W."
        "max_authors": 6,
        "et_al_threshold": 6,
    },
    "lancet": {
        "style": "vancouver",
        "format": "{number} {authors}. {title}. {journal} {year}; {volume}: {pages}.",
        "author_format": "full_first",  # "Kim SH, Lee JW"
        "max_authors": 6,
        "et_al_threshold": 3,
    },
    "bja": {  # British Journal of Anaesthesia
        "style": "vancouver",
        "format": "{number}. {authors}. {title}. {journal} {year}; {volume}: {pages}.",
        "author_format": "last_initials_space",  # "Kim S H, Lee J W"
        "max_authors": 6,
        "et_al_threshold": 6,
    },
    "anesthesiology": {
        "style": "ama",
        "format": "{number}. {authors}. {title}. {journal}. {year};{volume}:{pages}.",
        "author_format": "last_initials",
        "max_authors": 6,
        "et_al_threshold": 6,
    },
    "default": {
        "style": "vancouver",
        "format": "[{number}] {authors}. {title}. {journal} ({year}). PMID:{pmid}.",
        "author_format": "full",
        "max_authors": 10,
        "et_al_threshold": 3,
    },
}


class Drafter:
    def __init__(
        self,
        reference_manager: ReferenceManager,
        drafts_dir: str = "drafts",
        citation_style: str = CitationStyle.VANCOUVER.value,
        project_manager: Optional["ProjectManager"] = None,
    ):
        """
        Initialize the Drafter.

        Args:
            reference_manager: Instance of ReferenceManager to retrieve citation info.
            drafts_dir: Default directory to store drafts (used if no project active).
            citation_style: Default citation style.
            project_manager: Optional ProjectManager for multi-project support.
        """
        self.ref_manager = reference_manager
        self._default_drafts_dir = drafts_dir
        self.citation_style = citation_style
        self._project_manager = project_manager
        self._snapshot_manager: Optional[DraftSnapshotManager] = None
        self._git_committer: Optional[GitAutoCommitter] = None
        # Note: Directory is created on-demand when writing drafts,
        # not at initialization to avoid polluting root directory

    @property
    def drafts_dir(self) -> str:
        """
        Get the current drafts directory.
        Uses project directory if a project is active, otherwise default.
        """
        if self._project_manager:
            try:
                paths = self._project_manager.get_project_paths()
                return paths.get("drafts", self._default_drafts_dir)
            except (ValueError, KeyError):
                logger.debug("Project paths unavailable, using default drafts dir")
        return self._default_drafts_dir

    @property
    def snapshot_manager(self) -> DraftSnapshotManager:
        """Lazy-initialized snapshot manager tied to current drafts_dir."""
        drafts = self.drafts_dir
        if self._snapshot_manager is None or str(self._snapshot_manager._drafts_dir) != drafts:
            self._snapshot_manager = DraftSnapshotManager(drafts)
        return self._snapshot_manager

    @property
    def git_committer(self) -> GitAutoCommitter:
        """Lazy-initialized git auto-committer tied to project root."""
        if self._git_committer is None:
            # Use parent of drafts_dir (project root) as the repo dir
            project_root = os.path.dirname(self.drafts_dir)
            self._git_committer = GitAutoCommitter(project_root)
        return self._git_committer

    def set_citation_style(self, style: str):
        """Set the citation style."""
        # Validate style
        valid_styles = [s.value for s in CitationStyle]
        if style not in valid_styles:
            raise ValueError(f"Invalid style: {style}. Valid options: {valid_styles}")
        self.citation_style = style

    def create_draft(self, filename: str, content: str) -> str:
        """
        Create a draft file with formatted citations.

        Args:
            filename: Name of the draft file (e.g., "introduction.md").
            content: Content with placeholders like (PMID:123456).

        Returns:
            Path to the created draft file.
        """
        final_content = self._compile_draft(content)

        # Save file
        if not filename.endswith(".md"):
            filename += ".md"

        filepath = os.path.join(self.drafts_dir, filename)

        # Auto-snapshot before overwrite
        self.snapshot_manager.snapshot_before_write(filename, reason="create_draft")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_content)

        # Auto-commit after successful write
        self.git_committer.commit_draft(filename, reason="create_draft")

        return filepath

    def insert_citation(self, filename: str, target_text: str, pmid: str) -> str:
        """
        Insert a citation after the target text in an existing draft.

        Args:
            filename: Name of the draft file.
            target_text: Text segment to locate insertion point.
            pmid: PubMed ID to cite.

        Returns:
            Path to the updated draft file.
        """
        if not filename.endswith(".md"):
            filename += ".md"

        filepath = os.path.join(self.drafts_dir, filename)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Draft file {filename} not found.")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Extract and Parse Bibliography to map [n] -> PMID
        body_content = content
        existing_refs = {}

        if "## References" in content:
            parts = content.split("## References")
            body_content = parts[0].strip()

            # Regex to parse bib: \[(\d+)\] .*? PMID:(\d+)
            # Note: This only works for numbered styles (Vancouver).
            # For Author-Date styles, we need a different strategy or just rely on PMID presence.
            # For now, we assume if we are inserting, we might be disrupting the order.
            # But if we use Author-Date, order doesn't matter as much (alphabetical usually).

            bib_pattern = r"\[(\d+)\] .*? PMID:(\d+)"
            found_refs = re.findall(bib_pattern, content)
            for ref_num, ref_pmid in found_refs:
                existing_refs[ref_num] = ref_pmid

        # 2. Replace [n] in body with [PMID:xxx] (Only for numbered styles)
        # If style is APA/Harvard, citations are (Author, Year).
        # We need to reverse-engineer them too? Or just leave them?
        # If we leave them, `_compile_draft` won't touch them unless they match `(PMID:...)`.
        # So we only need to revert if we want to re-number.

        if self.citation_style in [
            CitationStyle.VANCOUVER.value,
            CitationStyle.NATURE.value,
            CitationStyle.AMA.value,
        ]:
            for ref_num, ref_pmid in existing_refs.items():
                # Handle brackets [1] or superscript ^1 (if we implemented that)
                # For now assuming [1] for Vancouver
                body_content = body_content.replace(f"[{ref_num}]", f"[PMID:{ref_pmid}]")

        # 3. Find target text and insert new placeholder
        if target_text not in body_content:
            raise ValueError(f"Target text '{target_text}' not found in draft.")

        insertion = f" [PMID:{pmid}]"
        new_content = body_content.replace(target_text, target_text + insertion, 1)

        # 4. Re-compile
        final_content = self._compile_draft(new_content)

        # Auto-snapshot before overwrite
        self.snapshot_manager.snapshot_before_write(filename, reason="insert_citation")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_content)

        # Auto-commit after successful write
        self.git_committer.commit_draft(filename, reason="insert_citation")

        return filepath

    def _format_citation_in_text(self, number: int, metadata: Dict[str, Any]) -> str:
        """Format the in-text citation."""
        if self.citation_style == CitationStyle.VANCOUVER.value:
            return f"[{number}]"
        elif self.citation_style == CitationStyle.APA.value:
            # (Author, Year)
            authors = metadata.get("authors", [])
            if not authors:
                author_text = "Unknown"
            elif len(authors) == 1:
                author_text = authors[0].split()[0]
            elif len(authors) == 2:
                author1 = authors[0].split()[0]
                author2 = authors[1].split()[0]
                author_text = f"{author1} & {author2}"
            else:
                author_text = f"{authors[0].split()[0]} et al."

            year = metadata.get("year", "n.d.")
            return f"({author_text}, {year})"
        elif self.citation_style == CitationStyle.HARVARD.value:
            # (Author Year)
            authors = metadata.get("authors", [])
            if not authors:
                author_text = "Unknown"
            elif len(authors) == 1:
                author_text = authors[0].split()[0]
            elif len(authors) == 2:
                author1 = authors[0].split()[0]
                author2 = authors[1].split()[0]
                author_text = f"{author1} and {author2}"
            else:
                author_text = f"{authors[0].split()[0]} et al."

            year = metadata.get("year", "n.d.")
            return f"({author_text} {year})"
        elif self.citation_style in [CitationStyle.NATURE.value, CitationStyle.AMA.value]:
            # Superscript (Markdown doesn't support native superscript, usually ^1^)
            return f"^{number}^"
        return f"[{number}]"

    def _format_authors_vancouver(self, metadata: Dict[str, Any], max_authors: int = 6) -> str:
        """Format author list in Vancouver style (Last AB, Next CD).

        Uses authors_full (structured) when available, falls back to authors (flat strings).
        Truncates with 'et al.' when exceeding max_authors.

        Args:
            metadata: Reference metadata dict.
            max_authors: Maximum authors before truncation to 'et al.'.

        Returns:
            Formatted author string.
        """
        authors_full = metadata.get("authors_full", [])
        if authors_full:
            formatted = []
            for a in authors_full:
                last = a.get("last_name", "")
                initials = a.get("initials", "")
                formatted.append(f"{last} {initials}" if initials else last)
            if len(formatted) > max_authors:
                return ", ".join(formatted[:max_authors]) + ", et al."
            return ", ".join(formatted)
        # Fallback: flat author strings
        authors = metadata.get("authors", [])
        if len(authors) > max_authors:
            return ", ".join(authors[:max_authors]) + ", et al."
        return ", ".join(authors) if authors else "Unknown"

    def _format_bibliography_entry(self, number: int, metadata: Dict[str, Any], pmid: str) -> str:
        """Format a single bibliography entry.

        Uses pre-formatted citation strings from metadata when available
        (verified data from PubMed). Falls back to manual formatting with
        volume/issue/pages/DOI.

        Args:
            number: Citation number.
            metadata: Reference metadata dict (from metadata.json).
            pmid: PubMed ID.

        Returns:
            Formatted bibliography entry string ending with newline.
        """
        # Try pre-formatted citation from verified metadata
        citation_data = metadata.get("citation", {})
        if self.citation_style == CitationStyle.VANCOUVER.value and citation_data.get("vancouver"):
            return f"[{number}] {citation_data['vancouver']}\n"
        if self.citation_style == CitationStyle.APA.value and citation_data.get("apa"):
            return f"{citation_data['apa']}\n"
        if self.citation_style == CitationStyle.NATURE.value and citation_data.get("nature"):
            return f"{number}. {citation_data['nature']}\n"

        # Manual formatting fallback
        max_authors = 6  # default, can be overridden by journal-profile
        authors = self._format_authors_vancouver(metadata, max_authors)
        title = metadata.get("title", "Unknown Title")
        journal = metadata.get("journal", "Unknown Journal")
        year = metadata.get("year", "Unknown Year")
        volume = metadata.get("volume", "")
        issue = metadata.get("issue", "")
        pages = metadata.get("pages", "")
        doi = metadata.get("doi", "")

        # Build volume;issue:pages segment
        vol_part = ""
        if volume:
            vol_part = f";{volume}"
            if issue:
                vol_part += f"({issue})"
            if pages:
                vol_part += f":{pages}"

        doi_part = f" doi:{doi}" if doi else ""

        if self.citation_style == CitationStyle.VANCOUVER.value:
            return f"[{number}] {authors}. {title}. {journal}. {year}{vol_part}.{doi_part}\n"
        elif self.citation_style == CitationStyle.APA.value:
            return f"{authors} ({year}). {title}. {journal}{vol_part}.{doi_part}\n"
        elif self.citation_style == CitationStyle.HARVARD.value:
            return f"{authors} ({year}) '{title}', {journal}{vol_part}.{doi_part}\n"
        elif self.citation_style == CitationStyle.NATURE.value:
            return f"{number}. {authors}. {title}. {journal} {year}{vol_part}.{doi_part}\n"
        elif self.citation_style == CitationStyle.AMA.value:
            return f"{number}. {authors}. {title}. {journal}. {year}{vol_part}.{doi_part}\n"
        return f"[{number}] {authors}. {title}. {journal}. {year}{vol_part}.{doi_part}\n"

    def _compile_draft(self, content: str) -> str:
        """
        Compile draft content: replace placeholders and generate bibliography.

        Args:
            content: Raw content with [PMID:xxx] placeholders.

        Returns:
            Compiled content with formatted citations and bibliography.
        """
        # 1. Find all PMID placeholders
        pattern = r"[\(\[]PMID:(\d+)[\)\]]"
        matches = re.findall(pattern, content)

        # Deduplicate but keep order
        pmids = []
        for pmid in matches:
            if pmid not in pmids:
                pmids.append(pmid)

        # 2. Replace placeholders
        citation_map = {pmid: i + 1 for i, pmid in enumerate(pmids)}

        def replace_match(match):
            pmid = match.group(1)
            number = citation_map.get(pmid)
            metadata = self.ref_manager.get_metadata(pmid) or {}
            return self._format_citation_in_text(number, metadata)

        formatted_content = re.sub(pattern, replace_match, content)

        # 3. Generate Bibliography
        bibliography = "\n\n## References\n\n"

        # For Author-Date styles, usually bibliography is alphabetical.
        # For Numbered styles, it's by appearance.
        # We will stick to appearance order for now unless strictly required otherwise.
        # (APA/Harvard usually alphabetical, but for simplicity we keep appearance order or we'd need to re-sort pmids)

        # If APA/Harvard, we should sort pmids alphabetically by author?
        # Let's keep it simple for Phase 1: Order by appearance for all, but format differently.

        for pmid in pmids:
            number = citation_map[pmid]
            metadata = self.ref_manager.get_metadata(pmid) or {}
            entry = self._format_bibliography_entry(number, metadata, pmid)
            bibliography += entry

        return formatted_content + bibliography

    def sync_references_from_wikilinks(self, filename: str) -> Dict[str, Any]:
        """
        Scan markdown for [[citation_key]] wikilinks and generate/update References section.

        This implements a citation manager workflow:
        1. User writes [[pachecolopez2014_24891204]] in text
        2. This method scans for all wikilinks
        3. Maps them to saved references
        4. Generates numbered or author-date citations in text
        5. Appends formatted References section

        Args:
            filename: Name of the markdown file to process.

        Returns:
            Dict with processing results including citations found and generated.
        """
        if not filename.endswith(".md"):
            filename += ".md"

        # Determine project root directory
        project_root = None
        if self._project_manager:
            try:
                paths = self._project_manager.get_project_paths()
                project_root = paths.get("root")
            except (ValueError, KeyError):
                logger.debug("Project paths unavailable, skipping project root")

        # Search order: drafts dir, project root, current dir
        search_paths = [self.drafts_dir]
        if project_root:
            search_paths.insert(0, project_root)

        filepath = None
        for search_dir in search_paths:
            candidate = os.path.join(search_dir, filename)
            if os.path.exists(candidate):
                filepath = candidate
                break

        if not filepath:
            raise FileNotFoundError(f"File {filename} not found. Searched: {search_paths}")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Extract body (everything before ## References)
        if "## References" in content:
            body_content = content.split("## References")[0].rstrip()
        else:
            body_content = content.rstrip()

        # 2. First, restore any previously synced citations back to wikilinks
        #    Pattern: [1]<!-- [[citation_key]] --> or (Author, Year)<!-- [[citation_key]] -->
        restore_pattern = r"(?:\[\d+\]|\([^)]+,\s*\d{4}\))<!-- \[\[([^\]]+)\]\] -->"
        body_content = re.sub(restore_pattern, r"[[\1]]", body_content)

        # 3. Find all wikilinks: [[citation_key]] or [[PMID:12345]]
        wikilink_pattern = r"\[\[([^\]]+)\]\]"
        wikilinks = re.findall(wikilink_pattern, body_content)

        if not wikilinks:
            return {
                "success": True,
                "message": "No wikilinks found in document.",
                "citations_found": 0,
                "filepath": filepath,
            }

        # 3. Map wikilinks to PMIDs
        citations = []  # List of (wikilink, pmid, metadata) in order of appearance
        seen_pmids = set()
        not_found = []

        for wikilink in wikilinks:
            # Skip non-citation wikilinks (e.g., internal links)
            # Citation wikilinks typically match: author_year_pmid or PMID:xxx or just pmid

            pmid = None

            # Try PMID:xxx format
            if wikilink.upper().startswith("PMID:"):
                pmid = wikilink.split(":")[1].strip()
            # Try pure numeric (PMID)
            elif wikilink.isdigit():
                pmid = wikilink
            # Try citation_key format (e.g., pachecolopez2014_24891204)
            elif "_" in wikilink:
                # Extract PMID from citation_key (last part after _)
                parts = wikilink.split("_")
                potential_pmid = parts[-1]
                if potential_pmid.isdigit():
                    pmid = potential_pmid

            if not pmid:
                continue  # Not a citation wikilink

            if pmid in seen_pmids:
                continue  # Already processed

            # Get metadata from reference manager
            metadata = self.ref_manager.get_metadata(pmid)
            if metadata:
                citations.append((wikilink, pmid, metadata))
                seen_pmids.add(pmid)
            else:
                not_found.append(wikilink)

        if not citations:
            return {
                "success": True,
                "message": "No valid citation wikilinks found.",
                "citations_found": 0,
                "not_found": not_found,
                "filepath": filepath,
            }

        # 4. Replace wikilinks with formatted in-text citations (REVERSIBLE)
        #    Format: [1]<!-- [[citation_key]] --> so it can be restored later
        new_body = body_content
        citation_map = {pmid: i + 1 for i, (_, pmid, _) in enumerate(citations)}

        for wikilink, pmid, metadata in citations:
            number = citation_map[pmid]
            in_text = self._format_citation_in_text(number, metadata)
            # REVERSIBLE format: [1]<!-- [[wikilink]] -->
            reversible_citation = f"{in_text}<!-- [[{wikilink}]] -->"
            new_body = new_body.replace(f"[[{wikilink}]]", reversible_citation)

        # 5. Generate References section
        references_section = "\n\n---\n\n## References\n\n"

        for wikilink, pmid, metadata in citations:
            number = citation_map[pmid]
            entry = self._format_bibliography_entry(number, metadata, pmid)
            # Add wikilink back as invisible anchor for bidirectional linking
            # Blank line between entries for readability
            references_section += f"{entry.rstrip()} <!-- [[{wikilink}]] -->\n\n"

        # 6. Assemble final content
        final_content = new_body + references_section

        # 7. Write back
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_content)

        # Auto-commit after sync
        self.git_committer.commit_draft(filename, reason="sync_references")

        return {
            "success": True,
            "message": f"Synchronized {len(citations)} references.",
            "citations_found": len(citations),
            "citations": [
                {
                    "number": citation_map[pmid],
                    "wikilink": wikilink,
                    "pmid": pmid,
                    "title": metadata.get("title", "Unknown")[:60] + "...",
                }
                for wikilink, pmid, metadata in citations
            ],
            "not_found": not_found,
            "filepath": filepath,
            "style": self.citation_style,
        }
