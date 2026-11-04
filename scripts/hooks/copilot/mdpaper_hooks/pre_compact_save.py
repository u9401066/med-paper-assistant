"""PreCompact hook: remind the agent to persist critical state before compaction."""

from __future__ import annotations

from .common import HookContext, HookResult, Payload, alt, build_output, count_audit_lines
from .workspace import mode_or_normal, read_state, writing_section

EVENT = "PreCompact"
ACTION_REQUIRED = (
    "ACTION REQUIRED: Before proceeding, call sync_workspace_state() and "
    "checkpoint_writing_context() if actively writing. Also call get_workspace_state() "
    "after compaction to recover full context."
)


def build_context(mode: str, state: Payload, tool_count: int) -> str:
    lines = [
        "[PRE-COMPACT CHECKPOINT] Context is being compacted. Critical state to preserve:",
        f"- Mode: {mode}",
    ]
    for label, value in (
        ("Doing", alt(state.get("doing"))),
        ("Next", alt(state.get("next_action"))),
        ("Project", alt(state.get("active_project"))),
        ("Writing", writing_section(state)),
    ):
        if value:
            lines.append(f"- {label}: {value}")
    lines.append(f"- Tool calls this session: {tool_count}")
    return "\n".join(lines) + "\n\n" + ACTION_REQUIRED


def run(_payload: Payload, ctx: HookContext) -> HookResult:
    root = ctx.workspace_root
    context = build_context(mode_or_normal(root), read_state(root), count_audit_lines(ctx))
    return build_output(EVENT, context)
