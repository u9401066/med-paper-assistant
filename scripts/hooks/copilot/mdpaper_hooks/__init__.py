"""MedPaper Copilot lifecycle hooks, implemented in-process (stdlib only).

``hook_dispatch.py`` is the single entry point. Each hook module exposes
``run(payload, ctx) -> dict | None``; ``None`` means "nothing to add" and the
dispatcher answers with the neutral ``{"continue": true}``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from . import (
    post_tool_check,
    pre_compact_save,
    pre_tool_guard,
    prompt_analyzer,
    session_init,
    session_stop,
    subagent_init,
)
from .common import HookContext, HookResult, Payload, parse_payload

HookFunc = Callable[[Payload, HookContext], HookResult]

HOOKS: dict[str, HookFunc] = {
    "session-init": session_init.run,
    "prompt-analyzer": prompt_analyzer.run,
    "pre-tool-guard": pre_tool_guard.run,
    "post-tool-check": post_tool_check.run,
    "pre-compact-save": pre_compact_save.run,
    "subagent-init": subagent_init.run,
    "session-stop": session_stop.run,
}


def normalize_name(name: str) -> str:
    """``session_init``, ``Session-Init.sh`` and ``session-init`` are the same hook."""
    cleaned = name.strip().lower().replace("_", "-")
    return cleaned[: -len(".sh")] if cleaned.endswith(".sh") else cleaned


def run_hook(name: str, raw_payload: str, workspace_root: Path) -> HookResult:
    """Run one lifecycle hook; ``None`` for unknown names or when it has no output."""
    func = HOOKS.get(normalize_name(name))
    if func is None:
        return None
    return func(parse_payload(raw_payload), HookContext(workspace_root))
