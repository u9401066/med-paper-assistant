"""
CSL Citation Formatter — Infrastructure Service.

Uses citeproc-py to format citations per CSL (Citation Style Language) standard.
Replaces hand-written formatting with 10,000+ community-maintained styles.

Architecture:
  Domain: Reference entity → to_csl_json() → CSL-JSON dict
  Infrastructure: This module → citeproc-py → formatted strings
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from citeproc import (
    Citation,
    CitationItem,
    CitationStylesBibliography,
    CitationStylesStyle,
    formatter,
)
from citeproc.source.json import CiteProcJSON

from med_paper_assistant.domain.entities.reference import Reference
from med_paper_assistant.domain.value_objects.citation import CitationStyle

logger = logging.getLogger(__name__)

# CSL style directory: templates/csl/ (user-provided) or citeproc built-in
_TEMPLATES_CSL_DIR = Path(__file__).parents[4] / "templates" / "csl"

# Map our CitationStyle enum → CSL file names
_STYLE_TO_CSL_FILE: dict[str, str] = {
    "vancouver": "vancouver.csl",
    "apa": "apa.csl",
    "harvard": "harvard-cite-them-right.csl",
    "nature": "nature.csl",
    "ama": "american-medical-association.csl",
    "nlm": "national-library-of-medicine.csl",
    "mdpi": "multidisciplinary-digital-publishing-institute.csl",
}


def reference_to_csl_json(ref: Reference, ref_id: str | None = None) -> dict[str, Any]:
    """
    Convert a Reference entity to CSL-JSON format.

    CSL-JSON is the standard interchange format for citation processors.
    Spec: https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html
    """
    csl_id = ref_id or ref.unique_id or ref.citation_key or "ref"

    # Build author list
    authors = []
    if ref.authors_full:
        for au in ref.authors_full:
            if isinstance(au, dict):
                authors.append({
                    "family": au.get("last_name", ""),
                    "given": au.get("first_name", au.get("initials", "")),
                })
    elif ref.authors:
        for name in ref.authors:
            parts = name.strip().split()
            if len(parts) >= 2:
                authors.append({"family": parts[0], "given": " ".join(parts[1:])})
            elif parts:
                authors.append({"family": parts[0]})

    # Build issued date
    issued: dict[str, Any] = {}
    if ref.year:
        issued = {"date-parts": [[int(ref.year)]]}

    entry: dict[str, Any] = {
        "id": csl_id,
        "type": "article-journal",
        "title": ref.title,
        "author": authors,
        "issued": issued,
    }

    # Optional fields
    journal = ref.journal_abbrev or ref.journal
    if journal:
        entry["container-title"] = journal
    if ref.volume:
        entry["volume"] = ref.volume
    if ref.issue:
        entry["issue"] = ref.issue
    if ref.pages:
        entry["page"] = ref.pages
    if ref.doi:
        entry["DOI"] = ref.doi
    if ref.pmid:
        entry["PMID"] = ref.pmid

    return entry


def _resolve_csl_path(style: str | CitationStyle) -> str | None:
    """
    Resolve a CSL style to a file path.

    Search order:
    1. Absolute/relative path (if file exists)
    2. templates/csl/{name}.csl
    3. templates/csl/{mapped_name}.csl (via _STYLE_TO_CSL_FILE)
    4. citeproc-py built-in styles
    """
    style_str = style.value if isinstance(style, CitationStyle) else str(style)

    # 1. Direct file path
    if os.path.isfile(style_str):
        return style_str

    # Also check with .csl extension
    if os.path.isfile(f"{style_str}.csl"):
        return f"{style_str}.csl"

    # 2. templates/csl/{style_str}.csl
    candidate = _TEMPLATES_CSL_DIR / f"{style_str}.csl"
    if candidate.is_file():
        return str(candidate)

    # 3. Mapped name
    mapped = _STYLE_TO_CSL_FILE.get(style_str.lower())
    if mapped:
        candidate = _TEMPLATES_CSL_DIR / mapped
        if candidate.is_file():
            return str(candidate)

    # 4. citeproc built-in
    import citeproc as _cp

    builtin_dir = Path(_cp.__file__).parent / "data" / "styles"
    for name in [f"{style_str}.csl", mapped or ""]:
        if name:
            candidate = builtin_dir / name
            if candidate.is_file():
                return str(candidate)

    return None


class CSLCitationFormatter:
    """
    Format citations using CSL (Citation Style Language) via citeproc-py.

    Usage:
        fmt = CSLCitationFormatter("vancouver")  # or path to .csl file
        bib_entries = fmt.format_bibliography([ref1, ref2, ref3])
        in_text = fmt.format_in_text_citation([ref1], [1])
    """

    def __init__(self, style: str | CitationStyle = "vancouver") -> None:
        self._style_name = style.value if isinstance(style, CitationStyle) else style
        self._csl_path = _resolve_csl_path(style)
        self._available = self._csl_path is not None

        if not self._available:
            logger.warning(
                "CSL style '%s' not found. Install .csl file to templates/csl/ "
                "or use a built-in style. Falling back to legacy formatter.",
                self._style_name,
            )

    @property
    def available(self) -> bool:
        """Whether the CSL style file is available."""
        return self._available

    @property
    def style_name(self) -> str:
        return self._style_name

    @property
    def csl_path(self) -> str | None:
        return self._csl_path

    def format_bibliography(
        self,
        references: list[Reference],
        output_format: str = "plain",
    ) -> list[str]:
        """
        Format a list of references as a numbered bibliography.

        Args:
            references: List of Reference entities
            output_format: "plain" or "html"

        Returns:
            List of formatted bibliography strings (one per reference)
        """
        if not self._available:
            raise RuntimeError(f"CSL style '{self._style_name}' not available")

        if not references:
            return []

        fmt = formatter.html if output_format == "html" else formatter.plain

        # Convert references to CSL-JSON
        csl_data = []
        ref_ids = []
        for i, ref in enumerate(references, 1):
            ref_id = f"ref{i}"
            csl_data.append(reference_to_csl_json(ref, ref_id=ref_id))
            ref_ids.append(ref_id)

        source = CiteProcJSON(csl_data)
        style = CitationStylesStyle(self._csl_path, validate=False)
        bibliography = CitationStylesBibliography(style, source, fmt)

        # Register all citations (required before bibliography generation)
        for ref_id in ref_ids:
            citation = Citation([CitationItem(ref_id)])
            bibliography.register(citation)
            bibliography.cite(citation, lambda _: None)

        # Generate bibliography
        return [str(item).strip() for item in bibliography.bibliography()]

    def format_in_text_citations(
        self,
        references: list[Reference],
    ) -> list[str]:
        """
        Generate in-text citation markers for a list of references.

        Returns a list of formatted in-text citations (e.g., "[1]", "(Tang, 2024)").
        """
        if not self._available:
            raise RuntimeError(f"CSL style '{self._style_name}' not available")

        if not references:
            return []

        csl_data = []
        ref_ids = []
        for i, ref in enumerate(references, 1):
            ref_id = f"ref{i}"
            csl_data.append(reference_to_csl_json(ref, ref_id=ref_id))
            ref_ids.append(ref_id)

        source = CiteProcJSON(csl_data)
        style = CitationStylesStyle(self._csl_path, validate=False)
        bibliography = CitationStylesBibliography(style, source, formatter.plain)

        results = []
        for ref_id in ref_ids:
            citation = Citation([CitationItem(ref_id)])
            bibliography.register(citation)
            text = str(bibliography.cite(citation, lambda _: None)).strip()
            results.append(text)

        return results

    def format_single(self, reference: Reference, number: int = 1) -> str:
        """Format a single reference. Convenience wrapper."""
        entries = self.format_bibliography([reference])
        return entries[0] if entries else ""

    @staticmethod
    def list_available_styles() -> list[str]:
        """List all available CSL style files."""
        styles: list[str] = []

        # templates/csl/
        if _TEMPLATES_CSL_DIR.is_dir():
            for f in _TEMPLATES_CSL_DIR.glob("*.csl"):
                styles.append(f.stem)

        # citeproc built-in
        import citeproc as _cp

        builtin_dir = Path(_cp.__file__).parent / "data" / "styles"
        if builtin_dir.is_dir():
            for f in builtin_dir.glob("*.csl"):
                name = f.stem
                if name not in styles:
                    styles.append(name)

        return sorted(styles)
