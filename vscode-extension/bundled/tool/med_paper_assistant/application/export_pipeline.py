"""
Export Pipeline — Orchestrates citation conversion + bibliography generation + Pandoc export.

Bridges the gap between the wikilink-based editing workflow and
Pandoc --citeproc's [@key] + CSL-JSON bibliography requirement.

Pipeline:
  1. Read draft (wikilink format)
  2. Convert wikilinks → [@key] (CitationConverter)
  3. Build CSL-JSON bibliography from referenced keys
  4. Call Pandoc with --citeproc --bibliography --csl
  5. Return formatted document

Architecture:
  Application layer service. Orchestrates domain + infrastructure services.
  No direct file I/O for conversion logic — delegates to lower layers.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from med_paper_assistant.domain.services.citation_converter import (
    extract_citation_keys,
    wikilinks_to_pandoc,
)
from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager
from med_paper_assistant.infrastructure.services.csl_formatter import reference_to_csl_json
from med_paper_assistant.infrastructure.services.pandoc_exporter import PandocExporter

logger = logging.getLogger(__name__)


class ExportPipeline:
    """
    End-to-end export: Markdown (wikilinks) → formatted document.

    Usage:
        pipeline = ExportPipeline(ref_manager, pandoc_exporter)

        # Export to Word
        pipeline.export_docx(
            draft_path="projects/my-paper/drafts/introduction.md",
            output_path="exports/introduction.docx",
            csl_style="vancouver",
        )

        # Or just convert citations without exporting
        result = pipeline.prepare_for_pandoc(content, ref_manager)
    """

    def __init__(
        self,
        ref_manager: ReferenceManager,
        pandoc_exporter: PandocExporter | None = None,
    ) -> None:
        self._ref_manager = ref_manager
        self._pandoc = pandoc_exporter or PandocExporter()

    def prepare_for_pandoc(self, content: str) -> dict[str, Any]:
        """
        Convert draft content to Pandoc-ready format.

        Steps:
          1. Convert [[wikilinks]] → [@key]
          2. Build CSL-JSON bibliography for all referenced keys
          3. Return converted content + bibliography data

        Args:
            content: Markdown with wikilink citations.

        Returns:
            {
                "content": str,          # Markdown with [@key] citations
                "bibliography": list,    # CSL-JSON entries
                "citation_keys": list,   # All citation keys found
                "conversion": ConversionResult,
                "warnings": list[str],
            }
        """
        # Step 1: Convert wikilinks → [@key]
        conversion = wikilinks_to_pandoc(content)

        # Step 2: Build bibliography from citation keys
        bibliography = []
        warnings = list(conversion.warnings)

        for key in conversion.citation_keys:
            csl_entry = self._resolve_citation_key(key)
            if csl_entry:
                bibliography.append(csl_entry)
            else:
                warnings.append(f"Citation key '{key}' not found in local references")

        return {
            "content": conversion.content,
            "bibliography": bibliography,
            "citation_keys": conversion.citation_keys,
            "conversion": conversion,
            "warnings": warnings,
        }

    @staticmethod
    def _build_yaml_frontmatter(
        title: str,
        authors: list[dict[str, Any]] | None = None,
        date: str | None = None,
    ) -> str:
        """Build YAML frontmatter for Pandoc metadata (title, authors, date).

        Pandoc uses YAML frontmatter to populate document properties and
        render title/author blocks in the output (Word, PDF, HTML).

        Args:
            title: Document title.
            authors: List of structured author dicts with 'name', 'affiliations',
                     'email', 'is_corresponding', 'orcid' fields.
            date: Optional date string.

        Returns:
            YAML frontmatter string (including ``---`` delimiters), or empty
            string if no metadata provided.
        """
        import yaml

        meta: dict[str, Any] = {}
        if title:
            meta["title"] = title
        if authors:
            # Pandoc author metadata: keep only 'name' for YAML.
            # Detailed author info (affiliations, email, ORCID) is rendered
            # in the content block via _build_author_content_block().
            pandoc_authors = []
            for a in authors:
                name = a.get("name", "")
                if not name:
                    continue
                pandoc_authors.append(name)
            if pandoc_authors:
                meta["author"] = pandoc_authors
        if date:
            meta["date"] = date

        if not meta:
            return ""

        return "---\n" + yaml.dump(meta, allow_unicode=True, default_flow_style=False) + "---\n\n"

    @staticmethod
    def _build_author_content_block(authors: list[dict[str, Any]]) -> str:
        """Build a rich author block as markdown content (with affiliations).

        Complements YAML frontmatter by injecting a visible author/affiliation
        section directly into the document body.  This ensures affiliations,
        ORCID, and corresponding-author info are visible in the output even
        when the Pandoc template doesn't render structured author metadata.

        Args:
            authors: List of structured author dicts.

        Returns:
            Markdown string with author line, affiliations, and corresponding
            author details.  Empty string if no authors provided.
        """
        from med_paper_assistant.domain.value_objects.author import Author, generate_author_block

        if not authors:
            return ""

        author_objs = [Author.from_dict(a) for a in authors if a.get("name")]
        if not author_objs:
            return ""

        return generate_author_block(author_objs) + "\n"

    @staticmethod
    def _strip_title_heading(content: str) -> tuple[str, str]:
        """Extract and remove the first H1 heading from markdown content.

        When we inject the title via YAML frontmatter, the original ``# Title``
        line would be duplicated.  This helper strips it.

        Args:
            content: Markdown content.

        Returns:
            (title_text, remaining_content) — title without ``# `` prefix,
            and the content with the H1 line removed.
        """
        import re

        match = re.match(r"^#\s+(.+?)(?:\n|$)", content)
        if match:
            title = match.group(1).strip()
            remaining = content[match.end() :]
            return title, remaining
        return "", content

    def export_docx(
        self,
        draft_path: str,
        output_path: str,
        *,
        csl_style: str = "vancouver",
        reference_doc: str | None = None,
        extra_args: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Full export: draft file → Word document with formatted citations.

        Args:
            draft_path: Path to markdown draft file.
            output_path: Path for the output .docx file.
            csl_style: CSL style name (e.g., "vancouver", "apa").
            reference_doc: Optional Word template for styling.
            extra_args: Additional Pandoc arguments.
            metadata: Optional project metadata dict with keys:
                - ``title`` (str): Override document title.
                - ``authors`` (list[dict]): Structured author information.
                - ``date`` (str): Document date.
                When provided, YAML frontmatter and an author content block
                are injected into the document.

        Returns:
            Dict with export results and any warnings.
        """
        if not self._pandoc.available:
            raise RuntimeError("Pandoc is not available. Install via pypandoc.download_pandoc()")

        # Read draft
        content = Path(draft_path).read_text(encoding="utf-8")

        # Prepare for Pandoc (citation conversion)
        prepared = self.prepare_for_pandoc(content)

        if not prepared["bibliography"]:
            logger.warning("No bibliography entries found — citations won't be resolved")

        # Inject title/author metadata if provided
        pandoc_content = prepared["content"]
        if metadata:
            authors = metadata.get("authors", [])
            date = metadata.get("date")

            # Extract title from H1 heading (avoid duplication)
            extracted_title, body = self._strip_title_heading(pandoc_content)
            title = metadata.get("title") or extracted_title

            # Build YAML frontmatter (sets Word document properties)
            frontmatter = self._build_yaml_frontmatter(title, authors, date)

            # Build visible author block (affiliations, corresponding author)
            author_block = self._build_author_content_block(authors)

            pandoc_content = frontmatter + author_block + body

        # Write temporary bibliography file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as bib_file:
            json.dump(prepared["bibliography"], bib_file, ensure_ascii=False, indent=2)
            bib_path = bib_file.name

        try:
            # Call Pandoc
            result_path = self._pandoc.markdown_to_docx(
                source=pandoc_content,
                output_path=output_path,
                csl=csl_style,
                bibliography=bib_path,
                reference_doc=reference_doc,
                extra_args=extra_args,
            )

            return {
                "success": True,
                "output_path": result_path,
                "citations_converted": prepared["conversion"].citations_converted,
                "citation_keys": prepared["citation_keys"],
                "warnings": prepared["warnings"],
            }
        finally:
            # Clean up temp file
            try:
                os.unlink(bib_path)
            except OSError:
                pass

    def export_pdf(
        self,
        draft_path: str,
        output_path: str,
        *,
        csl_style: str = "vancouver",
        extra_args: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Full export: draft file → PDF with formatted citations.

        Requires a LaTeX engine (pdflatex, xelatex, or lualatex).

        Args:
            draft_path: Path to markdown draft file.
            output_path: Path for the output .pdf file.
            csl_style: CSL style name (e.g., "vancouver", "apa").
            extra_args: Additional Pandoc arguments.
            metadata: Optional project metadata dict (title, authors, date).

        Returns:
            Dict with export results and any warnings.
        """
        if not self._pandoc.available:
            raise RuntimeError("Pandoc is not available. Install via pypandoc.download_pandoc()")

        content = Path(draft_path).read_text(encoding="utf-8")
        prepared = self.prepare_for_pandoc(content)

        if not prepared["bibliography"]:
            logger.warning("No bibliography entries found — citations won't be resolved")

        # Inject title/author metadata if provided
        pandoc_content = prepared["content"]
        if metadata:
            authors = metadata.get("authors", [])
            date = metadata.get("date")
            extracted_title, body = self._strip_title_heading(pandoc_content)
            title = metadata.get("title") or extracted_title
            frontmatter = self._build_yaml_frontmatter(title, authors, date)
            author_block = self._build_author_content_block(authors)
            pandoc_content = frontmatter + author_block + body

        # Write temporary bibliography file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as bib_file:
            json.dump(prepared["bibliography"], bib_file, ensure_ascii=False, indent=2)
            bib_path = bib_file.name

        try:
            # Build args: CSL + bibliography + citeproc + user extras
            args = list(extra_args or [])
            csl_path = self._pandoc._resolve_csl(csl_style)
            if csl_path:
                args.extend(["--csl", csl_path, "--citeproc"])
            args.extend(["--bibliography", bib_path])

            # For lualatex/xelatex: use a Unicode-capable font + fallback
            engine = self._pandoc._detect_pdf_engine()
            if engine in ("lualatex", "xelatex"):
                if not any("mainfont" in a for a in args):
                    args.extend(["-V", "mainfont=DejaVu Serif"])
                if not any("monofont" in a for a in args):
                    args.extend(["-V", "monofont=DejaVu Sans Mono"])

                # Fallback font for chars missing in DejaVu Serif (e.g. ✗)
                preamble = (
                    "\\newfontfamily\\fallbackfont{DejaVu Sans}\n"
                    "\\usepackage{newunicodechar}\n"
                    "\\newunicodechar{✗}{{\\fallbackfont ✗}}\n"
                    "\\newunicodechar{✓}{{\\fallbackfont ✓}}\n"
                )
                preamble_file = tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".tex",
                    delete=False,
                    encoding="utf-8",
                )
                preamble_file.write(preamble)
                preamble_path = preamble_file.name
                preamble_file.close()
                args.extend(["-H", preamble_path])
            else:
                preamble_path = None

            # Strip internal emoji markers (🔒) that aren't in any system font
            import re as _re

            pandoc_content = _re.sub(r"[\U0001F512\U0001F916\u270F\u2728]", "", pandoc_content)

            result_path = self._pandoc.markdown_to_pdf(
                source=pandoc_content,
                output_path=output_path,
                extra_args=args,
            )

            return {
                "success": True,
                "output_path": result_path,
                "citations_converted": prepared["conversion"].citations_converted,
                "citation_keys": prepared["citation_keys"],
                "warnings": prepared["warnings"],
            }
        finally:
            try:
                os.unlink(bib_path)
            except OSError:
                pass
            if preamble_path:
                try:
                    os.unlink(preamble_path)
                except OSError:
                    pass

    def export_html(
        self,
        content: str,
        *,
        csl_style: str = "vancouver",
    ) -> dict[str, Any]:
        """
        Export to HTML with formatted citations.

        Args:
            content: Markdown with wikilink citations.
            csl_style: CSL style name.

        Returns:
            Dict with HTML content and metadata.
        """
        if not self._pandoc.available:
            raise RuntimeError("Pandoc is not available")

        prepared = self.prepare_for_pandoc(content)

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as bib_file:
            json.dump(prepared["bibliography"], bib_file, ensure_ascii=False, indent=2)
            bib_path = bib_file.name

        try:
            html = self._pandoc.convert(
                source=prepared["content"],
                to="html",
                csl=csl_style,
                bibliography=bib_path,
            )
            return {
                "success": True,
                "html": html,
                "citations_converted": prepared["conversion"].citations_converted,
                "warnings": prepared["warnings"],
            }
        finally:
            try:
                os.unlink(bib_path)
            except OSError:
                pass

    def build_bibliography_json(
        self,
        content: str,
        output_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Build a CSL-JSON bibliography file from draft content.

        Extracts all citation keys from the content and resolves them
        to CSL-JSON entries via the reference manager.

        Args:
            content: Markdown with any citation format.
            output_path: Optional path to write the .json file.

        Returns:
            List of CSL-JSON entries.
        """
        keys = extract_citation_keys(content)
        entries = []

        for key in keys:
            entry = self._resolve_citation_key(key)
            if entry:
                entries.append(entry)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(
                json.dumps(entries, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        return entries

    def _resolve_citation_key(self, key: str) -> dict[str, Any] | None:
        """
        Resolve a citation key to a CSL-JSON entry.

        Tries multiple strategies:
          1. Extract PMID from key (e.g., tang2023_38049909 → 38049909)
          2. Look up metadata in reference manager
          3. Convert to CSL-JSON format

        Args:
            key: Citation key (e.g., "tang2023_38049909")

        Returns:
            CSL-JSON dict or None if not found.
        """
        pmid = self._extract_pmid(key)
        if not pmid:
            return None

        metadata = self._ref_manager.get_metadata(pmid)
        if not metadata:
            return None

        # Build a minimal Reference-like object for CSL conversion
        # We use reference_to_csl_json which expects a Reference entity,
        # but we can construct a lightweight one from metadata
        from med_paper_assistant.domain.entities.reference import Reference

        ref = Reference(
            unique_id=pmid,
            title=metadata.get("title", ""),
            pmid=pmid,
            doi=metadata.get("doi", ""),
            authors=metadata.get("authors", []),
            authors_full=metadata.get("authors_full", []),
            journal=metadata.get("journal", ""),
            journal_abbrev=metadata.get("journal_abbrev", ""),
            year=int(metadata.get("year", 0) or 0),
            volume=metadata.get("volume", ""),
            issue=metadata.get("issue", ""),
            pages=metadata.get("pages", ""),
            citation_key=key,
        )

        # Use the citation_key as the CSL id so Pandoc can match [@key]
        return reference_to_csl_json(ref, ref_id=key)

    @staticmethod
    def _extract_pmid(key: str) -> str | None:
        """
        Extract PMID from a citation key.

        Patterns:
          tang2023_38049909  → 38049909
          PMID:38049909      → 38049909
          38049909           → 38049909
        """
        # author2024_PMID format
        if "_" in key:
            parts = key.split("_")
            candidate = parts[-1]
            if candidate.isdigit():
                return candidate

        # PMID:xxx
        if key.upper().startswith("PMID:"):
            return key.split(":")[1].strip()

        # Pure PMID
        if key.isdigit():
            return key

        return None
