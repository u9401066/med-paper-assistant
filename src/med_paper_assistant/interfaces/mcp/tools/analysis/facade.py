"""Consolidated analysis facade tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from .._shared import invoke_tool_handler, normalize_facade_action

ToolMap = Mapping[str, Callable[..., Any]]


def register_analysis_facade_tools(
    mcp: FastMCP,
    stats_tools: ToolMap,
    table_one_tools: ToolMap,
    figure_tools: ToolMap,
) -> dict[str, Callable[..., Any]]:
    """Register one stable facade verb for compact analysis workflows."""

    stats_tools = stats_tools or {}
    table_one_tools = table_one_tools or {}
    figure_tools = figure_tools or {}

    @mcp.tool()
    async def analysis_action(
        action: str,
        filename: str = "",
        caption: str = "",
        asset_type: str = "",
        observations: str = "",
        rationale: str = "",
        proposed_caption: str = "",
        evidence_excerpt: str = "",
        figure_number: int = 0,
        table_number: int = 0,
        draft_filename: str = "",
        after_section: str = "",
        table_content: str = "",
        plot_type: str = "",
        x_var: str = "",
        y_var: str = "",
        hue_var: str = "",
        title: str = "",
        output_name: str = "",
        test_type: str = "",
        variables: str = "",
        group_var: str = "",
        group_col: str = "",
        continuous_cols: str = "",
        categorical_cols: str = "",
        project: Optional[str] = None,
    ) -> str:
        """
        Run data analysis and figure/table asset actions through one stable entrypoint.

        Actions:
        - analyze_dataset
        - run_statistical_test
        - create_plot
        - generate_table_one
        - review_asset
        - insert_figure
        - insert_table
        - list_assets
        - list
        """
        aliases = {
            "analyze": "analyze_dataset",
            "stats": "run_statistical_test",
            "statistical_test": "run_statistical_test",
            "plot": "create_plot",
            "table_one": "generate_table_one",
            "review_asset_for_insertion": "review_asset",
            "review_asset": "review_asset",
            "review": "review_asset",
            "figure": "insert_figure",
            "table": "insert_table",
            "assets": "list_assets",
            "list": "list_assets",
        }
        normalized = normalize_facade_action(action, aliases)

        action_specs: dict[str, tuple[ToolMap, str, dict[str, Any]]] = {
            "analyze_dataset": (
                stats_tools,
                "analyze_dataset",
                {"filename": filename, "project": project},
            ),
            "run_statistical_test": (
                stats_tools,
                "run_statistical_test",
                {
                    "filename": filename,
                    "test_type": test_type,
                    "variables": variables,
                    "group_var": group_var or None,
                    "project": project,
                },
            ),
            "create_plot": (
                stats_tools,
                "create_plot",
                {
                    "filename": filename,
                    "plot_type": plot_type,
                    "x_var": x_var,
                    "y_var": y_var or None,
                    "hue_var": hue_var or None,
                    "title": title or None,
                    "output_name": output_name or None,
                    "project": project,
                },
            ),
            "generate_table_one": (
                table_one_tools,
                "generate_table_one",
                {
                    "filename": filename,
                    "group_col": group_col,
                    "continuous_cols": continuous_cols,
                    "categorical_cols": categorical_cols,
                    "output_name": output_name or None,
                    "project": project,
                },
            ),
            "review_asset": (
                figure_tools,
                "review_asset_for_insertion",
                {
                    "asset_type": asset_type,
                    "filename": filename,
                    "observations": observations,
                    "rationale": rationale,
                    "proposed_caption": proposed_caption or caption,
                    "evidence_excerpt": evidence_excerpt,
                    "project": project,
                },
            ),
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

        if normalized not in action_specs:
            supported = ", ".join(sorted(action_specs))
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        tool_group, handler_name, kwargs = action_specs[normalized]
        handler = tool_group.get(handler_name)
        if handler is None:
            return f"❌ Analysis facade misconfigured: missing handler '{handler_name}'"

        return await invoke_tool_handler(handler, **kwargs)

    return {"analysis_action": analysis_action}


__all__ = ["register_analysis_facade_tools"]
