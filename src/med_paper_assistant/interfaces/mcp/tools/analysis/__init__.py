"""
Analysis Tools Module

Provides tools for data analysis, Table 1 generation, statistical tests,
and figure/table asset management.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.analyzer import Analyzer
from med_paper_assistant.interfaces.mcp.tool_surface import ToolSurface, uses_compact_tool_surface

from .facade import register_analysis_facade_tools
from .figures import register_figure_tools
from .stats import register_stats_tools
from .table_one import register_table_one_tools


def register_analysis_tools(
    mcp: FastMCP,
    analyzer: Analyzer,
    drafter: Drafter,
    *,
    tool_surface: ToolSurface | None = None,
):
    """Register all analysis-related tools with the MCP server."""
    register_public_verbs = not uses_compact_tool_surface(tool_surface)

    table_one_tools = register_table_one_tools(
        mcp,
        analyzer,
        register_public_verbs=register_public_verbs,
    )
    stats_tools = register_stats_tools(
        mcp,
        analyzer,
        register_public_verbs=register_public_verbs,
    )
    figure_tools = register_figure_tools(
        mcp,
        drafter,
        register_public_verbs=register_public_verbs,
    )
    facade_tools = {}
    if uses_compact_tool_surface(tool_surface):
        facade_tools = register_analysis_facade_tools(
            mcp,
            stats_tools=stats_tools,
            table_one_tools=table_one_tools,
            figure_tools=figure_tools,
        )

    return {
        **table_one_tools,
        **stats_tools,
        **figure_tools,
        **facade_tools,
    }


__all__ = ["register_analysis_tools"]
