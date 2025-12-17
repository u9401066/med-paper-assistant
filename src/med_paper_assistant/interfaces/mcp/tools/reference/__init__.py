"""
Reference Tools Module

Tools for reference management and citation formatting.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager, ReferenceManager
from med_paper_assistant.infrastructure.services import Drafter

from .manager import register_reference_manager_tools


def register_reference_tools(
    mcp: FastMCP, ref_manager: ReferenceManager, drafter: Drafter, project_manager: ProjectManager
):
    """Register all reference-related tools with the MCP server."""
    register_reference_manager_tools(mcp, ref_manager, drafter, project_manager)


__all__ = ["register_reference_tools"]
