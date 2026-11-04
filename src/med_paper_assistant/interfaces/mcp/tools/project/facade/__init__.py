"""Consolidated project/workspace facade tools."""

from __future__ import annotations

from mcp.server import MCPServer

from .deps import FACADE_DEPS, FacadeDeps, ToolMap
from .library_action import library_action
from .project_action import project_action
from .workspace_state_action import workspace_state_action


def register_project_facade_tools(
    mcp: MCPServer,
    crud_tools: ToolMap,
    settings_tools: ToolMap,
    exploration_tools: ToolMap,
    workspace_state_tools: ToolMap,
    library_tools: ToolMap | None = None,
    diagram_tools: ToolMap | None = None,
    workspace_tools: ToolMap | None = None,
):
    """Register stable public verbs for project and workspace state management."""

    deps = FacadeDeps(
        crud_tools=crud_tools,
        settings_tools=settings_tools,
        exploration_tools=exploration_tools,
        workspace_state_tools=workspace_state_tools,
        library_tools=library_tools or {},
        diagram_tools=diagram_tools or {},
        workspace_tools=workspace_tools or {},
    )
    project, library, workspace_state = FACADE_DEPS.bind(
        deps, [project_action, library_action, workspace_state_action]
    )

    registered_project = mcp.tool()(project)
    registered_library = mcp.tool()(library)
    registered_workspace_state = mcp.tool(structured_output=True)(workspace_state)

    return {
        "library_action": registered_library,
        "project_action": registered_project,
        "workspace_state_action": registered_workspace_state,
    }


__all__ = ["register_project_facade_tools"]
