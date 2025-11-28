"""
Review Tools Module (Future)

Tools for peer review simulation and formatting checks.
- critique: Simulate peer review feedback
- check_formatting: Verify journal formatting requirements
- suggest_improvements: AI-powered writing suggestions
"""

from mcp.server.fastmcp import FastMCP

from .critique import register_critique_tools
from .formatting import register_formatting_tools


def register_review_tools(mcp: FastMCP):
    """Register all review tools with the MCP server."""
    register_critique_tools(mcp)
    register_formatting_tools(mcp)


__all__ = ["register_review_tools"]
