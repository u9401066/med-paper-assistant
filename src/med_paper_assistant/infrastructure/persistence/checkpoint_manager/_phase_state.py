"""Phase lifecycle state: phase start/completion records and flagged issues."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ._io import CheckpointIOMixin


class PhaseStateMixin(CheckpointIOMixin):
    """Record phase starts, completions, and issues flagged for later phases."""

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
