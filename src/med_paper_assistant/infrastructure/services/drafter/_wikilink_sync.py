"""Wikilink-driven reference synchronisation for drafts."""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import structlog

from med_paper_assistant.domain.services.citation_converter import (
    restore_reversible_citations_to_wikilinks,
)
from med_paper_assistant.domain.services.reference_key_resolution import (
    extract_pmid_from_key,
    is_non_pmid_key,
    resolve_reference_metadata,
)
from med_paper_assistant.domain.services.references_section import (
    ReferencesSplit,
    split_references_section,
)

from ._filenames import normalize_draft_filename
from ._formatting import CitationFormattingMixin

logger = structlog.get_logger(__package__)

_Citations = List[Tuple[str, str, Dict[str, Any]]]


def _find_draft_file(drafter: CitationFormattingMixin, filename: str) -> str:
    """Locate a draft in the project root or drafts dir (in that order)."""
    # Determine project root directory
    project_root = None
    if drafter._project_manager:
        try:
            paths = drafter._project_manager.get_project_paths()
            project_root = paths.get("root")
        except (ValueError, KeyError):
            logger.debug("Project paths unavailable, skipping project root")

    # Search order: drafts dir, project root, current dir
    search_paths = [drafter.drafts_dir]
    if project_root:
        search_paths.insert(0, project_root)

    for search_dir in search_paths:
        candidate = os.path.join(search_dir, filename)
        if os.path.exists(candidate):
            return candidate

    raise FileNotFoundError(f"File {filename} not found. Searched: {search_paths}")


def _collect_citations(wikilinks: List[str], ref_manager: Any) -> Tuple[_Citations, List[str]]:
    """Resolve wikilinks to ``(wikilink, pmid, metadata)`` in order, plus unresolved keys."""
    citations: _Citations = []
    seen_pmids = set()
    not_found: List[str] = []

    for wikilink in wikilinks:
        # Skip non-citation wikilinks (e.g., internal links).
        # Citation wikilinks match: author2024_pmid, PMID:xxx, a bare PMID,
        # or Zotero/DOI keys (author2024_zot_ID / author2024_doi_ID).
        if extract_pmid_from_key(wikilink) is None and not is_non_pmid_key(wikilink):
            continue

        resolved = resolve_reference_metadata(
            wikilink,
            ref_manager.get_metadata,
            getattr(ref_manager, "list_references", None),
        )
        if resolved is None:
            if wikilink not in not_found:
                not_found.append(wikilink)
            continue

        pmid, metadata = resolved
        if pmid in seen_pmids:
            continue  # Already processed
        citations.append((wikilink, pmid, metadata))
        seen_pmids.add(pmid)

    return citations, not_found


def _replace_with_reversible_citations(
    drafter: CitationFormattingMixin,
    body_content: str,
    citations: _Citations,
    citation_map: Dict[str, int],
) -> str:
    """Replace each wikilink with ``[n] [[wikilink]]`` so Foam can still detect links.

    Older drafts may still contain the legacy HTML-comment format.
    """
    new_body = body_content
    for wikilink, pmid, metadata in citations:
        number = citation_map[pmid]
        in_text = drafter._format_citation_in_text(number, metadata)
        # REVERSIBLE format: [1] [[wikilink]]
        reversible_citation = f"{in_text} [[{wikilink}]]"
        new_body = new_body.replace(f"[[{wikilink}]]", reversible_citation)
    return new_body


def _build_references_section(
    drafter: CitationFormattingMixin, citations: _Citations, citation_map: Dict[str, int]
) -> str:
    references_section = "\n\n---\n\n## References\n\n"

    for wikilink, pmid, metadata in citations:
        number = citation_map[pmid]
        entry = drafter._format_bibliography_entry(number, metadata, pmid)
        # Add wikilink anchor for bidirectional linking and Foam graph edges
        # Blank line between entries for readability
        references_section += f"{entry.rstrip()} [[{wikilink}]]\n\n"
    return references_section


def _render_synced_content(
    drafter: CitationFormattingMixin,
    split: ReferencesSplit,
    body_content: str,
    citations: _Citations,
    citation_map: Dict[str, int],
) -> str:
    # Replace wikilinks with formatted in-text citations (REVERSIBLE), generate the
    # References section, and re-append sections that followed References.
    new_body = _replace_with_reversible_citations(drafter, body_content, citations, citation_map)
    references_section = _build_references_section(drafter, citations, citation_map)
    return split.with_tail(new_body + references_section)


def _no_citations_result(
    message: str, filepath: str, not_found: Optional[List[str]] = None
) -> Dict[str, Any]:
    result: Dict[str, Any] = {"success": True, "message": message, "citations_found": 0}
    if not_found is not None:
        result["not_found"] = not_found
    result["filepath"] = filepath
    return result


def _write_synced_draft(
    drafter: CitationFormattingMixin, filename: str, filepath: str, final_content: str
) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_content)

    drafter.ref_manager.refresh_foam_graph()

    # Auto-commit after sync
    drafter.git_committer.commit_draft(filename, reason="sync_references")


def _sync_summary(
    drafter: Any,
    citations: _Citations,
    citation_map: Dict[str, int],
    not_found: List[str],
    filepath: str,
) -> Dict[str, Any]:
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
        "style": drafter.citation_style,
    }


class WikilinkSyncMixin(CitationFormattingMixin):
    # Synchronises ``[[citation_key]]`` wikilinks with a generated References section
    # (no docstring: see CitationFormattingMixin).

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
        filename = normalize_draft_filename(filename)

        filepath = _find_draft_file(self, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Extract body (everything before ## References); keep trailing sections
        split = split_references_section(content)

        # 2. Restore any previously synced reversible citations back to raw
        #    wikilinks so re-syncing never duplicates the in-text prefix.
        body_content = restore_reversible_citations_to_wikilinks(split.body)

        # 3. Find all wikilinks: [[citation_key]] or [[PMID:12345]]
        wikilinks = re.findall(r"\[\[([^\]]+)\]\]", body_content)

        if not wikilinks:
            return _no_citations_result("No wikilinks found in document.", filepath)

        # 3. Map wikilinks to saved references
        citations, not_found = _collect_citations(wikilinks, self.ref_manager)

        if not citations:
            return _no_citations_result("No valid citation wikilinks found.", filepath, not_found)

        citation_map = {pmid: i + 1 for i, (_, pmid, _) in enumerate(citations)}
        final_content = _render_synced_content(self, split, body_content, citations, citation_map)
        _write_synced_draft(self, filename, filepath, final_content)

        return _sync_summary(self, citations, citation_map, not_found, filepath)
