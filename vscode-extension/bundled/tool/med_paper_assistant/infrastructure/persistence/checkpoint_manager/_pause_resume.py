"""Pipeline pause/resume with draft-edit detection."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from ._continuity import ContinuityMixin

logger = structlog.get_logger()


class PauseResumeMixin(ContinuityMixin):
    """Pause the pipeline, snapshot drafts, and resume with edit detection."""

    def save_pause(self, reason: str = "user_requested") -> None:
        """
        Pause the pipeline, recording current state and draft hashes.

        The draft hashes are used to detect user edits during the pause.
        """
        state = self.load() or self._empty_state()
        if state.get("status") == "paused" and state.get("pause_state"):
            return  # keep the original snapshot so edits made since the first pause stay detectable

        state["pause_state"] = {
            "paused_at": datetime.now().isoformat(),
            "reason": reason,
            "phase_at_pause": state.get("current_phase", state.get("last_completed_phase", -1)),
            "draft_hashes": self._compute_draft_hashes(),
        }
        state["status"] = "paused"
        state["timestamp"] = datetime.now().isoformat()

        state["history"].append(
            {
                "action": "pipeline_paused",
                "reason": reason,
                "phase": state["pause_state"]["phase_at_pause"],
                "timestamp": datetime.now().isoformat(),
            }
        )

        self._write(state)
        logger.info("Pipeline paused", reason=reason)

    def resume_from_pause(self) -> dict[str, Any]:
        """
        Resume the pipeline from a paused state.

        Compares current draft hashes with those at pause time to detect
        user edits made while the pipeline was paused.

        Returns:
            Dict with:
              - changed: bool — whether drafts were modified
              - changed_files: list[str] — filenames that changed
              - phase_at_pause: int — which phase was active
              - auto_resume: bool — whether the pipeline can continue without
                manual intervention (no edits detected)
              - next_action: str — the recommended continuity action
              - reason: str — human-readable rationale for the decision
        """
        state = self.load()
        if not state or state.get("status") != "paused":
            return {
                "changed": False,
                "changed_files": [],
                "phase_at_pause": -1,
                "auto_resume": False,
                "next_action": "no_pause_state_available",
                "reason": "No paused pipeline state is available",
            }

        pause_state = state.get("pause_state") or {}
        changed_files = self._detect_changed_files(pause_state.get("draft_hashes", {}))
        phase_at_pause = pause_state.get("phase_at_pause", -1)
        decision = self._continuity_decision(
            changed_files,
            phase_at_pause,
            prior_auto_resumes=self._consecutive_auto_resumes(state),
        )

        state["status"] = "in_progress"
        state["timestamp"] = datetime.now().isoformat()

        state["history"].append(
            {
                "action": "pipeline_resumed",
                "changed_files": changed_files,
                "auto_resume": decision["auto_resume"],
                "phase": phase_at_pause,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Keep pause_state for reference but mark as resumed
        state["pause_state"] = {**pause_state, "resumed_at": datetime.now().isoformat()}

        self._write(state)
        logger.info(
            "Pipeline resumed",
            changed_files=changed_files,
            auto_resume=decision["auto_resume"],
        )

        return {
            "changed": len(changed_files) > 0,
            "changed_files": changed_files,
            "phase_at_pause": phase_at_pause,
            "auto_resume": decision["auto_resume"],
            "next_action": decision["next_action"],
            "reason": decision["reason"],
        }
