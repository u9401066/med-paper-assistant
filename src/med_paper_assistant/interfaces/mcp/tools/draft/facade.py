"""Consolidated draft facade tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services.drafter import (
    draft_filename_from_section,
    normalize_draft_filename,
)

from .._shared import invoke_tool_handler, normalize_facade_action

ToolMap = Mapping[str, Callable[..., Any]]


def register_draft_facade_tools(
    mcp: FastMCP,
    writing_tools: ToolMap,
    template_tools: ToolMap,
    editing_tools: ToolMap,
    citation_tools: ToolMap,
    figure_tools: ToolMap,
):
    """Register stable public verbs for manuscript drafting workflows."""

    writing_tools = writing_tools or {}
    template_tools = template_tools or {}
    editing_tools = editing_tools or {}
    citation_tools = citation_tools or {}
    figure_tools = figure_tools or {}

    @mcp.tool()
    async def draft_action(
        action: str,
        filename: str = "",
        caption: str = "",
        figure_number: int = 0,
        table_number: int = 0,
        draft_filename: str = "",
        after_section: str = "",
        content: str = "",
        table_content: str = "",
        topic: str = "",
        notes: str = "",
        target_text: str = "",
        pmid: str = "",
        section: str = "",
        old_text: str = "",
        new_text: str = "",
        claim_type: str = "general",
        max_results: int = 5,
        search_pubmed: bool = True,
        confirm: bool = False,
        project: Optional[str] = None,
    ) -> str:
        """
        Run manuscript drafting actions through one stable entrypoint.

        Actions:
        - check_order
        - draft_section
        - write
        - list
        - read
        - delete
        - insert_citation
        - sync_references
        - count_words
        - list_citations
        - patch
        - suggest_citations
        - scan_citations
        - insert_figure
        - insert_table
        - list_assets
        """
        aliases = {
            "order": "check_order",
            "check_writing_order": "check_order",
            "section": "draft_section",
            "create": "write",
            "update": "write",
            "write_draft": "write",
            "list_drafts": "list",
            "read_draft": "read",
            "delete_draft": "delete",
            "cite": "insert_citation",
            "sync": "sync_references",
            "words": "count_words",
            "citations": "list_citations",
            "available_citations": "list_citations",
            "get_available_citations": "list_citations",
            "edit": "patch",
            "patch_draft": "patch",
            "suggest": "suggest_citations",
            "scan_draft_citations": "scan_citations",
            "scan": "scan_citations",
            "review_asset_for_insertion": "review_asset",
            "review_asset": "review_asset",
            "review": "review_asset",
            "figure": "insert_figure",
            "table": "insert_table",
            "assets": "list_assets",
            "asset": "list_assets",
        }
        normalized = normalize_facade_action(action, aliases)

        write_filename = filename
        write_content = content
        count_filename = filename
        count_section = section or None

        if normalized == "write":
            write_filename = filename.strip() or draft_filename_from_section(section)
            write_content = content or new_text or notes
            if not write_filename:
                return "❌ Write action requires either `filename` or `section`."
            if not write_content.strip():
                return "❌ Write action requires non-empty `content`."
            try:
                write_filename = normalize_draft_filename(write_filename)
            except ValueError as e:
                return f"❌ Invalid draft filename: {e}"

        if normalized == "count_words":
            count_filename = filename.strip()
            if not count_filename and section:
                count_filename = draft_filename_from_section(section)
                count_section = None
            if not count_filename:
                return "❌ Count words requires either `filename` or `section`."
            try:
                count_filename = normalize_draft_filename(count_filename)
            except ValueError as e:
                return f"❌ Invalid draft filename: {e}"

        action_specs: dict[str, tuple[ToolMap, str, dict[str, Any]]] = {
            "check_order": (writing_tools, "check_writing_order", {"project": project}),
            "draft_section": (
                writing_tools,
                "draft_section",
                {"topic": topic, "notes": notes or content, "project": project},
            ),
            "write": (
                writing_tools,
                "write_draft",
                {"filename": write_filename, "content": write_content, "project": project},
            ),
            "list": (writing_tools, "list_drafts", {"project": project}),
            "read": (
                writing_tools,
                "read_draft",
                {"filename": filename, "project": project},
            ),
            "delete": (
                writing_tools,
                "delete_draft",
                {"filename": filename, "confirm": confirm, "project": project},
            ),
            "insert_citation": (
                template_tools,
                "insert_citation",
                {
                    "filename": filename,
                    "target_text": target_text,
                    "pmid": pmid,
                    "project": project,
                },
            ),
            "sync_references": (
                template_tools,
                "sync_references",
                {"filename": filename, "project": project},
            ),
            "count_words": (
                template_tools,
                "count_words",
                {"filename": count_filename, "section": count_section, "project": project},
            ),
            "list_citations": (
                editing_tools,
                "get_available_citations",
                {"project": project},
            ),
            "patch": (
                editing_tools,
                "patch_draft",
                {
                    "filename": filename,
                    "old_text": old_text,
                    "new_text": new_text or content,
                    "project": project,
                },
            ),
            "suggest_citations": (
                citation_tools,
                "suggest_citations",
                {
                    "text": content or notes,
                    "section": section,
                    "claim_type": claim_type,
                    "max_results": max_results,
                    "search_pubmed": search_pubmed,
                    "project": project,
                },
            ),
            "scan_citations": (
                citation_tools,
                "scan_draft_citations",
                {"filename": filename, "project": project},
            ),
        }
        if figure_tools:
            action_specs.update(
                {
                    "insert_figure": (
                        figure_tools,
                        "insert_figure",
                        {
                            "filename": filename,
                            "caption": caption,
                            "figure_number": figure_number or None,
                            "draft_filename": draft_filename or None,
                            "after_section": after_section or None,
                            "project": project,
                        },
                    ),
                    "insert_table": (
                        figure_tools,
                        "insert_table",
                        {
                            "filename": filename,
                            "caption": caption,
                            "table_number": table_number or None,
                            "table_content": table_content or None,
                            "draft_filename": draft_filename or None,
                            "after_section": after_section or None,
                            "project": project,
                        },
                    ),
                    "list_assets": (
                        figure_tools,
                        "list_assets",
                        {"project": project},
                    ),
                }
            )

        if normalized not in action_specs:
            supported = ", ".join(sorted(action_specs))
            if normalized in {"review_asset", "review_asset_for_insertion"}:
                return (
                    f"❌ Unsupported draft action '{action}'. "
                    "Use `analysis_action(action=\"review_asset\")` for "
                    "figure/table asset review."
                )
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        tool_group, handler_name, kwargs = action_specs[normalized]
        handler = tool_group.get(handler_name)
        if handler is None:
            return f"❌ Draft facade misconfigured: missing handler '{handler_name}'"

        return await invoke_tool_handler(handler, **kwargs)

    return {"draft_action": draft_action}


__all__ = ["register_draft_facade_tools"]
