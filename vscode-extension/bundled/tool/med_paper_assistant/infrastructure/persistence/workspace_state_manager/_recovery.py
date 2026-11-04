"""Startup recovery summary and recovery-hint reset."""

from ._io import StateIOMixin


class RecoveryMixin(StateIOMixin):
    """Render recovery context for the agent and clear it after recovery."""

    def get_recovery_summary(self) -> str:
        """
        Get a human-readable recovery summary.

        Returns:
            Markdown-formatted summary for agent consumption.
        """
        state = self.get_state()

        lines = ["## 🔄 Workspace State Recovery\n"]

        # ── PIPELINE STATE BANNER (highest priority after compaction) ──
        ps = state.get("pipeline_state", {})
        if ps.get("active"):
            lines.extend(
                [
                    "### ⚠️ ACTIVE PIPELINE IN PROGRESS",
                    "",
                    f"**Project**: `{ps.get('project')}`",
                    f"**Current Phase**: {ps.get('current_phase')} ({ps.get('current_phase_name')})",
                ]
            )
            if ps.get("current_round"):
                lines.append(f"**Current Round**: {ps['current_round']}")
            if ps.get("review_verdict"):
                lines.append(f"**Review Verdict**: {ps['review_verdict']}")
            lines.append(f"**Last Gate**: {ps.get('last_gate_result')}")
            if ps.get("last_gate_failures"):
                lines.append("**Failing Checks**:")
                for f in ps["last_gate_failures"]:
                    lines.append(f"  - {f}")
            if ps.get("next_required_action"):
                lines.append(f"\n🎯 **NEXT ACTION**: {ps['next_required_action']}")
            if ps.get("phases_remaining"):
                lines.append(f"**Phases Remaining**: {ps['phases_remaining']}")
            lines.append(f"**Last Heartbeat**: {ps.get('last_heartbeat')}")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Current project (from .current_project file, not from state)
        project = self._get_current_project_slug()
        if project:
            lines.append(f"**Current Project:** `{project}`")
            lines.append(f"**State File:** `projects/{project}/.mdpaper-state.json`")
        else:
            lines.append("**Current Project:** None (use `list_projects` or `create_project`)")

        # Last activity
        last_activity = state.get("last_activity")
        if last_activity:
            lines.append(f"**Last Activity:** {last_activity}")

        # What agent was doing
        hints = state.get("recovery_hints", {})
        if hints.get("agent_was_doing"):
            lines.append("\n### 📝 Last Session")
            lines.append(f"Agent was: **{hints['agent_was_doing']}**")

        if hints.get("next_suggested_action"):
            lines.append(f"Suggested next: `{hints['next_suggested_action']}`")

        if hints.get("important_context"):
            lines.append("\n**Important Context:**")
            for ctx in hints["important_context"]:
                lines.append(f"- {ctx}")

        # Workspace state
        ws_state = state.get("workspace_state", {})
        if ws_state.get("last_search_pmids"):
            count = len(ws_state["last_search_pmids"])
            lines.append(f"\n**Recent Search:** {count} PMIDs available")

        if ws_state.get("pending_validations"):
            lines.append(f"**Pending Validations:** {len(ws_state['pending_validations'])}")

        # ── WRITING SESSION BANNER ──
        ws = state.get("writing_session", {})
        if ws.get("active"):
            lines.append("")
            lines.append("### ✍️ WRITING SESSION IN PROGRESS")
            lines.append("")
            lines.append(f"**Last Section**: {ws.get('current_section')}")
            lines.append(f"**Last File**: `{ws.get('last_file_modified')}`")
            lines.append(f"**Last Operation**: {ws.get('last_operation')}")
            lines.append(f"**Word Count**: {ws.get('word_count', 0)}")
            lines.append(f"**Timestamp**: {ws.get('timestamp')}")
            if ws.get("agent_context"):
                lines.append(f"\n📋 **Agent Context**: {ws['agent_context']}")
            if ws.get("sections_on_disk"):
                lines.append("\n**Sections on Disk:**")
                for sec in ws["sections_on_disk"]:
                    lines.append(f"  - {sec}")
            lines.append("\n💡 Use `read_draft` to review current content before continuing.")

        return "\n".join(lines)

    def clear_recovery_hints(self) -> bool:
        """
        Clear recovery hints after successful recovery.

        Returns:
            True if saved successfully.
        """
        state = self.get_state()
        state["recovery_hints"] = {
            "agent_was_doing": None,
            "next_suggested_action": None,
            "important_context": [],
        }
        return self.save_state(state)
