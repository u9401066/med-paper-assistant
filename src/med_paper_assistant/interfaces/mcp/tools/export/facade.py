"""Consolidated export facade tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from mcp.server import MCPServer

from .._shared import facade_schema_json, invoke_tool_handler, normalize_facade_action

ToolMap = Mapping[str, Callable[..., Any]]
ActionSpecs = dict[str, tuple[ToolMap, str, dict[str, Any]]]

_EXPORT_NOTE = "Use inspect_export(action='list') for non-writing export inspection actions."
_INSPECT_NOTE = "Use export_document(action='docx'|'pdf') to produce final files."

_EXPORT_ALIASES: dict[str, str] = {
    "actions": "list",
    "help": "list",
    "list": "list",
    "supported": "list",
    "word": "docx",
    "start": "session_start",
    "insert": "session_insert",
    "save": "session_save",
}

_INSPECT_ALIASES: dict[str, str] = {
    "actions": "list",
    "help": "list",
    "list": "list",
    "supported": "list",
    "templates": "list_templates",
    "template": "read_template",
    "verify": "verify_document",
    "preview": "preview_citations",
    "bibliography": "build_bibliography",
    "docx_smoke": "inspect_docx_xml",
    "xml_smoke": "inspect_docx_xml",
}


def _output_specs(
    pandoc_tools: ToolMap,
    draft_filename: str,
    output_filename: str,
    csl_style: str,
    reference_doc: str,
    project: Optional[str],
) -> ActionSpecs:
    return {
        "docx": (
            pandoc_tools,
            "export_docx",
            {
                "draft_filename": draft_filename,
                "output_filename": output_filename or None,
                "csl_style": csl_style,
                "reference_doc": reference_doc or None,
                "project": project,
            },
        ),
        "pdf": (
            pandoc_tools,
            "export_pdf",
            {
                "draft_filename": draft_filename,
                "output_filename": output_filename or None,
                "csl_style": csl_style,
                "project": project,
            },
        ),
    }


def _session_specs(
    word_tools: ToolMap,
    template_name: str,
    session_id: str,
    section_name: str,
    content: str,
    mode: str,
    output_filename: str,
    project: Optional[str],
) -> ActionSpecs:
    return {
        "session_start": (
            word_tools,
            "start_document_session",
            {
                "template_name": template_name,
                "session_id": session_id,
                "project": project,
            },
        ),
        "session_insert": (
            word_tools,
            "insert_section",
            {
                "session_id": session_id,
                "section_name": section_name,
                "content": content,
                "mode": mode,
                "project": project,
            },
        ),
        "session_save": (
            word_tools,
            "save_document",
            {
                "session_id": session_id,
                "output_filename": output_filename,
                "project": project,
            },
        ),
    }


def _word_inspect_specs(
    word_tools: ToolMap,
    template_name: str,
    session_id: str,
    limits_json: str,
    project: Optional[str],
) -> ActionSpecs:
    return {
        "list_templates": (word_tools, "list_templates", {}),
        "read_template": (
            word_tools,
            "read_template",
            {"template_name": template_name},
        ),
        "verify_document": (
            word_tools,
            "verify_document",
            {
                "session_id": session_id,
                "limits_json": limits_json or None,
                "project": project,
            },
        ),
    }


def _pandoc_inspect_specs(
    pandoc_tools: ToolMap,
    draft_filename: str,
    output_filename: str,
    project: Optional[str],
) -> ActionSpecs:
    return {
        "preview_citations": (
            pandoc_tools,
            "preview_citations",
            {"draft_filename": draft_filename, "project": project},
        ),
        "build_bibliography": (
            pandoc_tools,
            "build_bibliography",
            {
                "draft_filename": draft_filename,
                "output_filename": output_filename or None,
                "project": project,
            },
        ),
        "inspect_docx_xml": (
            pandoc_tools,
            "inspect_docx_xml",
            {"output_filename": output_filename, "project": project},
        ),
    }


async def _run_facade_action(
    tool_name: str,
    action: str,
    aliases: dict[str, str],
    action_specs: ActionSpecs,
    note: str,
) -> str:
    normalized = normalize_facade_action(action, aliases)

    if normalized == "list":
        return facade_schema_json(
            tool=tool_name,
            actions={
                name: {"handler": spec[1], "params": sorted(k for k in spec[2])}
                for name, spec in sorted(action_specs.items())
            },
            aliases=aliases,
            notes=[note],
        )

    if normalized not in action_specs:
        supported = ", ".join(sorted(action_specs))
        return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

    tool_group, handler_name, kwargs = action_specs[normalized]
    handler = tool_group.get(handler_name)
    if handler is None:
        return f"❌ Export facade misconfigured: missing handler '{handler_name}'"

    return await invoke_tool_handler(handler, **kwargs)


def _register_export_document(
    mcp: MCPServer, word_tools: ToolMap, pandoc_tools: ToolMap
) -> Callable[..., Any]:
    @mcp.tool()
    async def export_document(
        action: str,
        draft_filename: str = "",
        output_filename: str = "",
        csl_style: str = "vancouver",
        reference_doc: str = "",
        template_name: str = "",
        session_id: str = "default",
        section_name: str = "",
        content: str = "",
        mode: str = "replace",
        project: Optional[str] = None,
    ) -> str:
        """
        Run export-producing actions through one stable entrypoint.

        Actions:
        - docx
        - pdf
        - session_start
        - session_insert
        - session_save
        """
        action_specs = {
            **_output_specs(
                pandoc_tools, draft_filename, output_filename, csl_style, reference_doc, project
            ),
            **_session_specs(
                word_tools,
                template_name,
                session_id,
                section_name,
                content,
                mode,
                output_filename,
                project,
            ),
        }
        return await _run_facade_action(
            "export_document", action, _EXPORT_ALIASES, action_specs, _EXPORT_NOTE
        )

    return export_document


def _register_inspect_export(
    mcp: MCPServer, word_tools: ToolMap, pandoc_tools: ToolMap
) -> Callable[..., Any]:
    @mcp.tool()
    async def inspect_export(
        action: str,
        template_name: str = "",
        session_id: str = "default",
        limits_json: str = "",
        draft_filename: str = "",
        output_filename: str = "",
        project: Optional[str] = None,
    ) -> str:
        """
        Inspect export inputs and intermediate artifacts through one stable entrypoint.

        Actions:
        - list_templates
        - read_template
        - verify_document
        - inspect_docx_xml
        - preview_citations
        - build_bibliography
        """
        action_specs = {
            **_word_inspect_specs(word_tools, template_name, session_id, limits_json, project),
            **_pandoc_inspect_specs(pandoc_tools, draft_filename, output_filename, project),
        }
        return await _run_facade_action(
            "inspect_export", action, _INSPECT_ALIASES, action_specs, _INSPECT_NOTE
        )

    return inspect_export


def register_export_facade_tools(
    mcp: MCPServer,
    word_tools: ToolMap,
    pandoc_tools: ToolMap,
):
    """Register stable public verbs for export workflows."""
    export_document = _register_export_document(mcp, word_tools, pandoc_tools)
    inspect_export = _register_inspect_export(mcp, word_tools, pandoc_tools)

    return {
        "export_document": export_document,
        "inspect_export": inspect_export,
    }
