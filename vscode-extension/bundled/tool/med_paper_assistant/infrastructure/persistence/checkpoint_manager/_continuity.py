"""Continuity decisions: draft-change detection and bounded-autonomy resume rules."""

from __future__ import annotations

import hashlib
from typing import Any

from . import _models
from ._io import CheckpointIOMixin


class ContinuityMixin(CheckpointIOMixin):
    """Decide whether a paused or regressed pipeline may continue autonomously."""

    def get_continuity_plan(self) -> dict[str, Any]:
        """Return a continuity plan for seamless pipeline automation.

        Dispatches on the current checkpoint status so the agent always has a
        single, explicit "what happens next" decision:
        - paused: auto-resume when drafts are unchanged, otherwise review first.
        - regression: rewrite the flagged sections and continue autonomously,
          unless the regression count has exceeded the safe threshold.
        - anything else: no blocking continuity decision is pending.
        """
        state = self.load()
        if not state:
            return {
                "kind": "none",
                "auto_resume": False,
                "requires_human": False,
                "next_action": "no_checkpoint_available",
                "changed_files": [],
                "phase_at_pause": -1,
                "reason": "No checkpoint state is available",
            }

        status = state.get("status")
        if status == "paused":
            pause_state = state.get("pause_state", {})
            changed_files = self._detect_changed_files(pause_state.get("draft_hashes", {}))
            return self._continuity_decision(
                changed_files,
                pause_state.get("phase_at_pause", -1),
                prior_auto_resumes=self._consecutive_auto_resumes(state),
            )

        if status == "regression":
            return self._regression_continuity_decision(state.get("regression_context", {}))

        return {
            "kind": "none",
            "auto_resume": False,
            "requires_human": False,
            "next_action": "proceed",
            "changed_files": [],
            "phase_at_pause": -1,
            "reason": f"No pending continuity decision (status: {status})",
        }

    # Maximum auto-resumable regressions before a human checkpoint is required.
    # Mirrors the request_section_rewrite enforcement (max 2 regressions).
    MAX_AUTONOMOUS_REGRESSIONS = _models.MAX_AUTONOMOUS_REGRESSIONS

    # Maximum consecutive unattended auto-resumes before a periodic human
    # checkpoint is required (bounded-autonomy safeguard for the YOLO flow).
    MAX_CONSECUTIVE_AUTO_RESUMES = _models.MAX_CONSECUTIVE_AUTO_RESUMES

    def _regression_continuity_decision(self, regression_ctx: dict[str, Any]) -> dict[str, Any]:
        """Build the continuity decision for a regression state.

        Below the regression threshold the agent may rewrite the flagged
        sections and continue without asking. Above it, a human checkpoint is
        required to avoid an unbounded rewrite loop (CONSTITUTION: bounded
        autonomy).
        """
        count = regression_ctx.get("regression_count", 1)
        sections = regression_ctx.get("sections_to_rewrite", [])
        to_phase = regression_ctx.get("to_phase", -1)
        requires_human = count > self.MAX_AUTONOMOUS_REGRESSIONS

        if requires_human:
            reason = (
                f"Regression count {count} exceeds safe threshold "
                f"({self.MAX_AUTONOMOUS_REGRESSIONS}); human checkpoint required"
            )
            next_action = "escalate_to_human"
        else:
            reason = (
                f"Regression to Phase {to_phase}; rewrite {len(sections)} "
                "section(s) then continue autonomously"
            )
            next_action = "rewrite_sections_and_continue"

        return {
            "kind": "regression",
            "auto_resume": not requires_human,
            "requires_human": requires_human,
            "next_action": next_action,
            "changed_files": [],
            "phase_at_pause": to_phase,
            "to_phase": to_phase,
            "sections_to_rewrite": sections,
            "regression_count": count,
            "reason": reason,
        }

    def _continuity_decision(
        self,
        changed_files: list[str],
        phase_at_pause: int,
        prior_auto_resumes: int = 0,
    ) -> dict[str, Any]:
        """Build the seamless-resume decision shared by peek and resume paths.

        Single source of truth for the auto-resume rule: no draft edits since
        the pause means the pipeline can continue autonomously; any edit keeps
        the human-in-the-loop safeguard.

        Bounded autonomy (CONSTITUTION: autonomy must have boundaries): after
        ``MAX_CONSECUTIVE_AUTO_RESUMES`` unattended auto-resumes, a periodic
        human checkpoint is required even when no edits are detected, so the
        continuous-flow harness cannot loop forever without human oversight.
        """
        if changed_files:
            return {
                "kind": "paused",
                "auto_resume": False,
                "requires_human": True,
                "next_action": "review_changes_before_resume",
                "changed_files": changed_files,
                "phase_at_pause": phase_at_pause,
                "consecutive_auto_resumes": prior_auto_resumes,
                "reason": "Draft changes detected since pause",
            }

        if prior_auto_resumes >= self.MAX_CONSECUTIVE_AUTO_RESUMES:
            return {
                "kind": "paused",
                "auto_resume": False,
                "requires_human": True,
                "next_action": "periodic_human_checkpoint",
                "changed_files": [],
                "phase_at_pause": phase_at_pause,
                "consecutive_auto_resumes": prior_auto_resumes,
                "reason": (
                    f"{prior_auto_resumes} consecutive auto-resumes reached the "
                    f"safety budget ({self.MAX_CONSECUTIVE_AUTO_RESUMES}); "
                    "periodic human checkpoint required"
                ),
            }

        return {
            "kind": "paused",
            "auto_resume": True,
            "requires_human": False,
            "next_action": "continue_without_manual_intervention",
            "changed_files": [],
            "phase_at_pause": phase_at_pause,
            "consecutive_auto_resumes": prior_auto_resumes,
            "reason": "No draft changes detected since pause",
        }

    def _consecutive_auto_resumes(self, state: dict[str, Any]) -> int:
        """Count the run of unattended auto-resumes ending at the latest event.

        Walks the history backwards: ``pipeline_resumed`` entries flagged
        ``auto_resume`` extend the streak; intervening ``pipeline_paused``
        entries are skipped; any other event (a reviewed resume, a regression,
        a phase completion) resets the streak. This makes the budget reflect
        only genuinely unattended continuations.
        """
        count = 0
        for entry in reversed(state.get("history", [])):
            action = entry.get("action")
            if action == "pipeline_paused":
                continue
            if action == "pipeline_resumed":
                if entry.get("auto_resume"):
                    count += 1
                    continue
                break
            break
        return count

    def _detect_changed_files(self, old_hashes: dict[str, str]) -> list[str]:
        """Detect draft files that changed since a pause snapshot."""
        current_hashes = self._compute_draft_hashes()

        changed_files = []
        for filename, old_hash in old_hashes.items():
            new_hash = current_hashes.get(filename)
            if new_hash != old_hash:
                changed_files.append(filename)

        for filename in current_hashes:
            if filename not in old_hashes:
                changed_files.append(filename)

        return sorted(set(changed_files))

    def _compute_draft_hashes(self) -> dict[str, str]:
        """Compute MD5 hashes for all draft files in the project.

        Returns:
            Dict mapping filename → MD5 hex digest.
        """
        drafts_dir = self._project_dir / "drafts"
        hashes: dict[str, str] = {}

        if not drafts_dir.is_dir():
            return hashes

        for draft_file in sorted(drafts_dir.iterdir()):
            if draft_file.is_file() and draft_file.suffix == ".md":
                try:
                    content = draft_file.read_bytes()
                    hashes[draft_file.name] = hashlib.md5(
                        content, usedforsecurity=False
                    ).hexdigest()  # noqa: S324
                except OSError:
                    continue

        return hashes
