"""
Pipeline Checkpoint Manager — Save/restore auto-paper pipeline state.

Implements the checkpoint.json spec from auto-paper SKILL.md.
Enables interrupted pipelines to resume from the last completed phase.

Architecture:
  Infrastructure layer service. Called by auto-paper pipeline at phase transitions.
  Stores to: projects/{slug}/.audit/checkpoint.json

Design rationale (CONSTITUTION §22):
  - Auditable: every phase transition is recorded
  - Recomposable: resume from any phase
"""

from __future__ import annotations

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

    def __init__(self, audit_dir: str | Path) -> None:
        self._audit_dir = Path(audit_dir)
        self._checkpoint_path = self._audit_dir / self.CHECKPOINT_FILE

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
            phase: Phase number (0-10)
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

    def save_section_progress(self, section: str, word_count: int = 0) -> None:
        """Record progress within a phase (e.g., during Phase 5 writing)."""
        state = self.load() or self._empty_state()
        state["current_section"] = section
        state["timestamp"] = datetime.now().isoformat()

        if "section_progress" not in state:
            state["section_progress"] = {}
        state["section_progress"][section] = {
            "word_count": word_count,
            "completed_at": datetime.now().isoformat(),
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
            "",
            "### Options:",
            f"1. **Continue** from Phase {last_phase + 1}",
            f"2. **Redo** Phase {last_phase} ({last_name})",
            "3. **Restart** (keep concept + references)",
            "4. **Full restart**",
        ]

        return "\n".join(lines)

    def clear(self) -> None:
        """Remove the checkpoint file (for full restart)."""
        if self._checkpoint_path.is_file():
            self._checkpoint_path.unlink()
            logger.info("Checkpoint cleared")

    def _empty_state(self) -> dict[str, Any]:
        """Create an empty checkpoint state."""
        return {
            "version": 1,
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

    def _write(self, state: dict[str, Any]) -> None:
        """Write state to disk."""
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoint_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
