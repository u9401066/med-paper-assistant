"""record_hook_event tool."""

import re
from pathlib import Path
from typing import Literal, Optional, cast

from med_paper_assistant.infrastructure.persistence.hook_effectiveness_tracker import (
    HookEffectivenessTracker,
)

from ..._shared import log_tool_call, log_tool_error, log_tool_result
from .._tool_doc import nested_tool_doc
from ._common import _coerce_project_info, resolve_manuscript_project


def _invalid_event_error(hook_id: str, event_type: str) -> str | None:
    """Return the validation error for a malformed event type or hook id, if any."""
    valid_events = ("trigger", "pass", "fix", "false_positive")
    if event_type not in valid_events:
        return f"❌ Invalid event_type '{event_type}'. Must be one of: {', '.join(valid_events)}"

    # Validate hook_id format: letter prefix + number (e.g., A1, B5, C3, P8)
    if not re.match(r"^[A-Z]\d{1,2}$", hook_id):
        return f"❌ Invalid hook_id '{hook_id}'. Must be a letter + 1-2 digits (e.g., 'A1', 'B5', 'C3')"
    return None


def _stats_lines(tracker: HookEffectivenessTracker, hook_id: str, event_type: str) -> list[str]:
    """Current stats of the recorded hook, in TOON format."""
    # Return current stats for this hook (TOON format)
    stats = tracker.get_stats(hook_id)
    lines = [
        "status: ok",
        f"hook: {hook_id}",
        f"event: {event_type}",
        "stats[1]{triggers,passes,fixes,false_positives,trigger_rate,fix_rate}:",
        f"  {stats.get('trigger', 0)},{stats.get('pass', 0)},{stats.get('fix', 0)},{stats.get('false_positive', 0)},{stats.get('trigger_rate', 0):.0%},{stats.get('fix_rate', 0):.0%}",
    ]
    return lines


@nested_tool_doc
def record_hook_event(
    hook_id: str,
    event_type: str,
    project: Optional[str] = None,
) -> str:
    """
    📊 Record a hook evaluation outcome.

    Call this AFTER evaluating each hook (A1-A4, B1-B7, C1-C8, etc.)
    to record whether the hook triggered, passed, required a fix,
    or produced a false positive.

    This is CODE-ENFORCED — Phase 6 gate validates that hook events
    were actually recorded. You cannot skip this.

    Args:
        hook_id: Hook identifier (e.g., "A1", "B5", "C3", "E2")
        event_type: One of "trigger", "pass", "fix", "false_positive"
        project: Project slug (optional, uses current project)

    Returns:
        Current stats for the recorded hook
    """
    log_tool_call(
        "record_hook_event", {"hook_id": hook_id, "event_type": event_type, "project": project}
    )
    try:
        error = _invalid_event_error(hook_id, event_type)
        if error:
            return error
        project_info, workflow_error = resolve_manuscript_project(project)
        if workflow_error:
            return workflow_error
        project_info = _coerce_project_info(project_info)
        project_dir = Path(project_info["project_path"])
        audit_dir = project_dir / ".audit"
        tracker = HookEffectivenessTracker(audit_dir)
        tracker.record_event(
            hook_id,
            cast(Literal["trigger", "pass", "fix", "false_positive"], event_type),
        )
        result = "\n".join(_stats_lines(tracker, hook_id, event_type))
        log_tool_result("record_hook_event", f"{hook_id}={event_type}")
        return result

    except Exception as e:
        log_tool_error("record_hook_event", e)
        return f"❌ Error recording hook event: {e}"
