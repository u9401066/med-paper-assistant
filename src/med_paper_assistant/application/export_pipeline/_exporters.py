"""Document exports (DOCX, PDF, HTML) and post-export smoke checks."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

import structlog

from med_paper_assistant.shared import export_integrity

from ._bibliography import BibliographyMixin
from ._inputs import (
    PandocInputMixin,
    inject_pandoc_metadata,
    remove_quietly,
    write_temp_bibliography,
)

logger = structlog.get_logger(__package__)

# Fallback font for chars missing in DejaVu Serif (e.g. ✗)
_FALLBACK_FONT_PREAMBLE = (
    "\\newfontfamily\\fallbackfont{DejaVu Sans}\n"
    "\\usepackage{newunicodechar}\n"
    "\\newunicodechar{✗}{{\\fallbackfont ✗}}\n"
    "\\newunicodechar{✓}{{\\fallbackfont ✓}}\n"
)


def _raise_if_smoke_failed(label: str, post_export_checks: dict[str, Any]) -> None:
    if not post_export_checks.get("passed"):
        failed = [
            check["name"]
            for check in post_export_checks.get("checks", [])
            if not check.get("passed")
        ]
        raise RuntimeError(f"{label} export validation failed: " + ", ".join(failed))


def _export_result(
    prepared: dict[str, Any], result_path: str, post_export_checks: dict[str, Any]
) -> dict[str, Any]:
    return {
        "success": True,
        "output_path": result_path,
        "citations_converted": prepared["conversion"].citations_converted,
        "citations_resolved": len(prepared["bibliography"]),
        "citation_keys": prepared["citation_keys"],
        "warnings": prepared["warnings"],
        "post_export_checks": post_export_checks,
    }


def _write_font_preamble() -> str:
    preamble_file = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".tex",
        delete=False,
        encoding="utf-8",
    )
    preamble_file.write(_FALLBACK_FONT_PREAMBLE)
    preamble_path = preamble_file.name
    preamble_file.close()
    return preamble_path


def _build_pdf_args(
    pipeline: ExportFormatsMixin,
    draft_path: str,
    csl_style: str,
    extra_args: list[str] | None,
    bib_path: str,
) -> tuple[list[str], str | None]:
    """Build Pandoc PDF args; also return the font preamble temp file path, if any."""
    # Build args: CSL + bibliography + citeproc + user extras
    args = pipeline._build_resource_path_args(draft_path, extra_args)
    csl_path = pipeline._pandoc.resolve_csl(csl_style)
    if csl_path:
        args.extend(["--csl", csl_path])
    args.extend(["--bibliography", bib_path])
    if "--citeproc" not in args:
        args.append("--citeproc")

    # For lualatex/xelatex: use a Unicode-capable font + fallback
    engine = pipeline._pandoc.detect_pdf_engine()
    if engine not in ("lualatex", "xelatex"):
        return args, None

    if not any("mainfont" in a for a in args):
        args.extend(["-V", "mainfont=DejaVu Serif"])
    if not any("monofont" in a for a in args):
        args.extend(["-V", "monofont=DejaVu Sans Mono"])

    preamble_path = _write_font_preamble()
    args.extend(["-H", preamble_path])
    return args, preamble_path


def _prepare_export_inputs(
    pipeline: ExportFormatsMixin, draft_path: str, metadata: dict[str, Any] | None
) -> tuple[dict[str, Any], str, str]:
    """Shared DOCX/PDF front half: returns (prepared, pandoc_content, temp bibliography path)."""
    if not pipeline._pandoc.available:
        raise RuntimeError("Pandoc is not available. Install via pypandoc.download_pandoc()")

    # Read draft
    content = Path(draft_path).read_text(encoding="utf-8")

    # Prepare for Pandoc (citation conversion) — strict mode blocks on missing refs
    prepared = pipeline.prepare_for_pandoc(content, strict=True)

    if not prepared["bibliography"]:
        logger.warning("No bibliography entries found — citations won't be resolved")

    # Inject title/author metadata if provided
    pandoc_content = inject_pandoc_metadata(pipeline, prepared["content"], metadata)

    # Write temporary bibliography file
    bib_path = write_temp_bibliography(prepared["bibliography"])
    return prepared, pandoc_content, bib_path


class ExportFormatsMixin(BibliographyMixin, PandocInputMixin):
    """Exports prepared drafts to Word, PDF and HTML.

    Relies on ``self._pandoc`` (a ``DocumentExporterPort``) set by ``ExportPipeline``.
    """

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
        prepared, pandoc_content, bib_path = _prepare_export_inputs(self, draft_path, metadata)

        try:
            pandoc_args = self._build_resource_path_args(draft_path, extra_args)
            # Call Pandoc
            result_path = self._pandoc.markdown_to_docx(
                source=pandoc_content,
                output_path=output_path,
                csl=csl_style,
                bibliography=bib_path,
                reference_doc=reference_doc,
                extra_args=pandoc_args,
            )
            post_export_checks = self.inspect_docx_xml_smoke(result_path)
            _raise_if_smoke_failed("DOCX", post_export_checks)

            return _export_result(prepared, result_path, post_export_checks)
        finally:
            # Clean up temp file
            remove_quietly(bib_path)

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
        prepared, pandoc_content, bib_path = _prepare_export_inputs(self, draft_path, metadata)

        try:
            args, preamble_path = _build_pdf_args(self, draft_path, csl_style, extra_args, bib_path)

            # Strip internal emoji markers (🔒) that aren't in any system font
            pandoc_content = re.sub(r"[\U0001F512\U0001F916\u270F\u2728]", "", pandoc_content)

            result_path = self._pandoc.markdown_to_pdf(
                source=pandoc_content,
                output_path=output_path,
                extra_args=args,
            )
            post_export_checks = self.inspect_pdf_smoke(result_path)
            _raise_if_smoke_failed("PDF", post_export_checks)

            return _export_result(prepared, result_path, post_export_checks)
        finally:
            remove_quietly(bib_path)
            if preamble_path:
                remove_quietly(preamble_path)

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

        bib_path = write_temp_bibliography(prepared["bibliography"])

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
            remove_quietly(bib_path)

    @staticmethod
    def inspect_docx_xml_smoke(docx_path: str | Path) -> dict[str, Any]:
        """Delegate the public DOCX smoke API to the layer-neutral checker."""
        return export_integrity.inspect_docx_xml_smoke(docx_path)

    @staticmethod
    def inspect_pdf_smoke(pdf_path: str | Path) -> dict[str, Any]:
        """Delegate the public PDF smoke API to the layer-neutral checker."""
        return export_integrity.inspect_pdf_smoke(pdf_path)
