"""
Project CRUD Tools

Create, List, Switch, Get Current project operations.
"""

from mcp.server import MCPServer

from med_paper_assistant.infrastructure.persistence import ProjectManager

from ..._binding import register_handlers
from ..._shared import get_optional_tool_decorator
from .._deps import PROJECT_MANAGER
from .create import create_project
from .lifecycle import archive_project, delete_project
from .queries import get_current_project, list_projects, switch_project

CRUD_HANDLERS = (
    create_project,
    list_projects,
    switch_project,
    get_current_project,
    archive_project,
    delete_project,
)

__all__ = ["CRUD_HANDLERS", "register_crud_tools"]


def register_crud_tools(
    mcp: MCPServer,
    project_manager: ProjectManager,
    *,
    register_public_verbs: bool = True,
):
    """Register project CRUD tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)
    return register_handlers(tool, PROJECT_MANAGER.bind(project_manager, CRUD_HANDLERS))
