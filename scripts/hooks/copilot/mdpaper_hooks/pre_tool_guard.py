"""PreToolUse hook: mode-based file protection and destructive-command guard.

Decisions (deny/ask) are expressed only through the JSON output. Returning
``None`` means "no opinion" and the dispatcher turns it into the neutral
``{"continue": true}`` answer.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from .common import (
    CONTEXT_FILE,
    CROSS_PLATFORM_RE,
    HookContext,
    HookResult,
    Payload,
    append_audit,
    build_decision,
    first_alt,
    get_tool_input,
    get_tool_name,
    normalize_slashes,
)
from .workspace import read_mode_file, read_workspace_mode

EVENT = "PreToolUse"
GIT_BUDGET_SECONDS = 4.0
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

PROTECTED_PATH_RE = re.compile(
    r"(\.claude/|\.github/|src/|tests/|integrations/|AGENTS\.md|CONSTITUTION\.md"
    r"|ARCHITECTURE\.md|pyproject\.toml)"
)
EDIT_TOOL_RE = re.compile(
    r"editFiles|create_file|replace_string|multi_replace|write_file", re.IGNORECASE
)
TERMINAL_TOOL_RE = re.compile(r"terminal", re.IGNORECASE)
SAVE_REFERENCE_RE = re.compile(r"mcp_mdpaper_save_reference$", re.IGNORECASE)
DANGEROUS_COMMAND_RE = re.compile(
    r"(rm\s+-rf\s+/|DROP\s+TABLE|DROP\s+DATABASE|--no-verify|--force\s+push|git\s+push\s+--force)"
)
GIT_CONFIRM_RE = re.compile(r"(git\s+push|git\s+reset\s+--hard|git\s+tag\s+v[0-9])")
GIT_DIFF_COMMANDS = (
    ("diff", "--name-only", "--cached"),
    ("diff", "--name-only"),
    ("diff", "--name-only", "HEAD~1..HEAD"),
)


def current_mode(ctx: HookContext) -> str:
    """Mode from the session context, overridden by ``.copilot-mode.json``."""
    session_mode = read_mode_file(ctx.state_dir / CONTEXT_FILE)
    file_mode = read_workspace_mode(ctx.workspace_root)
    if file_mode is not None:
        return file_mode
    return "normal" if session_mode is None else session_mode


def _git_names(root: Path, args: tuple[str, ...], timeout: float) -> list[str]:
    try:
        completed = subprocess.run(  # noqa: S603 - fixed git binary, read-only diff arguments
            ["git", "-c", "core.quotepath=off", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=root,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def recent_cross_platform_changes(root: Path) -> list[str]:
    """Staged, unstaged and last-commit files that touch cross-platform code."""
    deadline = time.monotonic() + GIT_BUDGET_SECONDS
    names: set[str] = set()
    for args in GIT_DIFF_COMMANDS:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        names.update(_git_names(root, args, remaining))
    return sorted(name for name in names if CROSS_PLATFORM_RE.search(name))


def _protected_path_decision(tool: str, tool_input: Payload, mode: str) -> HookResult:
    if mode not in ("normal", "research") or not EDIT_TOOL_RE.search(tool):
        return None
    file_path = first_alt(
        tool_input.get("filePath"), tool_input.get("path"), tool_input.get("file")
    )
    if file_path and PROTECTED_PATH_RE.search(normalize_slashes(file_path)):
        reason = (
            f"PROTECTED PATH in {mode} mode: '{file_path}' is read-only. "
            "Switch to development mode first."
        )
        return build_decision(EVENT, "deny", reason)
    return None


def _git_confirmation(command: str, root: Path) -> HookResult:
    changed = recent_cross_platform_changes(root)
    if changed:
        reason = (
            "RELEASE/PUSH CHECK: recent cross-platform or installation files changed. "
            f"Confirm CI smoke matrix passed before running '{command}'."
        )
        context = "Changed files requiring smoke evidence:\n" + "\n".join(changed)
        return build_decision(EVENT, "ask", reason, context)
    return build_decision(EVENT, "ask", f"GIT OPERATION requires confirmation: '{command}'")


def _terminal_decision(tool: str, tool_input: Payload, root: Path) -> HookResult:
    if not TERMINAL_TOOL_RE.search(tool):
        return None
    command = first_alt(tool_input.get("command"))
    if not command:
        return None
    if DANGEROUS_COMMAND_RE.search(command):
        reason = (
            f"DESTRUCTIVE COMMAND BLOCKED: '{command}'. This operation is potentially "
            "dangerous and requires explicit user approval."
        )
        return build_decision(EVENT, "deny", reason)
    if GIT_CONFIRM_RE.search(command):
        return _git_confirmation(command, root)
    return None


def _save_reference_decision(tool: str) -> HookResult:
    if not SAVE_REFERENCE_RE.search(tool):
        return None
    return build_decision(
        EVENT,
        "ask",
        "CONSTITUTION RULE: Use save_reference_mcp(pmid) instead of save_reference(). "
        "save_reference is only for fallback when API is unavailable.",
        "save_reference_mcp fetches verified data directly from PubMed API, "
        "preventing metadata corruption.",
    )


def run(payload: Payload, ctx: HookContext) -> HookResult:
    tool = get_tool_name(payload)
    if not tool:
        return None
    tool_input = get_tool_input(payload)
    decision = (
        _protected_path_decision(tool, tool_input, current_mode(ctx))
        or _terminal_decision(tool, tool_input, ctx.workspace_root)
        or _save_reference_decision(tool)
    )
    if decision is not None:
        return decision
    append_audit(ctx, "pre_tool_use", tool=tool)
    return None
