"""
Word Export Tools

Full Word export workflow with session management.
"""

from collections.abc import Callable
from typing import Any, Optional

from mcp.server import MCPServer

from med_paper_assistant.infrastructure.services import Formatter, TemplateReader, WordWriter
from med_paper_assistant.shared.path_guard import PathGuardError, resolve_child_path

from .._shared import (
    get_optional_tool_decorator,
    resolve_project_context,
)
from .word_helpers import (
    _create_session_document,
    _prepare_output_path,
    _project_label,
    _residual_wikilink_warning,
    _session_started_message,
    _verification_summary,
    _wikilink_note,
    _word_limit_report,
)

# Global state for document editing sessions
_active_documents: dict[str, dict] = {}


def get_active_documents() -> dict:
    """Get the active document sessions dictionary."""
    return _active_documents


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


def _list_templates(template_reader: TemplateReader) -> str:
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


def _read_template(template_reader: TemplateReader, template_name: str) -> str:
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


def _start_document_session(
    template_reader: TemplateReader,
    word_writer: WordWriter,
    template_name: str,
    session_id: str,
    project: Optional[str],
) -> str:
    project_info, error_msg = resolve_project_context(
        project,
        required_mode="manuscript",
    )
    if error_msg:
        return error_msg

    try:
        doc, safe_template_name, error = _create_session_document(
            template_reader, word_writer, template_name
        )
        if error:
            return error

        _active_documents[session_id] = {
            "doc": doc,
            "template": safe_template_name or "(blank)",
            "modifications": [],
            "project": (project_info or {}).get("slug"),
        }

        return _session_started_message(
            template_reader, project_info, session_id, safe_template_name
        )
    except PathGuardError as e:
        return f"Error: Invalid template name: {e}"
    except Exception as e:
        return f"Error starting session: {str(e)}"


def _insert_section(
    word_writer: WordWriter,
    session_id: str,
    section_name: str,
    content: str,
    mode: str,
    project: Optional[str],
) -> str:
    project_info, error_msg = _resolve_session_project(session_id, project)
    if error_msg:
        return error_msg

    try:
        session = _active_documents[session_id]
        doc = session["doc"]

        fixed_content, wikilink_note = _wikilink_note(content)

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


def _verify_document(
    word_writer: WordWriter,
    session_id: str,
    limits_json: Optional[str],
    project: Optional[str],
) -> str:
    project_info, error_msg = _resolve_session_project(session_id, project)
    if error_msg:
        return error_msg

    try:
        session = _active_documents[session_id]
        doc = session["doc"]

        counts = word_writer.get_all_word_counts(doc)

        output = _verification_summary(session, project_info, counts)

        # Word limit check if limits provided
        if limits_json:
            output += _word_limit_report(counts, limits_json)

        return output
    except Exception as e:
        return f"Error verifying document: {str(e)}"


def _save_document(
    word_writer: WordWriter,
    session_id: str,
    output_filename: str,
    project: Optional[str],
) -> str:
    project_info, error_msg = _resolve_session_project(session_id, project)
    if error_msg:
        return error_msg

    try:
        session = _active_documents[session_id]
        doc = session["doc"]
        output_path = _prepare_output_path(project_info, output_filename)

        warning_msg = _residual_wikilink_warning(doc)

        path = word_writer.save_document(doc, str(output_path))

        del _active_documents[session_id]

        return (
            f"✅ Document saved successfully to: {path}\n\n"
            f"Project: {_project_label(project_info)}\n"
            f"Session '{session_id}' closed.{warning_msg}"
        )
    except PathGuardError as e:
        return f"Error: Invalid output filename: {e}"
    except Exception as e:
        return f"Error saving document: {str(e)}"


def _register_template_tools(
    tool: Callable[..., Any], template_reader: TemplateReader
) -> dict[str, Callable[..., Any]]:
    @tool()
    def list_templates() -> str:
        """
        List all available Word templates in templates/ directory.
        """
        return _list_templates(template_reader)

    @tool()
    def read_template(template_name: str) -> str:
        """
        Read a Word template's structure (sections, styles, word limits).

        Args:
            template_name: Template filename (e.g., "Type of the Paper.docx")
        """
        return _read_template(template_reader, template_name)

    return {"list_templates": list_templates, "read_template": read_template}


def _register_session_tools(
    tool: Callable[..., Any], template_reader: TemplateReader, word_writer: WordWriter
) -> dict[str, Callable[..., Any]]:
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
        return _start_document_session(
            template_reader, word_writer, template_name, session_id, project
        )

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
        return _insert_section(word_writer, session_id, section_name, content, mode, project)

    return {"start_document_session": start_document_session, "insert_section": insert_section}


def _register_finish_tools(
    tool: Callable[..., Any], word_writer: WordWriter
) -> dict[str, Callable[..., Any]]:
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
        return _verify_document(word_writer, session_id, limits_json, project)

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
        return _save_document(word_writer, session_id, output_filename, project)

    return {"verify_document": verify_document, "save_document": save_document}


def register_word_export_tools(
    mcp: MCPServer,
    formatter: Formatter,
    template_reader: TemplateReader,
    word_writer: WordWriter,
    *,
    register_public_verbs: bool = True,
):
    """Register Word export tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    return {
        **_register_template_tools(tool, template_reader),
        **_register_session_tools(tool, template_reader, word_writer),
        **_register_finish_tools(tool, word_writer),
    }
