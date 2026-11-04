"""Stop hook: finalize the audit trail and remind the agent to sync memory."""

from __future__ import annotations

from .common import (
    HookContext,
    HookResult,
    Payload,
    append_audit,
    build_output,
    count_audit_lines,
    remove_session_context,
)

EVENT = "Stop"


def build_context(tool_count: int) -> str:
    return "\n".join(
        [
            "[SESSION ENDING] Before this session closes, ensure:",
            "1. sync_workspace_state(doing, next_action) — save current progress",
            "2. Update memory-bank/ (progress.md, activeContext.md) if significant work was done",
            "3. Update projects/{slug}/.memory/ (activeContext.md, progress.md) "
            "if working on a paper",
            f"4. Total tool calls this session: {tool_count}",
        ]
    )


def run(_payload: Payload, ctx: HookContext) -> HookResult:
    tool_count = count_audit_lines(ctx)
    append_audit(ctx, "session_end", tool_count=tool_count)
    remove_session_context(ctx)
    return build_output(EVENT, build_context(tool_count))
