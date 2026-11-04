"""``workspace_state_action`` facade handler."""

from __future__ import annotations

from typing import Any, Optional

from ..._shared import invoke_tool_handler, normalize_facade_action
from .deps import FACADE_DEPS, ToolMap

WORKSPACE_STATE_ALIASES = {
    "actions": "list",
    "help": "list",
    "recover": "get",
    "save": "sync",
    "set_workspace": "bind",
    "supported": "list",
}


def _list_actions() -> dict[str, Any]:
    return {
        "status": "ok",
        "action": "list",
        "schema": "mdpaper.facade_actions.v1",
        "tool": "workspace_state_action",
        "actions": {
            "get": {"handler": "get_workspace_state", "params": ["workspace_dir"]},
            "bind": {"handler": "get_workspace_state", "params": ["workspace_dir"]},
            "sync": {
                "handler": "sync_workspace_state",
                "params": ["doing", "next_action", "context", "clear"],
            },
            "checkpoint": {
                "handler": "checkpoint_writing_context",
                "params": ["section", "plan", "notes", "references_in_use"],
            },
        },
        "aliases": dict(WORKSPACE_STATE_ALIASES),
    }


def _missing_handler(name: str) -> dict[str, Any]:
    return {"status": "error", "message": f"Missing handler '{name}'"}


async def _get_state(
    tools: ToolMap, *, action: str = "get", workspace_dir: Optional[str] = None
) -> dict[str, Any]:
    handler = tools.get("get_workspace_state")
    if handler is None:
        return _missing_handler("get_workspace_state")
    if workspace_dir:
        result = await invoke_tool_handler(handler, workspace_dir=workspace_dir)
    else:
        result = await invoke_tool_handler(handler)
    return {"status": "ok", "action": action, **result}


async def _bind_state(tools: ToolMap, workspace_dir: Optional[str]) -> dict[str, Any]:
    if not workspace_dir:
        return {
            "status": "error",
            "action": "bind",
            "message": "workspace_dir is required: pass the absolute path of the "
            "user's workspace folder.",
        }
    return await _get_state(tools, action="bind", workspace_dir=workspace_dir)


async def _sync_state(
    tools: ToolMap,
    *,
    doing: Optional[str],
    next_action: Optional[str],
    context: Optional[str],
    clear: bool,
) -> dict[str, Any]:
    handler = tools.get("sync_workspace_state")
    if handler is None:
        return _missing_handler("sync_workspace_state")
    message = await invoke_tool_handler(
        handler,
        doing=doing,
        next_action=next_action,
        context=context,
        clear=clear,
    )
    return {"status": "ok", "action": "sync", "message": message}


async def _checkpoint_state(
    tools: ToolMap, *, section: str, plan: str, notes: str, references_in_use: str
) -> dict[str, Any]:
    handler = tools.get("checkpoint_writing_context")
    if handler is None:
        return _missing_handler("checkpoint_writing_context")
    message = await invoke_tool_handler(
        handler,
        section=section,
        plan=plan,
        notes=notes,
        references_in_use=references_in_use,
    )
    return {"status": "ok", "action": "checkpoint", "message": message}


async def workspace_state_action(
    action: str,
    workspace_dir: Optional[str] = None,
    doing: Optional[str] = None,
    next_action: Optional[str] = None,
    context: Optional[str] = None,
    clear: bool = False,
    section: str = "",
    plan: str = "",
    notes: str = "",
    references_in_use: str = "",
) -> dict[str, Any]:
    """
    Manage workspace recovery state through one stable entrypoint.

    Actions:
    - get: recovery summary plus the active workspace root and its source
    - bind: bind the server to workspace_dir (absolute path of the user's
      workspace folder), then return the same payload as get. Use it when
      get reports a workspace.binding_hint.
    - sync
    - checkpoint
    """
    normalized = normalize_facade_action(action, WORKSPACE_STATE_ALIASES)
    tools = FACADE_DEPS.get().workspace_state_tools

    if normalized == "list":
        return _list_actions()
    if normalized == "get":
        return await _get_state(tools, workspace_dir=workspace_dir)
    if normalized == "bind":
        return await _bind_state(tools, workspace_dir)
    if normalized == "sync":
        return await _sync_state(
            tools, doing=doing, next_action=next_action, context=context, clear=clear
        )
    if normalized == "checkpoint":
        return await _checkpoint_state(
            tools, section=section, plan=plan, notes=notes, references_in_use=references_in_use
        )

    return {
        "status": "error",
        "message": (
            f"Unsupported action '{action}'. Supported actions: bind, checkpoint, get, list, sync"
        ),
    }
