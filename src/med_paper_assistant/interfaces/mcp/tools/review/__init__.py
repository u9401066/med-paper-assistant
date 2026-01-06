"""
Review Tools Module

Tools for manuscript review, consistency checking, and reviewer responses.
- consistency: Check manuscript for consistency issues before submission
- response: Generate structured responses to reviewer comments
- critique: Simulate peer review feedback (future)
- formatting: Verify journal formatting requirements (future)
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ReferenceManager
from med_paper_assistant.infrastructure.services import Drafter

from .consistency import register_consistency_tools
from .critique import register_critique_tools
from .formatting import register_formatting_tools
from .response import register_response_tools


def register_review_tools(
    mcp: FastMCP,
    drafter: Drafter,
    ref_manager: ReferenceManager,
):
    """Register all review tools with the MCP server."""
    register_consistency_tools(mcp, drafter, ref_manager)
    register_response_tools(mcp, drafter)
    register_critique_tools(mcp)
    register_formatting_tools(mcp)


__all__ = ["register_review_tools"]
