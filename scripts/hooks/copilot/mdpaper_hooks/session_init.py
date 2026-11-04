"""SessionStart hook: inject mode, recovery, pending-evolution and project context."""

from __future__ import annotations

from pathlib import Path

from .common import (
    CONTEXT_FILE,
    HookContext,
    HookResult,
    Payload,
    alt,
    append_audit,
    build_output,
    remove_session_context,
    utc_timestamp,
    write_json,
)
from .workspace import (
    count_pending_evolutions,
    count_projects,
    read_state,
    read_workspace_mode,
    resolve_active_project,
    workflow_mode,
    writing_section,
)

PROTECTED_PATHS_NOTE = (
    "Research skills only. Protected paths: .claude/ .github/ src/ tests/ "
    "AGENTS.md CONSTITUTION.md pyproject.toml"
)
STATE_LABELS = (
    ("doing", "RECOVERY: Was doing '{}'"),
    ("next_action", "NEXT ACTION: {}"),
    ("active_project", "ACTIVE PROJECT: {}"),
)


def _mode_parts(mode: str | None) -> list[str]:
    if mode is None:
        return []
    parts = [f"MODE: {mode}"]
    if mode == "development":
        parts.append("All skills enabled. Static analysis ON.")
    elif mode in ("research", "normal"):
        parts.append(PROTECTED_PATHS_NOTE)
    return parts


def _state_parts(state: Payload) -> list[str]:
    parts: list[str] = []
    for key, template in STATE_LABELS:
        value = alt(state.get(key))
        if value and value != "null":
            parts.append(template.format(value))
    section = writing_section(state)
    if section and section != "null":
        parts.append(f"WRITING SESSION: section={section} (call get_workspace_state() for details)")
    return parts


def _project_parts(root: Path, state: Payload) -> tuple[list[str], str, str]:
    parts: list[str] = []
    count = count_projects(root)
    if count is not None:
        parts.append(f"PROJECTS: {count} active")
    project = resolve_active_project(root, state, prefer_current_file=False)
    mode = workflow_mode(root, project, on_error="manuscript")
    if mode:
        parts.append(f"WORKFLOW MODE: {mode}")
    return parts, project, mode


def run(_payload: Payload, ctx: HookContext) -> HookResult:
    root = ctx.workspace_root
    remove_session_context(ctx)

    mode = read_workspace_mode(root)
    state = read_state(root)
    parts = _mode_parts(mode) + _state_parts(state)

    pending = count_pending_evolutions(root)
    if pending > 0:
        parts.append(
            f"PENDING EVOLUTIONS: {pending} items (call get_workspace_state() for details)"
        )

    project_parts, project, wf_mode = _project_parts(root, state)
    parts += project_parts
    if not parts:
        return None

    append_audit(ctx, "session_start", mode=mode or "unknown")
    write_json(
        ctx.state_dir / CONTEXT_FILE,
        {
            "mode": mode or "normal",
            "active_project": project,
            "workflow_mode": wf_mode,
            "started_at": utc_timestamp(),
        },
    )
    return build_output("SessionStart", "\n".join(parts))
