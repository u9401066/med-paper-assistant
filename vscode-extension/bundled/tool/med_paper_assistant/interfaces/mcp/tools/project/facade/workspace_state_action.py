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
    "supported": "list",
}


def _list_actions() -> dict[str, Any]:
    return {
        "status": "ok",
        "action": "list",
        "schema": "mdpaper.facade_actions.v1",
        "tool": "workspace_state_action",
        "actions": {
            "get": {"handler": "get_workspace_state", "params": []},
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


async def _get_state(tools: ToolMap) -> dict[str, Any]:
    handler = tools.get("get_workspace_state")
    if handler is None:
        return _missing_handler("get_workspace_state")
    result = await invoke_tool_handler(handler)
    return {"status": "ok", "action": "get", **result}


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
    - get
    - sync
    - checkpoint
    """
    normalized = normalize_facade_action(action, WORKSPACE_STATE_ALIASES)
    tools = FACADE_DEPS.get().workspace_state_tools

    if normalized == "list":
        return _list_actions()
    if normalized == "get":
        return await _get_state(tools)
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
            f"Unsupported action '{action}'. Supported actions: checkpoint, get, list, sync"
        ),
    }
