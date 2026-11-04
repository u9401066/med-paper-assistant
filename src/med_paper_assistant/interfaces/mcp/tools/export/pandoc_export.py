"""
Pandoc Export Tools — Citation-aware export using ExportPipeline.

Converts [[wikilink]] citations → [@key] → formatted citations via Pandoc --citeproc.
Generates CSL-JSON bibliography automatically from local references.
"""

import json
import os
from collections.abc import Callable
from typing import Any, Optional

from mcp.server import MCPServer

from .._shared import (
    ensure_project_context,
    get_optional_tool_decorator,
    log_tool_call,
    log_tool_error,
    log_tool_result,
    resolve_project_context,
)
from .export_inputs import require_drafts_dir, resolve_export_inputs
from .pandoc_export_helpers import (
    _bibliography_report,
    _export_output_path,
    _export_report,
    _find_draft,
    _get_pipeline,
    _pre_export_gate_error,
    _prepare_export_path,
    _preview_report,
    _project_metadata,
    _read_draft,
    _resolve_output_path,
)

_DOCX_PANDOC_MISSING = (
    "❌ **Pandoc not available**\n\n"
    "Install Pandoc:\n"
    "- Windows: `winget install pandoc`\n"
    "- macOS: `brew install pandoc`\n"
    "- Python: `import pypandoc; pypandoc.download_pandoc()`"
)

_PDF_PANDOC_MISSING = (
    "❌ **Pandoc not available**\n\n"
    "Install Pandoc:\n"
    "- `sudo apt install pandoc texlive-latex-base`\n"
    "- macOS: `brew install pandoc basictex`"
)


def _project_guard(project: Optional[str]) -> str | None:
    """Return the workflow/project guard message, or None when the tool may proceed."""
    _, workflow_error = resolve_project_context(
        project,
        required_mode="manuscript",
    )
    if workflow_error:
        return workflow_error

    is_valid, msg, _ = ensure_project_context(project)
    if not is_valid:
        return msg
    return None


def _export_docx(
    draft_filename: str,
    output_filename: Optional[str],
    csl_style: str,
    reference_doc: Optional[str],
    project: Optional[str],
) -> str:
    log_tool_call("export_docx", {"draft": draft_filename, "style": csl_style, "project": project})

    blocked = _project_guard(project)
    if blocked is not None:
        return blocked

    try:
        pipeline, pm = _get_pipeline()

        if not pipeline._pandoc or not pipeline._pandoc.available:
            return _DOCX_PANDOC_MISSING

        draft = _find_draft(pm, draft_filename)
        if draft.error:
            return draft.error

        project_dir, csl_file, reference_doc_file = resolve_export_inputs(
            draft.drafts_dir, pipeline, csl_style, reference_doc
        )

        gate_error = _pre_export_gate_error("export_docx", draft.path, project_dir, draft_filename)
        if gate_error:
            return gate_error

        output_path = _export_output_path(draft, output_filename, ".docx")

        result = pipeline.export_docx(
            draft_path=draft.path,
            output_path=output_path,
            csl_style=csl_file,
            reference_doc=reference_doc_file,
            metadata=_project_metadata(pm, with_date=True),
        )

        output = _export_report("✅ **Document exported successfully**\n\n", result, csl_style)
        log_tool_result("export_docx", output_path, success=True)
        return output

    except Exception as e:
        log_tool_error("export_docx", e, {"draft": draft_filename})
        return f"❌ Export failed: {e}"


def _export_pdf(
    draft_filename: str,
    output_filename: Optional[str],
    csl_style: str,
    project: Optional[str],
) -> str:
    log_tool_call("export_pdf", {"draft": draft_filename, "style": csl_style, "project": project})

    blocked = _project_guard(project)
    if blocked is not None:
        return blocked

    try:
        pipeline, pm = _get_pipeline()

        if not pipeline._pandoc or not pipeline._pandoc.available:
            return _PDF_PANDOC_MISSING

        draft = _find_draft(pm, draft_filename)
        if draft.error:
            return draft.error

        project_dir, csl_file, _ = resolve_export_inputs(draft.drafts_dir, pipeline, csl_style)

        gate_error = _pre_export_gate_error("export_pdf", draft.path, project_dir, draft_filename)
        if gate_error:
            return gate_error

        output_path = _export_output_path(draft, output_filename, ".pdf")

        result = pipeline.export_pdf(
            draft_path=draft.path,
            output_path=output_path,
            csl_style=csl_file,
            metadata=_project_metadata(pm, with_date=False),
        )

        output = _export_report("✅ **PDF exported successfully**\n\n", result, csl_style)
        log_tool_result("export_pdf", output_path, success=True)
        return output

    except Exception as e:
        log_tool_error("export_pdf", e, {"draft": draft_filename})
        return f"❌ PDF export failed: {e}"


def _preview_citations(draft_filename: str, project: Optional[str]) -> str:
    log_tool_call("preview_citations", {"draft": draft_filename, "project": project})

    blocked = _project_guard(project)
    if blocked is not None:
        return blocked

    try:
        pipeline, pm = _get_pipeline()

        draft = _find_draft(pm, draft_filename)
        if draft.error:
            return draft.error

        prepared = pipeline.prepare_for_pandoc(_read_draft(draft.path))
        output = _preview_report(draft.safe_name, prepared)

        log_tool_result(
            "preview_citations", f"{len(prepared['citation_keys'])} citations", success=True
        )
        return output

    except Exception as e:
        log_tool_error("preview_citations", e, {"draft": draft_filename})
        return f"❌ Preview failed: {e}"


