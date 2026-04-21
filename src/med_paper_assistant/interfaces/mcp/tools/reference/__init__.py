"""
Reference Tools Module

Tools for reference management and citation formatting.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager, ReferenceManager
from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.interfaces.mcp.tool_surface import ToolSurface, uses_compact_tool_surface

from .manager import register_reference_manager_tools


def register_reference_tools(
    mcp: FastMCP,
    ref_manager: ReferenceManager,
    drafter: Drafter,
    project_manager: ProjectManager,
    *,
    tool_surface: ToolSurface = "full",
):
    """Register all reference-related tools with the MCP server."""
    register_reference_manager_tools(
        mcp,
        ref_manager,
        drafter,
        project_manager,
        register_public_verbs=not uses_compact_tool_surface(tool_surface),
    )


__all__ = ["register_reference_tools"]
