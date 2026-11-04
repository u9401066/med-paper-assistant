"""Shared helpers for the audit hook tools."""

from typing import Any

from ..._shared import resolve_project_context

# Minimum dimensions required for Phase 6 gate
MIN_SCORED_DIMENSIONS = 4


def _coerce_project_info(project_info: dict[str, Any] | None) -> dict[str, Any]:
    """Narrow resolved project context after workflow_error has been checked."""
    if project_info is None:
        raise ValueError("Project context unavailable")
    return project_info


# Minimum average score threshold
MIN_AVERAGE_SCORE = 1.0


def resolve_manuscript_project(
    project: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Resolve the project context required by every manuscript-path audit tool."""
    return resolve_project_context(project, required_mode="manuscript")
