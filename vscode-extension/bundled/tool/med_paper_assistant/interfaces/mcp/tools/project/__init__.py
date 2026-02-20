"""
Project Management Tools Module

Provides tools for managing research paper projects.
Split into submodules for maintainability:
- crud: create_project, list_projects, switch_project, get_current_project (with include_files)
- settings: update_project_settings (with status, citation_style)
- exploration: start_exploration, convert_exploration_to_project
- diagrams: save_diagram (with output_dir for standalone), list_diagrams
- workspace: open_project_files
- workspace_state: get_workspace_state, sync_workspace_state (with clear)
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager

from .crud import register_crud_tools
from .diagrams import register_diagram_tools
from .exploration import register_exploration_tools
from .settings import register_settings_tools
from .workspace import register_workspace_tools
from .workspace_state import register_workspace_state_tools


def register_project_tools(mcp: FastMCP, project_manager: ProjectManager):
    """Register all project management tools with the MCP server."""
    register_crud_tools(mcp, project_manager)
    register_settings_tools(mcp, project_manager)
    register_exploration_tools(mcp, project_manager)
    register_diagram_tools(mcp, project_manager)
    register_workspace_tools(mcp, project_manager)
    register_workspace_state_tools(mcp)  # Workspace state tools


__all__ = ["register_project_tools"]
