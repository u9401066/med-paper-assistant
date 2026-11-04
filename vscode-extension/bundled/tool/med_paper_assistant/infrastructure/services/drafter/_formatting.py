"""In-text citation, author list, and bibliography formatting plus draft compilation."""

import re
from typing import Any, Dict, List

import structlog

from med_paper_assistant.domain.services.references_section import split_references_section

from ._base import DrafterBase
from ._models import CitationStyle

logger = structlog.get_logger(__package__)


def _volume_issue_pages(volume: str, issue: str, pages: str) -> str:
    """Build the ``;volume(issue):pages`` segment of a bibliography entry."""
    vol_part = ""
    if volume:
        vol_part = f";{volume}"
        if issue:
            vol_part += f"({issue})"
        if pages:
            vol_part += f":{pages}"
    return vol_part


class CitationFormattingMixin(DrafterBase):
    # Formats citations and bibliographies and compiles ``[PMID:x]`` placeholders.
    # No docstring: ``inspect.getdoc(Drafter)`` would otherwise inherit it (original is None).

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
                parts = authors[0].split()
                author_text = parts[0] if parts else "Unknown"
            elif len(authors) == 2:
                p1 = authors[0].split()
                p2 = authors[1].split()
                author1 = p1[0] if p1 else "Unknown"
                author2 = p2[0] if p2 else "Unknown"
                author_text = f"{author1} & {author2}"
            else:
                p0 = authors[0].split()
                author_text = f"{p0[0]} et al." if p0 else "Unknown et al."

            year = metadata.get("year", "n.d.")
            return f"({author_text}, {year})"
        elif self.citation_style == CitationStyle.HARVARD.value:
            # (Author Year)
            authors = metadata.get("authors", [])
            if not authors:
                author_text = "Unknown"
            elif len(authors) == 1:
                parts = authors[0].split()
                author_text = parts[0] if parts else "Unknown"
            elif len(authors) == 2:
                p1 = authors[0].split()
                p2 = authors[1].split()
                author1 = p1[0] if p1 else "Unknown"
                author2 = p2[0] if p2 else "Unknown"
                author_text = f"{author1} and {author2}"
            else:
                p0 = authors[0].split()
                author_text = f"{p0[0]} et al." if p0 else "Unknown et al."

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
        doi = metadata.get("doi", "")

        vol_part = _volume_issue_pages(
            metadata.get("volume", ""), metadata.get("issue", ""), metadata.get("pages", "")
        )
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

        # No citations: leave the content (including any existing References) untouched.
        if not pmids:
            return formatted_content

        # Replace an existing References block instead of appending a duplicate heading.
        split = split_references_section(formatted_content)
        bibliography = self._build_bibliography(pmids, citation_map)
        return split.with_tail(split.body + "\n\n" + bibliography)

    def _build_bibliography(self, pmids: List[str], citation_map: Dict[str, int]) -> str:
        """Build a References block in order of first appearance for every style."""
        bibliography = "## References\n\n"
        for pmid in pmids:
            number = citation_map[pmid]
            metadata = self.ref_manager.get_metadata(pmid)
            if not metadata:
                logger.warning("Reference metadata unavailable for PMID", pmid=pmid)
                bibliography += f"[{number}] Reference metadata unavailable. PMID:{pmid}\n"
                continue
            bibliography += self._format_bibliography_entry(number, metadata, pmid)
        return bibliography
