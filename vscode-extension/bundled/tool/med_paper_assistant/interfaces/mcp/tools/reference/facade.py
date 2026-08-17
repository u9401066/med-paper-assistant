"""Consolidated reference-management facade for the compact MCP surface."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from mcp.server import MCPServer

from .._shared import facade_schema_json, invoke_tool_handler, normalize_facade_action

ToolMap = Mapping[str, Callable[..., Any]]


def register_reference_facade_tools(
    mcp: MCPServer,
    reference_tools: ToolMap,
) -> dict[str, Callable[..., Any]]:
    """Register the compact reference facade without replacing the safe direct save verb."""

    reference_tools = reference_tools or {}

    @mcp.tool()
    async def reference_action(
        action: str,
        article: dict[str, Any] | str | None = None,
        query: str = "",
        pmid: str = "",
        pmids: str = "",
        max_chars: int = 10000,
        pdf_content: str = "",
        style: str = "vancouver",
        journal: Optional[str] = None,
        confirm: bool = False,
        summary: str = "",
        methodology: str = "",
        key_findings: str = "",
        limitations: str = "",
        usage_sections: str = "",
        relevance_score: int = 0,
        project: Optional[str] = None,
    ) -> str:
        """Run reference fallback, retrieval, formatting, and analysis actions.

        Actions:
        - save_agent (unverified fallback only)
        - list (machine-readable action schema)
        - list_saved
        - search
        - details
        - fulltext
        - save_pdf
        - format
        - rebuild_aliases
        - delete
        - analysis_get
        - analysis_save

        Use the direct ``save_reference_mcp`` tool for verified PubMed saves.
        """
        aliases = {
            "actions": "list",
            "help": "list",
            "supported": "list",
            "save": "save_agent",
            "save_reference": "save_agent",
            "agent_save": "save_agent",
            "references": "list_saved",
            "saved": "list_saved",
            "list_references": "list_saved",
            "list_saved_references": "list_saved",
            "search_local": "search",
            "search_local_references": "search",
            "get_reference_details": "details",
            "read_reference_fulltext": "fulltext",
            "save_reference_pdf": "save_pdf",
            "format_references": "format",
            "rebuild_foam_aliases": "rebuild_aliases",
            "delete_reference": "delete",
            "get_reference_for_analysis": "analysis_get",
            "save_reference_analysis": "analysis_save",
        }
        normalized = normalize_facade_action(action, aliases)

        format_pmids = pmids or pmid
        action_specs: dict[str, tuple[str, dict[str, Any]]] = {
            "save_agent": (
                "save_reference",
                {"article": article, "project": project},
            ),
            "list_saved": (
                "list_saved_references",
                {"project": project},
            ),
            "search": (
                "search_local_references",
                {"query": query},
            ),
            "details": (
                "get_reference_details",
                {"pmid": pmid},
            ),
            "fulltext": (
                "read_reference_fulltext",
                {"pmid": pmid, "max_chars": max_chars},
            ),
            "save_pdf": (
                "save_reference_pdf",
                {"pmid": pmid, "pdf_content": pdf_content},
            ),
            "format": (
                "format_references",
                {"pmids": format_pmids, "style": style, "journal": journal},
            ),
            "rebuild_aliases": (
                "rebuild_foam_aliases",
                {"project": project},
            ),
            "delete": (
                "delete_reference",
                {"pmid": pmid, "confirm": confirm, "project": project},
            ),
            "analysis_get": (
                "get_reference_for_analysis",
                {"pmid": pmid, "project": project},
            ),
            "analysis_save": (
                "save_reference_analysis",
                {
                    "pmid": pmid,
                    "summary": summary,
                    "methodology": methodology,
                    "key_findings": key_findings,
                    "limitations": limitations,
                    "usage_sections": usage_sections,
                    "relevance_score": relevance_score,
                    "project": project,
                },
            ),
        }

        if normalized == "list":
            actions = {
                name: {
                    "handler": handler_name,
                    "params": sorted(kwargs),
                }
                for name, (handler_name, kwargs) in sorted(action_specs.items())
            }
            actions["list"] = {
                "handler": "facade_schema_json",
                "params": ["action"],
            }
            return facade_schema_json(
                tool="reference_action",
                actions=actions,
                aliases=aliases,
                notes=[
                    "Use action='list_saved' to list saved references.",
                    "Use direct save_reference_mcp(pmid) for verified saves; "
                    "save_agent is an unverified fallback.",
                ],
            )

        if normalized == "save_agent" and article is None:
            return "❌ save_agent requires `article` metadata."
        if normalized == "analysis_save" and not summary.strip():
            return "❌ analysis_save requires a non-empty `summary`."
        if normalized not in action_specs:
            supported = ", ".join(["list", *sorted(action_specs)])
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        handler_name, kwargs = action_specs[normalized]
        handler = reference_tools.get(handler_name)
        if handler is None:
            return f"❌ Reference facade misconfigured: missing handler '{handler_name}'"

        return str(await invoke_tool_handler(handler, **kwargs))

    return {"reference_action": reference_action}


__all__ = ["register_reference_facade_tools"]
