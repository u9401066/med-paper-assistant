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
from med_paper_assistant.interfaces.mcp.tool_surface import ToolSurface, uses_compact_tool_surface

from .audit_hooks import register_audit_hook_tools
from .facade import register_review_facade_tools
from .formatting import register_formatting_tools
from .pipeline_gate import register_pipeline_tools
from .tool_health import register_tool_health_tools


def register_review_tools(
    mcp: FastMCP,
    drafter: Drafter,
    ref_manager: ReferenceManager,
    project_manager: Optional[ProjectManager] = None,
    *,
    tool_surface: ToolSurface = "full",
):
    """Register all review tools with the MCP server."""
    register_public_verbs = not uses_compact_tool_surface(tool_surface)
    formatting_tools = register_formatting_tools(
        mcp,
        drafter,
        ref_manager,
        register_public_verbs=register_public_verbs,
    )
    if project_manager is not None:
        pipeline_tools = register_pipeline_tools(
            mcp,
            project_manager,
            register_public_verbs=register_public_verbs,
        )
    else:
        pipeline_tools = {}
    audit_tools = register_audit_hook_tools(mcp, register_public_verbs=register_public_verbs)
    health_tools = register_tool_health_tools(
        mcp,
        register_public_verbs=register_public_verbs,
    )
    if pipeline_tools:
        register_review_facade_tools(
            mcp,
            audit_tools=audit_tools,
            pipeline_tools=pipeline_tools,
            formatting_tools=formatting_tools,
            health_tools=health_tools,
        )


__all__ = [
    "register_review_tools",
    "register_pipeline_tools",
    "register_audit_hook_tools",
    "register_review_facade_tools",
    "register_tool_health_tools",
]
