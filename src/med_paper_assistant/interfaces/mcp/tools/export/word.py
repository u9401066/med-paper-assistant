"""
Word Export Tools

Full Word export workflow with session management.
"""

import json
import re
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.domain.services.wikilink_validator import validate_wikilinks_in_content
from med_paper_assistant.infrastructure.services import Formatter, TemplateReader, WordWriter
from med_paper_assistant.shared.path_guard import PathGuardError, resolve_child_path

from .._shared import (
    get_optional_tool_decorator,
    resolve_project_context,
)

# Global state for document editing sessions
_active_documents: dict[str, dict] = {}


def get_active_documents() -> dict:
    """Get the active document sessions dictionary."""
    return _active_documents


def register_word_export_tools(
    mcp: FastMCP,
    formatter: Formatter,
    template_reader: TemplateReader,
    word_writer: WordWriter,
    *,
    register_public_verbs: bool = True,
):
    """Register Word export tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    def _resolve_session_project(
        session_id: str,
        project: Optional[str],
    ) -> tuple[Optional[dict], Optional[str]]:
        session = _active_documents.get(session_id)
        if session is None:
            return (
                None,
                f"Error: No active session '{session_id}'. Use start_document_session first.",
            )

        session_project = session.get("project")
        requested_project = project or session_project
        project_info, error_msg = resolve_project_context(
            requested_project,
            required_mode="manuscript",
        )
        if error_msg:
            return None, error_msg

        if session_project and project_info and project_info.get("slug") != session_project:
            return (
                None,
                "❌ This document session is bound to a different active project. "
                "Resume it from the original manuscript project or start a new session.",
            )

        return project_info, None

    @tool()
    def list_templates() -> str:
        """
        List all available Word templates in templates/ directory.
        """
        try:
            templates = template_reader.list_templates()
            if not templates:
                return "No templates found in templates/ directory."

            output = "📄 **Available Templates**\n\n"
            for t in templates:
                output += f"- {t}\n"
            return output
        except Exception as e:
            return f"Error listing templates: {str(e)}"

    @tool()
    def read_template(template_name: str) -> str:
        """
        Read a Word template's structure (sections, styles, word limits).

        Args:
            template_name: Template filename (e.g., "Type of the Paper.docx")
        """
        try:
            template_path = resolve_child_path(
                template_reader.templates_dir,
                template_name,
                field_name="template name",
                default_suffix=".docx",
                allowed_suffixes={".docx"},
            )
            return template_reader.get_template_summary(template_path.name)
        except PathGuardError as e:
            return f"Error: Invalid template name: {e}"
        except Exception as e:
            return f"Error reading template: {str(e)}"

    @tool()
    def start_document_session(
        template_name: str = "",
        session_id: str = "default",
        project: Optional[str] = None,
    ) -> str:
        """
        Start a document editing session, optionally from a Word template.

        Args:
            template_name: Template filename. If empty, creates a blank document.
            session_id: Unique session identifier (default: "default")
            project: Project slug (uses current if omitted)
        """
        project_info, error_msg = resolve_project_context(
            project,
            required_mode="manuscript",
        )
        if error_msg:
            return error_msg

        try:
            if template_name:
                template_path = resolve_child_path(
                    template_reader.templates_dir,
                    template_name,
                    field_name="template name",
                    default_suffix=".docx",
                    allowed_suffixes={".docx"},
                )
                if not template_path.exists():
                    return f"Error: Template not found: {template_name}"
                doc = word_writer.create_document_from_template(str(template_path))
                safe_template_name = template_path.name
            else:
                doc = word_writer.create_blank_document()
                safe_template_name = ""

            _active_documents[session_id] = {
                "doc": doc,
                "template": safe_template_name or "(blank)",
                "modifications": [],
                "project": (project_info or {}).get("slug"),
            }

            if safe_template_name:
                structure = template_reader.get_template_summary(safe_template_name)
                return (
                    f"✅ Document session '{session_id}' started with template: {safe_template_name}\n\n"
                    f"Project: {(project_info or {}).get('name', (project_info or {}).get('slug', 'Unknown'))}\n\n"
                    f"{structure}"
                )
            else:
                return (
                    f"✅ Document session '{session_id}' started with blank document. "
                    f"Project: {(project_info or {}).get('name', (project_info or {}).get('slug', 'Unknown'))}. "
                    "Use insert_section to add content."
                )
        except PathGuardError as e:
            return f"Error: Invalid template name: {e}"
        except Exception as e:
            return f"Error starting session: {str(e)}"

    @tool()
    def insert_section(
        session_id: str,
        section_name: str,
        content: str,
        mode: str = "replace",
        project: Optional[str] = None,
    ) -> str:
        """
        Insert content into a document section.

        Args:
            session_id: Session ID from start_document_session
            section_name: Target section (e.g., "Introduction")
            content: Text content to insert
            mode: "replace" or "append"
            project: Project slug (uses the session project if omitted)
        """
        project_info, error_msg = _resolve_session_project(session_id, project)
        if error_msg:
            return error_msg

        try:
            session = _active_documents[session_id]
            doc = session["doc"]

            # 🔧 Pre-check: 驗證並修復 wikilink 格式
            result, fixed_content = validate_wikilinks_in_content(content, auto_fix=True)
            wikilink_note = ""
            if result.auto_fixed > 0:
                wikilink_note = f"\n🔧 自動修復 {result.auto_fixed} 個 wikilink 格式錯誤"
            elif result.issues:
                wikilink_note = f"\n⚠️ 發現 {len(result.issues)} 個 wikilink 格式問題，請檢查"

            paragraphs = [p for p in fixed_content.split("\n") if p.strip()]
            clear_existing = mode == "replace"

            count = word_writer.insert_content_in_section(
                doc, section_name, paragraphs, clear_existing=clear_existing
            )

            session["modifications"].append(
                {"section": section_name, "paragraphs": count, "mode": mode}
            )

            word_count = word_writer.count_words_in_section(doc, section_name)

            return (
                f"✅ Inserted {count} paragraphs into '{section_name}' ({word_count} words)"
                f" for project {(project_info or {}).get('slug', 'unknown')}{wikilink_note}"
            )
        except Exception as e:
            return f"Error inserting section: {str(e)}"

    @tool()
    def verify_document(
        session_id: str,
        limits_json: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """
        Get document summary with all sections and word counts.
        Optionally check against word limits per section.

        Args:
            session_id: Session ID from start_document_session
            limits_json: Optional JSON with section word limits (e.g., '{"Abstract": 300, "Introduction": 800}')
            project: Project slug (uses the session project if omitted)
        """
        project_info, error_msg = _resolve_session_project(session_id, project)
        if error_msg:
            return error_msg

        try:
            session = _active_documents[session_id]
            doc = session["doc"]

            counts = word_writer.get_all_word_counts(doc)

            output = (
                f"📊 **Document Verification: {session['template']}**\n\n"
                f"Project: {(project_info or {}).get('name', (project_info or {}).get('slug', 'Unknown'))}\n\n"
            )
            output += "| Section | Word Count |\n"
            output += "|---------|------------|\n"

            total = 0
            for section, count in counts.items():
                output += f"| {section} | {count} |\n"
                total += count

            output += f"| **TOTAL** | **{total}** |\n\n"

            output += f"**Modifications made:** {len(session['modifications'])}\n"
            for mod in session["modifications"]:
                output += f"- {mod['section']}: {mod['paragraphs']} paragraphs ({mod['mode']})\n"

            # Word limit check if limits provided
            if limits_json:
                limits = {
                    "Abstract": 250,
                    "Introduction": 800,
                    "Methods": 1500,
                    "Materials and Methods": 1500,
                    "Results": 1500,
                    "Discussion": 1500,
                    "Conclusions": 300,
                }

                custom_limits = json.loads(limits_json)
                limits.update(custom_limits)

                output += "\n📏 **Word Limit Check**\n\n"
                output += "| Section | Words | Limit | Status |\n"
                output += "|---------|-------|-------|--------|\n"

                all_ok = True
                for section, count in counts.items():
                    limit = None
                    for limit_key, limit_val in limits.items():
                        if (
                            limit_key.lower() in section.lower()
                            or section.lower() in limit_key.lower()
                        ):
                            limit = limit_val
                            break

                    if limit:
                        if count <= limit:
                            status = "✅"
                        else:
                            status = f"⚠️ Over by {count - limit}"
                            all_ok = False
                        output += f"| {section} | {count} | {limit} | {status} |\n"
                    else:
                        output += f"| {section} | {count} | - | - |\n"

                if all_ok:
                    output += "\n✅ **All sections within word limits!**"
                else:
                    output += "\n⚠️ **Some sections exceed word limits.**"

            return output
        except Exception as e:
            return f"Error verifying document: {str(e)}"

    @tool()
    def save_document(
        session_id: str,
        output_filename: str,
        project: Optional[str] = None,
    ) -> str:
        """
        Save the document to Word file and close session.

        Performs a final safety check for residual [[wikilink]] citations
        that were never converted — these would appear as raw text in the
        exported Word file.

        Args:
            session_id: Session ID from start_document_session
            output_filename: Output file path
            project: Project slug (uses the session project if omitted)
        """
        project_info, error_msg = _resolve_session_project(session_id, project)
        if error_msg:
            return error_msg

        try:
            session = _active_documents[session_id]
            doc = session["doc"]
            project_paths = (project_info or {}).get("paths", {})
            project_root = Path(project_paths.get("root") or Path.cwd())
            exports_dir = project_root / "exports"
            output_path = resolve_child_path(
                exports_dir,
                output_filename,
                field_name="output filename",
                default_suffix=".docx",
                allowed_suffixes={".docx"},
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # ── Safety check: scan for residual [[wikilink]] citations ──
            residual_wikilinks: list[str] = []
            for paragraph in doc.paragraphs:
                found = re.findall(r"\[\[([^\]]+)\]\]", paragraph.text)
                residual_wikilinks.extend(found)

            warning_msg = ""
            if residual_wikilinks:
                unique = sorted(set(residual_wikilinks))
                warning_msg = (
                    f"\n\n⚠️ **Warning: {len(unique)} unresolved wikilink(s) "
                    f"found in document**\n"
                    f"These will appear as raw `[[...]]` text in the Word file:\n"
                )
                for wl in unique:
                    warning_msg += f"  - `[[{wl}]]`\n"
                warning_msg += (
                    "\nConsider using `sync_references()` to convert wikilinks before export."
                )

            path = word_writer.save_document(doc, str(output_path))

            del _active_documents[session_id]

            return (
                f"✅ Document saved successfully to: {path}\n\n"
                f"Project: {(project_info or {}).get('name', (project_info or {}).get('slug', 'Unknown'))}\n"
                f"Session '{session_id}' closed.{warning_msg}"
            )
        except PathGuardError as e:
            return f"Error: Invalid output filename: {e}"
        except Exception as e:
            return f"Error saving document: {str(e)}"

    return {
        "list_templates": list_templates,
        "read_template": read_template,
        "start_document_session": start_document_session,
        "insert_section": insert_section,
        "verify_document": verify_document,
        "save_document": save_document,
    }
