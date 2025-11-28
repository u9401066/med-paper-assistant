"""
Analysis Tools Module

Provides tools for data analysis, statistical tests, and visualization.
Split into submodules:
- statistics: analyze_dataset, run_statistical_test, generate_table_one
- visualization: create_plot (future: more chart types)
"""

from mcp.server.fastmcp import FastMCP
from med_paper_assistant.infrastructure.services import Analyzer

from .statistics import register_statistics_tools
from .visualization import register_visualization_tools


def register_analysis_tools(mcp: FastMCP, analyzer: Analyzer):
    """Register all analysis-related tools with the MCP server."""
    register_statistics_tools(mcp, analyzer)
    register_visualization_tools(mcp, analyzer)


__all__ = ["register_analysis_tools"]