def _build_bibliography(
    draft_filename: str, output_filename: Optional[str], project: Optional[str]
) -> str:
    log_tool_call("build_bibliography", {"draft": draft_filename, "project": project})

    blocked = _project_guard(project)
    if blocked is not None:
        return blocked

    try:
        pipeline, pm = _get_pipeline()

        draft = _find_draft(pm, draft_filename)
        if draft.error:
            return draft.error

        content = _read_draft(draft.path)

        if not output_filename:
            output_filename = "bibliography.json"
        bib_path = _prepare_export_path(
            draft.drafts_dir, output_filename, ".json", "Bibliography filename"
        )

        entries = pipeline.build_bibliography_json(content, bib_path)
        output = _bibliography_report(bib_path, entries)

        log_tool_result("build_bibliography", bib_path, success=True)
        return output

    except Exception as e:
        log_tool_error("build_bibliography", e, {"draft": draft_filename})
        return f"❌ Build bibliography failed: {e}"


def inspect_docx_xml(
    output_filename: str,
    project: Optional[str] = None,
) -> str:
    """Run Phase 9 DOCX XML smoke inspection on an exported DOCX file."""
    log_tool_call("inspect_docx_xml", {"output": output_filename, "project": project})

    blocked = _project_guard(project)
    if blocked is not None:
        return blocked

    try:
        pipeline, pm = _get_pipeline()
        drafts_dir = require_drafts_dir(pm.get_project_paths())
        exports_dir = os.path.join(os.path.dirname(drafts_dir), "exports")
        _, docx_path = _resolve_output_path(
            exports_dir,
            output_filename,
            ".docx",
            field_name="DOCX filename",
        )
        result = pipeline.inspect_docx_xml_smoke(docx_path)
        log_tool_result("inspect_docx_xml", docx_path, success=bool(result.get("passed")))
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        log_tool_error("inspect_docx_xml", e, {"output": output_filename})
        return f"❌ DOCX XML inspection failed: {e}"


def _register_export_tools(tool: Callable[..., Any]) -> dict[str, Callable[..., Any]]:
    @tool()
    def export_docx(
        draft_filename: str,
        output_filename: Optional[str] = None,
        csl_style: str = "vancouver",
        reference_doc: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        DEPRECATED public verb. Prefer `export_document(action="docx", ...)`.

        Export a draft to Word (.docx) with properly formatted citations.

        Converts [[wikilink]] citations → [@key] → formatted citations via Pandoc citeproc.
        Automatically builds CSL-JSON bibliography from saved references.

        Args:
            draft_filename: Draft file name (e.g., "introduction.md")
            output_filename: Output file name (default: same name with .docx extension)
            csl_style: Citation style (vancouver, apa, nature, etc.)
            reference_doc: Optional Word template for styling
            project: Project slug (uses current project if omitted)
        """
        return _export_docx(draft_filename, output_filename, csl_style, reference_doc, project)

    @tool()
    def export_pdf(
        draft_filename: str,
        output_filename: Optional[str] = None,
        csl_style: str = "vancouver",
        project: Optional[str] = None,
    ) -> str:
        """
        DEPRECATED public verb. Prefer `export_document(action="pdf", ...)`.

        Export a draft to PDF with properly formatted citations.

        Requires a LaTeX engine (pdflatex, xelatex, or lualatex).
        Converts [[wikilink]] citations → [@key] → formatted citations via Pandoc citeproc.

        Args:
            draft_filename: Draft file name (e.g., "manuscript.md")
            output_filename: Output file name (default: same name with .pdf extension)
            csl_style: Citation style (vancouver, apa, nature, etc.)
            project: Project slug (uses current project if omitted)
        """
        return _export_pdf(draft_filename, output_filename, csl_style, project)

    return {"export_docx": export_docx, "export_pdf": export_pdf}


def _register_citation_tools(tool: Callable[..., Any]) -> dict[str, Callable[..., Any]]:
    @tool()
    def preview_citations(
        draft_filename: str,
        project: Optional[str] = None,
    ) -> str:
        """
        Preview how citations will be converted for Pandoc export.

        Shows the wikilink → [@key] mapping and bibliography entries
        without actually running Pandoc. Useful for checking before export.

        Args:
            draft_filename: Draft file name (e.g., "introduction.md")
            project: Project slug (uses current project if omitted)
        """
        return _preview_citations(draft_filename, project)

    @tool()
    def build_bibliography(
        draft_filename: str,
        output_filename: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Build a CSL-JSON bibliography file from a draft's citations.

        Extracts all citation keys from the draft and resolves them
        to CSL-JSON entries. The resulting file can be used with
        Pandoc --bibliography flag.

        Args:
            draft_filename: Draft file name (e.g., "introduction.md")
            output_filename: Output file name (default: bibliography.json)
            project: Project slug (uses current project if omitted)
        """
        return _build_bibliography(draft_filename, output_filename, project)

    return {"preview_citations": preview_citations, "build_bibliography": build_bibliography}


def register_pandoc_export_tools(
    mcp: MCPServer,
    *,
    register_public_verbs: bool = True,
):
    """Register Pandoc-based export tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    return {
        **_register_export_tools(tool),
        **_register_citation_tools(tool),
        "inspect_docx_xml": inspect_docx_xml,
    }
