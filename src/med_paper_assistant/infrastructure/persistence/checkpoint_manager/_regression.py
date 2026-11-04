"""Phase regression tracking (e.g., Phase 7 → Phase 5 rewrite loops)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from ._io import CheckpointIOMixin

logger = structlog.get_logger()


class RegressionMixin(CheckpointIOMixin):
    """Record and clear pipeline regressions to earlier phases."""

    def save_phase_regression(
        self,
        from_phase: int,
        to_phase: int,
        reason: str,
        sections_to_rewrite: list[str] | None = None,
        original_scores: dict[str, Any] | None = None,
    ) -> None:
        """
        Record a pipeline regression (e.g., Phase 7 → Phase 5).

        Moves the pipeline back to an earlier phase, preserving context
        about why the regression happened and what needs to be redone.

        Args:
            from_phase: Phase we are regressing from.
            to_phase: Phase we are regressing to.
            reason: Human-readable explanation.
            sections_to_rewrite: Specific sections that need rewriting (Phase 5).
            original_scores: Quality scores before regression.
        """
        state = self.load() or self._empty_state()

        existing_regression = state.get("regression_context", {})
        regression_count = existing_regression.get("regression_count", 0) + 1

        state["regression_context"] = {
            "from_phase": from_phase,
            "to_phase": to_phase,
            "reason": reason,
            "sections_to_rewrite": sections_to_rewrite or [],
            "original_scores": original_scores or {},
            "regression_count": regression_count,
            "regressed_at": datetime.now().isoformat(),
        }

        state["last_completed_phase"] = to_phase - 1
        state["current_phase"] = to_phase
        state["current_phase_name"] = f"REGRESSION_TO_P{to_phase}"
        state["status"] = "regression"
        state["timestamp"] = datetime.now().isoformat()

        # Clear section approval for sections that need rewriting
        if sections_to_rewrite:
            section_progress = state.get("section_progress", {})
            for section in sections_to_rewrite:
                if section in section_progress:
                    section_progress[section]["approval_status"] = "pending"
                    section_progress[section]["user_feedback"] = ""

        state["history"].append(
            {
                "action": "phase_regression",
                "from_phase": from_phase,
                "to_phase": to_phase,
                "reason": reason,
                "sections_to_rewrite": sections_to_rewrite or [],
                "timestamp": datetime.now().isoformat(),
            }
        )

        self._write(state)
        logger.info(
            "Phase regression saved",
            from_phase=from_phase,
            to_phase=to_phase,
            reason=reason,
            sections=sections_to_rewrite,
        )

    def clear_regression_context(self) -> None:
        """Clear regression context after successful re-execution."""
        state = self.load()
        if state and "regression_context" in state:
            state.pop("regression_context", None)
            self._write(state)
