"""Shared helpers for the pipeline gate tools."""

from typing import Any

import structlog

from med_paper_assistant.infrastructure.persistence.workspace_state_manager import (
    get_workspace_state_manager,
)

from ..._shared import resolve_project_context

# Phase name mapping (shared across tools)
_PHASE_NAMES = {
    0: "Configuration",
    1: "Setup",
    2: "Literature",
    21: "Fulltext Ingestion",
    3: "Concept",
    4: "Planning",
    5: "Writing",
    6: "Audit",
    65: "Evolution Gate",
    7: "Autonomous Review",
    8: "Reference Sync",
    9: "Export",
    10: "Retrospective",
    11: "Final Delivery",
}
_ALL_PHASES = [0, 1, 2, 21, 3, 4, 5, 6, 65, 7, 8, 9, 10, 11]


def resolve_manuscript_project(
    project: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Resolve the project context required by every manuscript-path pipeline tool."""
    return resolve_project_context(project, required_mode="manuscript")


def _require_project_info(project_info: dict | None) -> dict:
    """Convert ensure_project_context output into an explicit runtime guard."""
    if project_info is None:
        raise RuntimeError(
            "Project context resolved without project metadata. "
            "Pass an explicit project slug or reselect the active project."
        )
    return project_info


def _sync_to_workspace_state(
    slug: str,
    phase: int,
    gate_passed: bool,
    gate_failures: list[str] | None = None,
    gate_details: dict | None = None,
    next_action: str | None = None,
    current_round: int | None = None,
    review_verdict: str | None = None,
) -> None:
    """
    Auto-sync pipeline state to per-project .mdpaper-state.json.

    This is the anti-compaction defense: even if the agent's context is
    summarized, the pipeline state is persisted on disk and will be
    recovered by get_workspace_state().
    """
    try:
        wsm = get_workspace_state_manager()
        # Read existing state to merge phases cumulatively
        existing_state = wsm.get_state()
        existing_pipeline = existing_state.get("pipeline_state", {})
        existing_passed = set(existing_pipeline.get("phases_passed", []))
        existing_remaining = set(existing_pipeline.get("phases_remaining", []))

        # Update cumulatively
        if gate_passed:
            existing_passed.add(phase)
            existing_remaining.discard(phase)
        else:
            existing_remaining.add(phase)

        wsm.sync_pipeline_state(
            project=slug,
            current_phase=phase,
            phase_name=_PHASE_NAMES.get(phase, "Unknown"),
            gate_passed=gate_passed,
            gate_failures=gate_failures,
            next_action=next_action,
            phases_passed=sorted(existing_passed),
            phases_remaining=sorted(existing_remaining),
            current_round=current_round,
            review_verdict=review_verdict,
            gate_details=gate_details,
        )
    except Exception:
        # Non-fatal: don't let state sync failure break the gate tool
        structlog.get_logger().debug("State sync failed (best-effort)", exc_info=True)  # nosec B110
