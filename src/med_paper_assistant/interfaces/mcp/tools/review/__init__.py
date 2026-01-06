"""
Review Tools Module

Tools for manuscript review, consistency checking, reviewer responses, and submission preparation.
- consistency: Check manuscript for consistency issues before submission
- response: Generate structured responses to reviewer comments
- submission: Cover letter, checklist, and highlights generation
- critique: Simulate peer review feedback (future)
- formatting: Verify journal formatting requirements (future)
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import (
    ProjectManager,
    ReferenceManager,
)
from med_paper_assistant.infrastructure.services import Drafter

from .consistency import register_consistency_tools
from .critique import register_critique_tools
from .formatting import register_formatting_tools
from .response import register_response_tools
from .submission import register_submission_tools


def register_review_tools(
    mcp: FastMCP,
    drafter: Drafter,
    ref_manager: ReferenceManager,
    project_manager: Optional[ProjectManager] = None,
):
    """Register all review tools with the MCP server."""
    register_consistency_tools(mcp, drafter, ref_manager)
    register_response_tools(mcp, drafter)
    if project_manager:
        register_submission_tools(mcp, project_manager)
    register_critique_tools(mcp)
    register_formatting_tools(mcp)


__all__ = ["register_review_tools"]
