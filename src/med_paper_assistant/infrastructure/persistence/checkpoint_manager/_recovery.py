"""Human-readable recovery summary for interrupted pipelines."""

from __future__ import annotations

from ._continuity import ContinuityMixin


class RecoverySummaryMixin(ContinuityMixin):
    """Render the checkpoint state as a markdown recovery briefing."""

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
