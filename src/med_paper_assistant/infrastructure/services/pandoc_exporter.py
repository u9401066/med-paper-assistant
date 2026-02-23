"""
Pandoc Document Exporter — Infrastructure Service.

Uses Pandoc (via pypandoc) for high-fidelity document conversion.
Replaces hand-written python-docx manipulation with Pandoc's native engine.

Supported conversions:
  Markdown → Word (.docx)   [primary]
  Markdown → PDF             [via LaTeX]
  Markdown → HTML
  Markdown → LaTeX

Key advantages over pure python-docx:
  - Native --reference-doc support (journal Word templates)
  - Native --csl for citation formatting in Pandoc's citeproc
  - Table/figure numbering, cross-references
  - Equation rendering (KaTeX/MathJax → LaTeX)
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import pypandoc

logger = logging.getLogger(__name__)

_TEMPLATES_CSL_DIR = Path(__file__).parents[4] / "templates" / "csl"


class PandocExporter:
    """
    Export documents using Pandoc.

    Usage:
        exporter = PandocExporter()
        exporter.markdown_to_docx("draft.md", "output.docx")
        exporter.markdown_to_docx("draft.md", "output.docx", reference_doc="template.docx")
    """

    def __init__(self) -> None:
        self._pandoc_available = self._check_pandoc()

    @property
    def available(self) -> bool:
        return self._pandoc_available

    @staticmethod
    def _check_pandoc() -> bool:
        """Check if Pandoc binary is available."""
        try:
            version = pypandoc.get_pandoc_version()
            logger.info("Pandoc %s available", version)
            return True
        except OSError:
            logger.warning(
                "Pandoc binary not found. Install via pypandoc.download_pandoc() "
                "or system package manager."
            )
            return False

    @staticmethod
    def get_pandoc_version() -> str | None:
        """Get Pandoc version string, or None if unavailable."""
        try:
            return pypandoc.get_pandoc_version()
        except OSError:
            return None

    def convert(
        self,
        source: str,
        to: str,
        *,
        source_format: str = "markdown",
        output_file: str | None = None,
        reference_doc: str | None = None,
        csl: str | None = None,
        bibliography: str | None = None,
        extra_args: list[str] | None = None,
        filters: list[str] | None = None,
    ) -> str:
        """
        Convert content using Pandoc.

        Args:
            source: Input text content
            to: Output format ('docx', 'pdf', 'html', 'latex')
            source_format: Input format (default: 'markdown')
            output_file: Path to write output (required for binary formats like docx/pdf)
            reference_doc: Path to Word template (.docx) for --reference-doc
            csl: CSL style name or path for --csl
            bibliography: Path to bibliography file (CSL-JSON, BibTeX, etc.)
            extra_args: Additional Pandoc CLI arguments
            filters: Pandoc filters to apply

        Returns:
            Output text (for text formats) or output file path (for binary formats)
        """
        if not self._pandoc_available:
            raise RuntimeError("Pandoc binary not available")

        args = list(extra_args or [])

        # --reference-doc for Word templates
        if reference_doc and os.path.isfile(reference_doc):
            args.extend(["--reference-doc", reference_doc])

        # --csl for citation styles
        csl_path = self._resolve_csl(csl) if csl else None
        if csl_path:
            args.extend(["--csl", csl_path])
            # Pandoc citeproc requires --citeproc filter
            if not filters:
                filters = []
            if "--citeproc" not in args:
                args.append("--citeproc")

        # --bibliography for Pandoc's built-in citeproc
        if bibliography and os.path.isfile(bibliography):
            args.extend(["--bibliography", bibliography])

        # Apply filters
        if filters:
            for f in filters:
                args.extend(["--filter", f])

        # Standalone for complete documents
        if "--standalone" not in args and "-s" not in args:
            args.append("--standalone")

        result = pypandoc.convert_text(
            source,
            to,
            format=source_format,
            outputfile=output_file,
            extra_args=args,
        )

        if output_file:
            return output_file
        return result

    def markdown_to_docx(
        self,
        source: str,
        output_path: str,
        *,
        reference_doc: str | None = None,
        csl: str | None = None,
        bibliography: str | None = None,
        extra_args: list[str] | None = None,
    ) -> str:
        """
        Convert Markdown to Word document.

        Args:
            source: Markdown content string
            output_path: Path to write the .docx file
            reference_doc: Path to Word template for styling
            csl: CSL style name or path
            bibliography: Path to bibliography file
            extra_args: Additional Pandoc arguments

        Returns:
            Path to the generated .docx file
        """
        # Ensure output directory exists
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        return self.convert(
            source,
            "docx",
            output_file=output_path,
            reference_doc=reference_doc,
            csl=csl,
            bibliography=bibliography,
            extra_args=extra_args,
        )

    def markdown_to_pdf(
        self,
        source: str,
        output_path: str,
        *,
        extra_args: list[str] | None = None,
    ) -> str:
        """
        Convert Markdown to PDF (requires LaTeX engine like xelatex).

        Args:
            source: Markdown content string
            output_path: Path to write the .pdf file
            extra_args: Additional Pandoc arguments

        Returns:
            Path to the generated .pdf file
        """
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        args = list(extra_args or [])
        # Use xelatex for CJK support if no engine specified
        if not any(a.startswith("--pdf-engine") for a in args):
            args.append("--pdf-engine=xelatex")

        return self.convert(
            source,
            "pdf",
            output_file=output_path,
            extra_args=args,
        )

    def markdown_to_html(
        self,
        source: str,
        *,
        csl: str | None = None,
        bibliography: str | None = None,
    ) -> str:
        """
        Convert Markdown to HTML string.

        Returns:
            HTML content as string
        """
        return self.convert(
            source,
            "html",
            csl=csl,
            bibliography=bibliography,
        )

    def markdown_file_to_docx(
        self,
        input_path: str,
        output_path: str,
        *,
        reference_doc: str | None = None,
        csl: str | None = None,
        bibliography: str | None = None,
    ) -> str:
        """
        Convert a Markdown file to Word document.

        Convenience method that reads a file and converts it.
        """
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        return self.markdown_to_docx(
            content,
            output_path,
            reference_doc=reference_doc,
            csl=csl,
            bibliography=bibliography,
        )

    def convert_with_csl_json_refs(
        self,
        source: str,
        output_path: str,
        csl_json_refs: list[dict[str, Any]],
        *,
        csl: str | None = None,
        reference_doc: str | None = None,
        to: str = "docx",
    ) -> str:
        """
        Convert with inline CSL-JSON references.

        Creates a temporary bibliography file and passes it to Pandoc's citeproc.
        References in the markdown should use [@id] syntax.

        Args:
            source: Markdown with [@ref-id] citations
            output_path: Output file path
            csl_json_refs: List of CSL-JSON reference dicts
            csl: CSL style name or path
            reference_doc: Word template path
            to: Output format

        Returns:
            Path to generated file
        """
        import json

        # Write CSL-JSON references to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(csl_json_refs, tmp, ensure_ascii=False)
            bib_path = tmp.name

        try:
            return self.convert(
                source,
                to,
                output_file=output_path,
                reference_doc=reference_doc,
                csl=csl,
                bibliography=bib_path,
            )
        finally:
            os.unlink(bib_path)

    @staticmethod
    def _resolve_csl(csl: str | None) -> str | None:
        """Resolve CSL style name to file path."""
        if not csl:
            return None

        # Direct file path
        if os.path.isfile(csl):
            return csl

        # templates/csl/{name}.csl
        candidate = _TEMPLATES_CSL_DIR / f"{csl}.csl"
        if candidate.is_file():
            return str(candidate)

        # Try without extension
        candidate = _TEMPLATES_CSL_DIR / csl
        if candidate.is_file():
            return str(candidate)

        logger.warning("CSL style '%s' not found", csl)
        return None
