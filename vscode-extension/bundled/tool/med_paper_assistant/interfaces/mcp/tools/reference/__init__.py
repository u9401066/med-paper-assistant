"""
Reference Tools Module

Tools for reference management and citation formatting.
"""

from mcp.server import MCPServer

from med_paper_assistant.infrastructure.persistence import ProjectManager, ReferenceManager
from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.interfaces.mcp.tool_surface import ToolSurface, uses_compact_tool_surface

from .facade import register_reference_facade_tools
from .manager import register_reference_manager_tools


def register_reference_tools(
    mcp: MCPServer,
    ref_manager: ReferenceManager,
    drafter: Drafter,
    project_manager: ProjectManager,
    *,
    tool_surface: ToolSurface = "full",
):
    """Register all reference-related tools with the MCP server."""
    compact_surface = uses_compact_tool_surface(tool_surface)
    manager_tools = register_reference_manager_tools(
        mcp,
        ref_manager,
        drafter,
        project_manager,
        register_public_verbs=not compact_surface,
    )
    facade_tools = {}
    if compact_surface:
        facade_tools = register_reference_facade_tools(
            mcp,
            reference_tools=manager_tools,
        )

    return {**manager_tools, **facade_tools}


__all__ = ["register_reference_tools"]
