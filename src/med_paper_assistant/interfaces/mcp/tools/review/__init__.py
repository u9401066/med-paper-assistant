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

from .audit_hooks import register_audit_hook_tools
from .formatting import register_formatting_tools
from .pipeline_gate import register_pipeline_tools
from .tool_health import register_tool_health_tools


def register_review_tools(
    mcp: FastMCP,
    drafter: Drafter,
    ref_manager: ReferenceManager,
    project_manager: Optional[ProjectManager] = None,
):
    """Register all review tools with the MCP server."""
    register_formatting_tools(mcp, drafter, ref_manager)
    if project_manager is not None:
        register_pipeline_tools(mcp, project_manager)
    register_audit_hook_tools(mcp)
    register_tool_health_tools(mcp)


__all__ = [
    "register_review_tools",
    "register_pipeline_tools",
    "register_audit_hook_tools",
    "register_tool_health_tools",
]
