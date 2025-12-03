"""
Project Management Tools Module

Provides tools for managing research paper projects.
Split into submodules for maintainability:
- crud: Create, list, switch, delete, get_current
- settings: update_settings, get_paper_types, update_status  
- exploration: start_exploration, convert_to_project
- diagrams: save_diagram, list_diagrams (Draw.io integration)
- workspace: VS Code integration for file opening/closing
"""

from mcp.server.fastmcp import FastMCP
from med_paper_assistant.infrastructure.persistence import ProjectManager

from .crud import register_crud_tools
from .settings import register_settings_tools
from .exploration import register_exploration_tools
from .diagrams import register_diagram_tools
from .workspace import register_workspace_tools


def register_project_tools(mcp: FastMCP, project_manager: ProjectManager):
    """Register all project management tools with the MCP server."""
    register_crud_tools(mcp, project_manager)
    register_settings_tools(mcp, project_manager)
    register_exploration_tools(mcp, project_manager)
    register_diagram_tools(mcp, project_manager)
    register_workspace_tools(mcp, project_manager)


__all__ = ["register_project_tools"]
