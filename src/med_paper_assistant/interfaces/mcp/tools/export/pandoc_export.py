"""
Pandoc Export Tools — Citation-aware export using ExportPipeline.

Converts [[wikilink]] citations → [@key] → formatted citations via Pandoc --citeproc.
Generates CSL-JSON bibliography automatically from local references.
"""

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence.git_auto_committer import GitAutoCommitter

from .._shared import (
    ensure_project_context,
    log_tool_call,
    log_tool_error,
    log_tool_result,
)


def register_pandoc_export_tools(mcp: FastMCP):
    """Register Pandoc-based export tools."""

    def _get_pipeline():
        """Lazy-initialize ExportPipeline with current project context."""
        from med_paper_assistant.infrastructure.persistence import get_project_manager
        from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager
        from med_paper_assistant.application.export_pipeline import ExportPipeline
        from med_paper_assistant.infrastructure.services.pandoc_exporter import PandocExporter

        pm = get_project_manager()
        ref_manager = ReferenceManager(project_manager=pm)
        pandoc = PandocExporter()
        return ExportPipeline(ref_manager, pandoc), pm

    @mcp.tool()
    def export_docx(
        draft_filename: str,
        output_filename: Optional[str] = None,
        csl_style: str = "vancouver",
        reference_doc: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
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
        log_tool_call("export_docx", {
            "draft": draft_filename, "style": csl_style, "project": project,
        })

        # Ensure project context
        context_error = ensure_project_context(project, "export_docx")
        if context_error:
            return context_error

        try:
            pipeline, pm = _get_pipeline()

            if not pipeline._pandoc or not pipeline._pandoc.available:
                return (
                    "❌ **Pandoc not available**\n\n"
                    "Install Pandoc:\n"
                    "- Windows: `winget install pandoc`\n"
                    "- macOS: `brew install pandoc`\n"
                    "- Python: `import pypandoc; pypandoc.download_pandoc()`"
                )

            # Resolve paths
            paths = pm.get_project_paths()
            drafts_dir = paths.get("drafts", "drafts")
            draft_path = os.path.join(drafts_dir, draft_filename)

            if not os.path.exists(draft_path):
                return f"❌ Draft file not found: `{draft_filename}`"

            # Determine output path
            if not output_filename:
                base = os.path.splitext(draft_filename)[0]
                output_filename = f"{base}.docx"

            exports_dir = os.path.join(os.path.dirname(drafts_dir), "exports")
            os.makedirs(exports_dir, exist_ok=True)
            output_path = os.path.join(exports_dir, output_filename)

            # Run the export pipeline
            result = pipeline.export_docx(
                draft_path=draft_path,
                output_path=output_path,
                csl_style=csl_style,
                reference_doc=reference_doc,
            )

            # Build report
            output = "✅ **Document exported successfully**\n\n"
            output += f"📄 Output: `{result['output_path']}`\n"
            output += f"📚 Citations converted: {result['citations_converted']}\n"
            output += f"🎨 Citation style: {csl_style}\n"

            if result.get("citation_keys"):
                output += f"\n**Citation keys** ({len(result['citation_keys'])}):\n"
                for key in result["citation_keys"]:
                    output += f"- `{key}`\n"

            if result.get("warnings"):
                output += "\n⚠️ **Warnings:**\n"
                for w in result["warnings"]:
                    output += f"- {w}\n"

            log_tool_result("export_docx", output_path, success=True)
            return output

        except Exception as e:
            log_tool_error("export_docx", e, {"draft": draft_filename})
            return f"❌ Export failed: {e}"

    @mcp.tool()
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
        log_tool_call("preview_citations", {"draft": draft_filename, "project": project})

        context_error = ensure_project_context(project, "preview_citations")
        if context_error:
            return context_error

        try:
            pipeline, pm = _get_pipeline()

            # Resolve paths
            paths = pm.get_project_paths()
            drafts_dir = paths.get("drafts", "drafts")
            draft_path = os.path.join(drafts_dir, draft_filename)

            if not os.path.exists(draft_path):
                return f"❌ Draft file not found: `{draft_filename}`"

            with open(draft_path, "r", encoding="utf-8") as f:
                content = f.read()

            prepared = pipeline.prepare_for_pandoc(content)

            output = "📋 **Citation Preview**\n\n"
            output += f"📄 File: `{draft_filename}`\n"
            output += f"🔄 Citations converted: {prepared['conversion'].citations_converted}\n\n"

            if prepared["citation_keys"]:
                output += "**Citation keys found:**\n"
                for key in prepared["citation_keys"]:
                    output += f"- `[[{key}]]` → `[@{key}]`\n"

                output += f"\n**Bibliography entries resolved:** {len(prepared['bibliography'])} / {len(prepared['citation_keys'])}\n"

                if prepared["bibliography"]:
                    output += "\n**CSL-JSON preview:**\n"
                    for entry in prepared["bibliography"][:5]:
                        title = entry.get("title", "Unknown")[:80]
                        output += f"- `{entry.get('id', '?')}`: {title}\n"
                    if len(prepared["bibliography"]) > 5:
                        output += f"  ... and {len(prepared['bibliography']) - 5} more\n"
            else:
                output += "No citations found in this draft.\n"

            if prepared["warnings"]:
                output += "\n⚠️ **Warnings:**\n"
                for w in prepared["warnings"]:
                    output += f"- {w}\n"

            log_tool_result("preview_citations", f"{len(prepared['citation_keys'])} citations", success=True)
            return output

        except Exception as e:
            log_tool_error("preview_citations", e, {"draft": draft_filename})
            return f"❌ Preview failed: {e}"

    @mcp.tool()
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
        log_tool_call("build_bibliography", {"draft": draft_filename, "project": project})

        context_error = ensure_project_context(project, "build_bibliography")
        if context_error:
            return context_error

        try:
            pipeline, pm = _get_pipeline()

            paths = pm.get_project_paths()
            drafts_dir = paths.get("drafts", "drafts")
            draft_path = os.path.join(drafts_dir, draft_filename)

            if not os.path.exists(draft_path):
                return f"❌ Draft file not found: `{draft_filename}`"

            with open(draft_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not output_filename:
                output_filename = "bibliography.json"

            exports_dir = os.path.join(os.path.dirname(drafts_dir), "exports")
            os.makedirs(exports_dir, exist_ok=True)
            bib_path = os.path.join(exports_dir, output_filename)

            entries = pipeline.build_bibliography_json(content, bib_path)

            output = "✅ **Bibliography built successfully**\n\n"
            output += f"📄 Output: `{bib_path}`\n"
            output += f"📚 Entries: {len(entries)}\n\n"

            if entries:
                output += "**References:**\n"
                for entry in entries:
                    title = entry.get("title", "Unknown")[:80]
                    authors = entry.get("author", [])
                    first_author = authors[0].get("family", "?") if authors else "?"
                    year = entry.get("issued", {}).get("date-parts", [[None]])[0][0] or "?"
                    output += f"- {first_author} ({year}). {title}\n"

            log_tool_result("build_bibliography", bib_path, success=True)
            return output

        except Exception as e:
            log_tool_error("build_bibliography", e, {"draft": draft_filename})
            return f"❌ Build bibliography failed: {e}"
