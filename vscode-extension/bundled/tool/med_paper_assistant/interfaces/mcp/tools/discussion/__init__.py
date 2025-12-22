"""
Discussion Tools Module (Future)

Tools for academic debate and viewpoint comparison.
- debate_topic: Simulate academic debate on a research topic
- compare_viewpoints: Compare different theoretical perspectives
- devils_advocate: Challenge assumptions in research design
"""

from mcp.server.fastmcp import FastMCP

from .debate import register_debate_tools


def register_discussion_tools(mcp: FastMCP):
    """Register all discussion tools with the MCP server."""
    register_debate_tools(mcp)


__all__ = ["register_discussion_tools"]
