"""Consolidated reference-management facade for the compact MCP surface."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from mcp.server import MCPServer

from .._shared import (
    facade_schema_json,
    format_unsupported_action_error,
    invoke_tool_handler,
    normalize_facade_action,
)

ToolMap = Mapping[str, Callable[..., Any]]

_REFERENCE_ALIASES: dict[str, str] = {
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
    "save_analysis": "analysis_save",
    "digest": "evidence_pack",
    "evidence": "evidence_pack",
    "pack": "evidence_pack",
    "synthesis_pack": "evidence_pack",
}


def _normalize_usage_sections(value: str | list[str]) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return value


def _analysis_and_pack_specs(
    params: dict[str, Any], usage_sections: str
) -> dict[str, tuple[str, dict[str, Any]]]:
    project = params["project"]
    return {
        "analysis_get": (
            "get_reference_for_analysis",
            {"pmid": params["pmid"], "project": project},
        ),
        "analysis_save": (
            "save_reference_analysis",
            {
                "pmid": params["pmid"],
                "summary": params["summary"],
                "methodology": params["methodology"],
                "key_findings": params["key_findings"],
                "limitations": params["limitations"],
                "usage_sections": usage_sections,
                "relevance_score": params["relevance_score"],
                "project": project,
            },
        ),
        "evidence_pack": (
            "get_reference_evidence_pack",
            {
                "usage_sections": usage_sections,
                "query": params["query"],
                "min_relevance": params["relevance_score"],
                "project": project,
            },
        ),
    }


def _build_reference_specs(params: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    usage_sections = _normalize_usage_sections(params["usage_sections"])
    format_pmids = params["pmids"] or params["pmid"]
    project = params["project"]
    return {
        "save_agent": ("save_reference", {"article": params["article"], "project": project}),
        "list_saved": ("list_saved_references", {"project": project}),
        "search": ("search_local_references", {"query": params["query"]}),
        "details": ("get_reference_details", {"pmid": params["pmid"]}),
        "fulltext": (
            "read_reference_fulltext",
            {"pmid": params["pmid"], "max_chars": params["max_chars"]},
        ),
        "save_pdf": (
            "save_reference_pdf",
            {"pmid": params["pmid"], "pdf_content": params["pdf_content"]},
        ),
        "format": (
            "format_references",
            {"pmids": format_pmids, "style": params["style"], "journal": params["journal"]},
        ),
        "rebuild_aliases": ("rebuild_foam_aliases", {"project": project}),
        "delete": (
            "delete_reference",
            {"pmid": params["pmid"], "confirm": params["confirm"], "project": project},
        ),
        **_analysis_and_pack_specs(params, usage_sections),
    }


def _reference_schema(action_specs: dict[str, tuple[str, dict[str, Any]]]) -> str:
    actions = {
        name: {"handler": handler_name, "params": sorted(kwargs)}
        for name, (handler_name, kwargs) in sorted(action_specs.items())
    }
    actions["list"] = {"handler": "facade_schema_json", "params": ["action"]}
    return facade_schema_json(
        tool="reference_action",
        actions=actions,
        aliases=_REFERENCE_ALIASES,
        notes=[
            "Use action='evidence_pack' for a single-call drafting digest of citation keys and findings.",
            "Use action='list_saved' to list saved references.",
            "Use direct save_reference_mcp(pmid) for verified saves; save_agent is an unverified fallback.",
        ],
    )


async def _dispatch_reference_action(
    reference_tools: ToolMap,
    action: str,
    params: dict[str, Any],
) -> str:
    normalized = normalize_facade_action(action, _REFERENCE_ALIASES)
    action_specs = _build_reference_specs(params)
    if normalized == "list":
        return _reference_schema(action_specs)
    if normalized == "save_agent" and params["article"] is None:
        return "❌ save_agent requires `article` metadata."
    if normalized == "analysis_save" and not str(params["summary"]).strip():
        return "❌ analysis_save requires a non-empty `summary`."
    if normalized not in action_specs:
        return format_unsupported_action_error(
            "reference_action",
            action,
            ["list", *action_specs],
            aliases=_REFERENCE_ALIASES,
        )
    handler_name, kwargs = action_specs[normalized]
    handler = reference_tools.get(handler_name)
    if handler is None:
        return f"❌ Reference facade misconfigured: missing handler '{handler_name}'"
    return str(await invoke_tool_handler(handler, **kwargs))


def register_reference_facade_tools(
    mcp: MCPServer,
    reference_tools: ToolMap,
) -> dict[str, Callable[..., Any]]:
    """Register the compact reference facade without replacing the safe direct save verb."""
    tools_map = reference_tools or {}

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
        usage_sections: str | list[str] = "",
        relevance_score: int = 0,
        project: Optional[str] = None,
    ) -> str:
        """Run reference fallback, retrieval, formatting, analysis, and evidence-pack actions.

        Actions: evidence_pack, save_agent, list, list_saved, search, details, fulltext,
        save_pdf, format, rebuild_aliases, delete, analysis_get, analysis_save.
        Use direct ``save_reference_mcp`` for verified PubMed saves.
        """
        params = dict(locals())
        params.pop("action", None)
        return await _dispatch_reference_action(tools_map, action, params)

    return {"reference_action": reference_action}


__all__ = ["register_reference_facade_tools"]
