"""Activity, search, and pipeline-state recording for compact-memory recovery."""

from datetime import datetime
from typing import Any, Optional

from ._io import StateIOMixin


class ActivityMixin(StateIOMixin):
    """Record agent activity, search PMIDs, and pipeline execution state."""

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def record_activity(
        self,
        tool_name: str,
        doing: Optional[str] = None,
        next_action: Optional[str] = None,
        context: Optional[list[str]] = None,
    ) -> bool:
        """
        Record an activity for recovery purposes.

        Args:
            tool_name: Name of the tool being called.
            doing: Description of what agent is doing.
            next_action: Suggested next action.
            context: Important context to preserve.

        Returns:
            True if saved successfully.
        """
        state = self.get_state()
        state["last_activity"] = datetime.now().isoformat()
        state["workspace_state"]["last_tool_called"] = tool_name

        if doing:
            state["recovery_hints"]["agent_was_doing"] = doing
        if next_action:
            state["recovery_hints"]["next_suggested_action"] = next_action
        if context:
            state["recovery_hints"]["important_context"] = context

        return self.save_state(state)

    def record_search_pmids(self, pmids: list[str]) -> bool:
        """
        Record PMIDs from a search for cross-MCP access.

        Args:
            pmids: List of PubMed IDs.

        Returns:
            True if saved successfully.
        """
        state = self.get_state()
        state["workspace_state"]["last_search_pmids"] = pmids[:50]  # Keep last 50
        state["cross_mcp_state"]["pubmed_session_active"] = True
        return self.save_state(state)

    def sync_pipeline_state(
        self,
        project: str,
        current_phase: int,
        phase_name: str,
        gate_passed: bool,
        gate_failures: list[str] | None = None,
        next_action: str | None = None,
        phases_passed: list[int] | None = None,
        phases_remaining: list[int] | None = None,
        current_round: int | None = None,
        review_verdict: str | None = None,
        gate_details: dict[str, Any] | None = None,
    ) -> bool:
        """
        Sync pipeline execution state for compact-memory recovery.

        Called automatically by gate/review tools. Ensures that even
        after context compaction, the agent can recover exact pipeline state.

        Args:
            project: Project slug.
            current_phase: Current phase number.
            phase_name: Current phase name.
            gate_passed: Whether the last gate check passed.
            gate_failures: List of failing check names.
            gate_details: Compact machine-readable gate result for recovery.
            next_action: Specific next action the agent should take.
            phases_passed: List of phase numbers that passed gate.
            phases_remaining: List of phase numbers not yet passed.
            current_round: Current review round (Phase 7 only).
            review_verdict: Review loop verdict (Phase 7 only).

        Returns:
            True if saved successfully.
        """
        state = self.get_state()
        state["pipeline_state"] = {
            "active": True,
            "project": project,
            "current_phase": current_phase,
            "current_phase_name": phase_name,
            "current_round": current_round,
            "last_gate_result": "PASSED" if gate_passed else "FAILED",
            "last_gate_failures": gate_failures or [],
            "last_gate_details": gate_details,
            "next_required_action": next_action,
            "phases_passed": phases_passed or [],
            "phases_remaining": phases_remaining or [],
            "review_verdict": review_verdict,
            "last_heartbeat": datetime.now().isoformat(),
        }
        # Also update recovery hints for double safety
        doing = f"Pipeline Phase {current_phase} ({phase_name})"
        if current_round:
            doing += f" Round {current_round}"
        state["recovery_hints"]["agent_was_doing"] = doing
        if next_action:
            state["recovery_hints"]["next_suggested_action"] = next_action
        state["last_activity"] = datetime.now().isoformat()
        return self.save_state(state)

    def clear_pipeline_state(self) -> bool:
        """Clear pipeline state (pipeline completed or abandoned)."""
        state = self.get_state()
        state["pipeline_state"] = self._default_state()["pipeline_state"]
        return self.save_state(state)
