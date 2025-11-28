"""
Diagram Tools Module

Tools for saving and managing diagrams in research projects.
"""

from mcp.server.fastmcp import FastMCP
from med_paper_assistant.infrastructure.persistence import ProjectManager

from .drawio import register_drawio_tools


def register_diagram_tools(mcp: FastMCP, project_manager: ProjectManager):
    """Register all diagram-related tools with the MCP server."""
    register_drawio_tools(mcp, project_manager)


__all__ = ["register_diagram_tools"]
