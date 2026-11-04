"""Section approval tracking within a phase (e.g., Phase 5 writing)."""

from __future__ import annotations

from datetime import datetime

from ._io import CheckpointIOMixin


class SectionApprovalMixin(CheckpointIOMixin):
    """Track per-section progress and user approval status."""

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
