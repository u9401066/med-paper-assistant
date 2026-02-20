"""
Review Tools Module

Tools for manuscript formatting verification (includes consistency checks and submission checklist).

Migrated to Skills:
- critique (peer_review, check_reporting_guidelines) → .claude/skills/manuscript-review/SKILL.md
- submission preparation (cover letter, highlights, reviewer response) → .claude/skills/submission-preparation/SKILL.md
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import (
    ProjectManager,
    ReferenceManager,
)
from med_paper_assistant.infrastructure.services import Drafter

from .formatting import register_formatting_tools


def register_review_tools(
    mcp: FastMCP,
    drafter: Drafter,
    ref_manager: ReferenceManager,
    project_manager: Optional[ProjectManager] = None,
):
    """Register all review tools with the MCP server."""
    register_formatting_tools(mcp, drafter, ref_manager)


__all__ = ["register_review_tools"]
