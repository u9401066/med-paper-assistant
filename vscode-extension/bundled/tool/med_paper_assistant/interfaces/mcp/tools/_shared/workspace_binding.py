"""Bind the running MCP server to the user's workspace folder.

MCP roots are deprecated (SEP-2577) and Agent Plugins clients start stdio
servers with the plugin root as their working directory, so the server cannot
always infer where the user's workspace is. The agent therefore passes the
workspace folder explicitly through ``workspace_state_action(action="bind")``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from med_paper_assistant.infrastructure.persistence import (
    get_project_manager,
    reset_workspace_state_manager,
)
from med_paper_assistant.shared.workspace_root import (
    SOURCE_CWD,
    SOURCE_PLUGIN_DATA,
    bind_workspace_root,
    describe_workspace_root,
)

from .tool_logging import initialize_tool_tracking

if TYPE_CHECKING:
    from med_paper_assistant.infrastructure.persistence import ProjectManager

_BIND_CALL = 'workspace_state_action(action="bind", workspace_dir="<absolute workspace path>")'


def bind_server_workspace(
    workspace_dir: str, project_manager: ProjectManager | None = None
) -> Path:
    """Bind the workspace root and rebind every component that caches it.

    Raises:
        ValueError: when ``workspace_dir`` is not an existing absolute directory
            outside the Agent Plugins package.
    """
    root = bind_workspace_root(workspace_dir)
    managers = [get_project_manager()]
    if project_manager is not None and project_manager is not managers[0]:
        managers.append(project_manager)
    for manager in managers:
        manager.rebind_base_path(root)
    reset_workspace_state_manager()
    initialize_tool_tracking(root)
    return root


def workspace_binding_info() -> dict[str, Any]:
    """Describe the active workspace root and whether the agent should bind it."""
    info = describe_workspace_root()
    hint = ""
    if info.source == SOURCE_PLUGIN_DATA:
        hint = (
            "MedPaper is using the plugin's private data folder because the client "
            "started it inside the plugin package. If the user has a workspace folder "
            f"open, call {_BIND_CALL} so projects are stored there."
        )
    elif info.source == SOURCE_CWD and not (info.path / "projects").is_dir():
        hint = (
            f"MedPaper fell back to its working directory ({info.path}), which has no "
            "projects/ folder. If this is not the user's workspace, call "
            f"{_BIND_CALL}."
        )
    return {"root": str(info.path), "source": info.source, "binding_hint": hint}


__all__ = ["bind_server_workspace", "workspace_binding_info"]
