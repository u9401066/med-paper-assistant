"""
Analysis Tools Module

Provides tools for data analysis, Table 1 generation, and statistical tests.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services.analyzer import Analyzer

from .table_one import register_table_one_tools
from .stats import register_stats_tools


def register_analysis_tools(mcp: FastMCP, analyzer: Analyzer):
    """Register all analysis-related tools with the MCP server."""
    register_table_one_tools(mcp, analyzer)
    register_stats_tools(mcp, analyzer)


__all__ = ["register_analysis_tools"]
