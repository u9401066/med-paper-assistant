"""
Pipeline Checkpoint Manager — Save/restore auto-paper pipeline state.

Implements the checkpoint.json spec from auto-paper SKILL.md.
Enables interrupted pipelines to resume from the last completed phase.
Supports phase regression, pause/resume with edit detection, and
per-section user approval tracking.

Architecture:
  Infrastructure layer service. Called by auto-paper pipeline at phase transitions.
  Stores to: projects/{slug}/.audit/checkpoint.json

Design rationale (CONSTITUTION §22):
  - Auditable: every phase transition is recorded
  - Recomposable: resume from any phase
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class CheckpointManager:
    """
    Save and restore pipeline checkpoint state.

    Usage:
        ckpt = CheckpointManager(audit_dir="projects/my-paper/.audit")

        # Save after completing a phase:
        ckpt.save_phase_completion(
            phase=2,
            phase_name="LITERATURE_SEARCH",
            outputs={"refs_saved": 15, "strategy": "mesh_expanded"},
        )

        # Check if we can resume:
        state = ckpt.load()
        if state:
            print(f"Can resume from Phase {state['last_completed_phase'] + 1}")

        # Restore and continue:
        ckpt.save_phase_start(phase=3, phase_name="CONCEPT_DEV")
    """

    CHECKPOINT_FILE = "checkpoint.json"

    def __init__(self, audit_dir: str | Path, project_dir: str | Path | None = None) -> None:
        self._audit_dir = Path(audit_dir)
        self._checkpoint_path = self._audit_dir / self.CHECKPOINT_FILE
        # project_dir is used for draft hash computation; inferred from audit_dir if not given
        if project_dir is not None:
            self._project_dir = Path(project_dir)
        else:
            # audit_dir is typically projects/{slug}/.audit
            self._project_dir = self._audit_dir.parent

    @property
    def checkpoint_path(self) -> Path:
        return self._checkpoint_path

    def exists(self) -> bool:
        """Check if a checkpoint file exists."""
        return self._checkpoint_path.is_file()

    def load(self) -> dict[str, Any] | None:
        """
        Load checkpoint state.

        Returns:
            Checkpoint dict or None if no checkpoint exists.
        """
        if not self._checkpoint_path.is_file():
            return None

        try:
            data = json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
            logger.info(
                "Checkpoint loaded: Phase %d (%s)",
                data.get("last_completed_phase", -1),
                data.get("last_phase_name", "unknown"),
            )
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load checkpoint: %s", e)
            return None

    def save_phase_completion(
        self,
        phase: int,
        phase_name: str,
        outputs: dict[str, Any] | None = None,
        flagged_issues: list[str] | None = None,
        audit_stats: dict[str, Any] | None = None,
    ) -> None:
        """
        Save checkpoint after completing a pipeline phase.

        Args:
            phase: Phase number (0-11, use 65 for Phase 6.5)
            phase_name: Phase name (e.g., "LITERATURE_SEARCH")
            outputs: Key outputs from this phase
            flagged_issues: Issues flagged for later phases
            audit_stats: Hook trigger/pass/fix statistics
        """
        state = self.load() or self._empty_state()

        state["last_completed_phase"] = phase
        state["last_phase_name"] = phase_name
        state["status"] = "phase_completed"
        state["timestamp"] = datetime.now().isoformat()

        # Accumulate phase outputs
        if outputs:
            state["phase_outputs"][f"P{phase}"] = outputs

        # Update flagged issues
        if flagged_issues:
            state["flagged_issues"].extend(flagged_issues)

        # Update audit stats
        if audit_stats:
            state["audit_stats"].update(audit_stats)

        # Append to history
        state["history"].append(
            {
                "action": "phase_completed",
                "phase": phase,
                "phase_name": phase_name,
                "timestamp": datetime.now().isoformat(),
            }
        )

        self._write(state)

    def save_phase_start(
        self,
        phase: int,
        phase_name: str,
        current_section: str | None = None,
    ) -> None:
        """
        Record that a phase has started (for crash recovery).

        Args:
            phase: Phase number starting
            phase_name: Phase name
            current_section: Current section being worked on (if applicable)
        """
        state = self.load() or self._empty_state()

        state["current_phase"] = phase
        state["current_phase_name"] = phase_name
        state["status"] = "in_progress"
        state["timestamp"] = datetime.now().isoformat()

        if current_section:
            state["current_section"] = current_section

        state["history"].append(
            {
                "action": "phase_started",
                "phase": phase,
                "phase_name": phase_name,
                "timestamp": datetime.now().isoformat(),
            }
        )

        self._write(state)

    def save_section_progress(
        self,
        section: str,
        word_count: int = 0,
        approval_status: str = "pending",
        user_feedback: str = "",
    ) -> None:
        """Record progress within a phase (e.g., during Phase 5 writing).

        Args:
            section: Section name (e.g., "Methods", "Results").
            word_count: Current word count for the section.
            approval_status: One of "pending", "approved", "revision_requested".
            user_feedback: User's feedback when requesting revision.
        """
        state = self.load() or self._empty_state()
        state["current_section"] = section
        state["timestamp"] = datetime.now().isoformat()

        if "section_progress" not in state:
            state["section_progress"] = {}

        existing = state["section_progress"].get(section, {})
        revision_count = existing.get("revision_count", 0)
        if approval_status == "revision_requested":
            revision_count += 1

        state["section_progress"][section] = {
            "word_count": word_count,
            "completed_at": datetime.now().isoformat(),
            "approval_status": approval_status,
            "user_feedback": user_feedback,
            "revision_count": revision_count,
        }

        self._write(state)

    def add_flagged_issue(self, issue: str, severity: str = "minor") -> None:
        """Add a flagged issue for later phases to address."""
        state = self.load() or self._empty_state()
        state["flagged_issues"].append(
            {
                "issue": issue,
                "severity": severity,
                "flagged_at": datetime.now().isoformat(),
            }
        )
        self._write(state)

    def get_recovery_summary(self) -> str:
        """
        Generate a human-readable recovery summary.

        Returns:
            Markdown-formatted summary for the agent to present to the user.
        """
        state = self.load()
        if not state:
            return "No checkpoint found. Starting fresh."

        last_phase = state.get("last_completed_phase", -1)
        last_name = state.get("last_phase_name", "unknown")
        status = state.get("status", "unknown")
        ts = state.get("timestamp", "unknown")
        section = state.get("current_section", "N/A")

        phases_done = list(state.get("phase_outputs", {}).keys())
        issues = state.get("flagged_issues", [])

        lines = [
            "## Pipeline Checkpoint Recovery",
            "",
            f"- **Last completed**: Phase {last_phase} ({last_name})",
            f"- **Status**: {status}",
            f"- **Timestamp**: {ts}",
            f"- **Current section**: {section}",
            f"- **Phases with outputs**: {', '.join(phases_done) if phases_done else 'None'}",
            f"- **Flagged issues**: {len(issues)}",
        ]

        # Show regression context if present
        regression = state.get("regression_context")
        if regression:
            lines.extend(
                [
                    "",
                    "### Regression Active",
                    f"- From Phase {regression.get('from_phase')} → Phase {regression.get('to_phase')}",
                    f"- Reason: {regression.get('reason', 'N/A')}",
                    f"- Sections to rewrite: {', '.join(regression.get('sections_to_rewrite', []))}",
                    f"- Regression count: {regression.get('regression_count', 1)}",
                ]
            )

        # Show pause state if present
        pause = state.get("pause_state")
        if pause and status == "paused":
            continuity = self.get_continuity_plan()
            lines.extend(
                [
                    "",
                    "### Pipeline Paused",
                    f"- Paused at: {pause.get('paused_at', 'N/A')}",
                    f"- Phase at pause: {pause.get('phase_at_pause', 'N/A')}",
                    f"- Reason: {pause.get('reason', 'user_requested')}",
                    f"- Auto-resume: {'Yes' if continuity['auto_resume'] else 'No'}",
                    f"- Next action: {continuity['next_action']}",
                ]
            )

        # Show section approval status
        section_progress = state.get("section_progress", {})
        has_approvals = any("approval_status" in s for s in section_progress.values())
        if has_approvals:
            lines.extend(["", "### Section Approval Status"])
            for sec_name, sec_data in section_progress.items():
                approval = sec_data.get("approval_status", "N/A")
                lines.append(f"- {sec_name}: {approval}")

        lines.extend(
            [
                "",
                "### Options:",
                f"1. **Continue** from Phase {last_phase + 1}",
                f"2. **Redo** Phase {last_phase} ({last_name})",
                "3. **Restart** (keep concept + references)",
                "4. **Full restart**",
            ]
        )

        return "\n".join(lines)

    # ── Phase Regression ──────────────────────────────────────────

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

    # ── Pause / Resume ────────────────────────────────────────────

    def save_pause(self, reason: str = "user_requested") -> None:
        """
        Pause the pipeline, recording current state and draft hashes.

        The draft hashes are used to detect user edits during the pause.
        """
        state = self.load() or self._empty_state()

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
            return self._regression_continuity_decision(
                state.get("regression_context", {})
            )

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
    MAX_AUTONOMOUS_REGRESSIONS = 2

    # Maximum consecutive unattended auto-resumes before a periodic human
    # checkpoint is required (bounded-autonomy safeguard for the YOLO flow).
    MAX_CONSECUTIVE_AUTO_RESUMES = 3

    def _regression_continuity_decision(
        self, regression_ctx: dict[str, Any]
    ) -> dict[str, Any]:
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

        pause_state = state.get("pause_state", {})
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
        state["pause_state"]["resumed_at"] = datetime.now().isoformat()

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

    # ── Section Approval ──────────────────────────────────────────

    def get_section_approval_status(self) -> dict[str, str]:
        """Get approval status for all tracked sections.

        Returns:
            Dict mapping section name → approval_status.
        """
        state = self.load()
        if not state:
            return {}
        return {
            section: data.get("approval_status", "pending")
            for section, data in state.get("section_progress", {}).items()
        }

    def all_sections_approved(self) -> bool:
        """Check if all tracked sections have been approved."""
        statuses = self.get_section_approval_status()
        if not statuses:
            return False
        return all(s == "approved" for s in statuses.values())

    def clear(self) -> None:
        """Remove the checkpoint file (for full restart)."""
        if self._checkpoint_path.is_file():
            self._checkpoint_path.unlink()
            logger.info("Checkpoint cleared")

    def _empty_state(self) -> dict[str, Any]:
        """Create an empty checkpoint state."""
        return {
            "version": 2,
            "last_completed_phase": -1,
            "last_phase_name": "",
            "current_phase": -1,
            "current_phase_name": "",
            "current_section": "",
            "status": "not_started",
            "phase_outputs": {},
            "flagged_issues": [],
            "audit_stats": {},
            "section_progress": {},
            "history": [],
            "created_at": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat(),
        }

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

    def _write(self, state: dict[str, Any]) -> None:
        """Write state to disk."""
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoint_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
