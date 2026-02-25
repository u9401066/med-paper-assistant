"""
Analysis Tools Module

Provides tools for data analysis, Table 1 generation, statistical tests,
and figure/table asset management.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.analyzer import Analyzer

from .figures import register_figure_tools
from .stats import register_stats_tools
from .table_one import register_table_one_tools


def register_analysis_tools(mcp: FastMCP, analyzer: Analyzer, drafter: Drafter):
    """Register all analysis-related tools with the MCP server."""
    register_table_one_tools(mcp, analyzer)
    register_stats_tools(mcp, analyzer)
    register_figure_tools(mcp, drafter)


__all__ = ["register_analysis_tools"]
