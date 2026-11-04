"""Composed CheckpointManager."""

from __future__ import annotations

from ._pause_resume import PauseResumeMixin
from ._phase_state import PhaseStateMixin
from ._recovery import RecoverySummaryMixin
from ._regression import RegressionMixin
from ._sections import SectionApprovalMixin


class CheckpointManager(
    PhaseStateMixin,
    SectionApprovalMixin,
    RegressionMixin,
    PauseResumeMixin,
    RecoverySummaryMixin,
):
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
