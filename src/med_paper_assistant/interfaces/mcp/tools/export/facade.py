"""Consolidated export facade tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from .._shared import facade_schema_json, invoke_tool_handler, normalize_facade_action

ToolMap = Mapping[str, Callable[..., Any]]


def register_export_facade_tools(
    mcp: FastMCP,
    word_tools: ToolMap,
    pandoc_tools: ToolMap,
):
    """Register stable public verbs for export workflows."""

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
        aliases = {
            "actions": "list",
            "help": "list",
            "list": "list",
            "supported": "list",
            "word": "docx",
            "start": "session_start",
            "insert": "session_insert",
            "save": "session_save",
        }
        normalized = normalize_facade_action(action, aliases)
        action_specs: dict[str, tuple[ToolMap, str, dict[str, Any]]] = {
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

        if normalized == "list":
            return facade_schema_json(
                tool="export_document",
                actions={
                    name: {"handler": spec[1], "params": sorted(k for k in spec[2])}
                    for name, spec in sorted(action_specs.items())
                },
                aliases=aliases,
                notes=["Use inspect_export(action='list') for non-writing export inspection actions."],
            )

        if normalized not in action_specs:
            supported = ", ".join(sorted(action_specs))
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        tool_group, handler_name, kwargs = action_specs[normalized]
        handler = tool_group.get(handler_name)
        if handler is None:
            return f"❌ Export facade misconfigured: missing handler '{handler_name}'"

        return await invoke_tool_handler(handler, **kwargs)

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
        aliases = {
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
        normalized = normalize_facade_action(action, aliases)
        action_specs: dict[str, tuple[ToolMap, str, dict[str, Any]]] = {
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

        if normalized == "list":
            return facade_schema_json(
                tool="inspect_export",
                actions={
                    name: {"handler": spec[1], "params": sorted(k for k in spec[2])}
                    for name, spec in sorted(action_specs.items())
                },
                aliases=aliases,
                notes=["Use export_document(action='docx'|'pdf') to produce final files."],
            )

        if normalized not in action_specs:
            supported = ", ".join(sorted(action_specs))
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        tool_group, handler_name, kwargs = action_specs[normalized]
        handler = tool_group.get(handler_name)
        if handler is None:
            return f"❌ Export facade misconfigured: missing handler '{handler_name}'"

        return await invoke_tool_handler(handler, **kwargs)

    return {
        "export_document": export_document,
        "inspect_export": inspect_export,
    }
