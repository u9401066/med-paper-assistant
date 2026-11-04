"""
Project Settings Tools

Update settings, get paper types, update status, interactive setup.
"""

from mcp.server import MCPServer

from med_paper_assistant.infrastructure.persistence import ProjectManager

from ..._binding import register_handlers
from ..._shared import get_optional_tool_decorator
from .._deps import PROJECT_MANAGER
from .schemas import PaperTypeSchema, ProjectSetupSchema
from .setup import make_setup_project_interactive
from .update import update_authors, update_project_settings

__all__ = [
    "PaperTypeSchema",
    "ProjectSetupSchema",
    "register_settings_tools",
]


def register_settings_tools(
    mcp: MCPServer,
    project_manager: ProjectManager,
    *,
    register_public_verbs: bool = True,
):
    """Register project settings tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)
    update_settings, update_author_list = PROJECT_MANAGER.bind(
        project_manager, (update_project_settings, update_authors)
    )
    setup_interactive = make_setup_project_interactive(project_manager)
    return register_handlers(tool, [update_settings, setup_interactive, update_author_list])
