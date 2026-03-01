"""
Workspace State Manager - Per-project state persistence

Each project stores its own state at: projects/{slug}/.mdpaper-state.json

State file is the "single source of truth" per project for:
- Pipeline execution state (phase, round, gate results)
- Recovery hints for interrupted workflows
- Cross-MCP state (e.g., last search PMIDs)
- Last activity timestamp

Current project tracking is handled by ProjectManager (.current_project file).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class WorkspaceStateManager:
    """
    Manages per-project state that persists across sessions.

    State File: projects/{slug}/.mdpaper-state.json
    Fallback: .mdpaper-state.json (when no project is active)

    This enables:
    - Agent to recover context after being summarized
    - Pipeline state preservation across context compaction
    - Coordination between multiple MCP servers
    - Recovery hints for interrupted workflows
    """

    STATE_FILE = ".mdpaper-state.json"
    STATE_VERSION = 2

    def __init__(self, base_path: str = "."):
        """
        Initialize WorkspaceStateManager.

        Args:
            base_path: Base directory for the med-paper-assistant workspace.
        """
        self.base_path = Path(base_path).resolve()
        self.projects_dir = self.base_path / "projects"

    # =========================================================================
    # State File Resolution
    # =========================================================================

    @property
    def state_file(self) -> Path:
        """
        Resolve state file path for the current project.

        Returns project-specific: projects/{slug}/.mdpaper-state.json
        Falls back to root: .mdpaper-state.json (when no project is active)
        """
        slug = self._get_current_project_slug()
        if slug:
            project_dir = self.projects_dir / slug
            if project_dir.is_dir():
                return project_dir / self.STATE_FILE
        return self.base_path / self.STATE_FILE

    def state_file_for_project(self, slug: str) -> Path:
        """Get state file path for a specific project."""
        return self.projects_dir / slug / self.STATE_FILE

    def _get_current_project_slug(self) -> Optional[str]:
        """Read current project slug from .current_project file."""
        marker = self.base_path / ".current_project"
        try:
            if marker.is_file():
                return marker.read_text(encoding="utf-8").strip() or None
        except OSError:
            pass
        return None

    # =========================================================================
    # State Read/Write
    # =========================================================================

    def get_state(self) -> dict[str, Any]:
        """
        Get the current project state.

        Returns:
            State dictionary with defaults if file doesn't exist.
        """
        sf = self.state_file
        if not sf.exists():
            # Try auto-migrate from root-level v1 state
            self._maybe_migrate_v1()
            if not sf.exists():
                return self._default_state()

        try:
            content = sf.read_text(encoding="utf-8")
            state = json.loads(content)

            # Ensure all required keys exist (forward compat)
            default = self._default_state()
            for key in default:
                if key not in state:
                    state[key] = default[key]

            return state
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read state file {sf}: {e}")
            return self._default_state()

    def save_state(self, state: dict[str, Any]) -> bool:
        """
        Save the project state.

        Args:
            state: State dictionary to save.

        Returns:
            True if saved successfully.
        """
        sf = self.state_file
        try:
            # Ensure parent directory exists
            sf.parent.mkdir(parents=True, exist_ok=True)

            state["version"] = self.STATE_VERSION
            state["last_updated"] = datetime.now().isoformat()

            content = json.dumps(state, indent=2, ensure_ascii=False)
            sf.write_text(content, encoding="utf-8")
            return True
        except OSError as e:
            logger.error(f"Failed to save state file {sf}: {e}")
            return False

    def _maybe_migrate_v1(self) -> None:
        """
        Auto-migrate root-level v1 state file to per-project location.

        If root .mdpaper-state.json exists with version=1 and its
        current_project matches our current project, migrate the data.
        """
        root_file = self.base_path / self.STATE_FILE
        if not root_file.is_file():
            return

        slug = self._get_current_project_slug()
        if not slug:
            return

        target = self.projects_dir / slug / self.STATE_FILE
        if target.exists():
            return

        try:
            content = root_file.read_text(encoding="utf-8")
            old_state = json.loads(content)

            if old_state.get("version") != 1:
                return

            # Only migrate if the old state was for this project
            old_project = old_state.get("current_project")
            if old_project and old_project != slug:
                return

            # Build v2 state from v1 data (drop current_project field)
            new_state = self._default_state()
            for key in [
                "last_activity",
                "workspace_state",
                "recovery_hints",
                "cross_mcp_state",
                "pipeline_state",
            ]:
                if key in old_state:
                    new_state[key] = old_state[key]

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(new_state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info(f"Migrated v1 state to {target}")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to migrate v1 state: {e}")

    def _default_state(self) -> dict[str, Any]:
        """Return default state structure (v2: per-project, no current_project)."""
        return {
            "version": self.STATE_VERSION,
            "last_activity": None,
            "last_updated": None,
            "workspace_state": {
                "open_drafts": [],
                "pending_validations": [],
                "last_search_pmids": [],
                "last_tool_called": None,
            },
            "recovery_hints": {
                "agent_was_doing": None,
                "next_suggested_action": None,
                "important_context": [],
            },
            "cross_mcp_state": {
                "pubmed_session_active": False,
                "cgu_session_active": False,
            },
            "pipeline_state": {
                "active": False,
                "project": None,
                "current_phase": None,
                "current_phase_name": None,
                "current_round": None,
                "last_gate_result": None,
                "last_gate_failures": [],
                "next_required_action": None,
                "phases_passed": [],
                "phases_remaining": [],
                "review_verdict": None,
                "last_heartbeat": None,
            },
            "writing_session": {
                "active": False,
                "current_section": None,
                "last_file_modified": None,
                "last_operation": None,
                "word_count": 0,
                "sections_on_disk": [],
                "timestamp": None,
                "agent_context": None,
            },
        }

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def get_current_project(self) -> Optional[str]:
        """Get the current project slug (reads from .current_project file)."""
        return self._get_current_project_slug()

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

    def sync_writing_session(
        self,
        section: str,
        filename: str,
        operation: str,
        word_count: int = 0,
        agent_context: str | None = None,
    ) -> bool:
        """
        Auto-checkpoint writing session state.

        Called automatically by write_draft/patch_draft after successful writes.
        Survives context compaction so the agent can recover writing progress.

        Args:
            section: Section name being written (e.g., "Introduction").
            filename: Draft filename modified.
            operation: "write" or "patch".
            word_count: Current word count of the file.
            agent_context: Optional agent notes about current writing intent.
        """
        state = self.get_state()

        # Scan drafts/ to capture all sections on disk
        sections_on_disk = []
        slug = self._get_current_project_slug()
        if slug:
            drafts_dir = self.projects_dir / slug / "drafts"
            if drafts_dir.is_dir():
                for f in sorted(drafts_dir.iterdir()):
                    if f.suffix == ".md":
                        name = f.stem.replace("-", " ").replace("_", " ").title()
                        wc = len(f.read_text(encoding="utf-8").split())
                        sections_on_disk.append(f"{name} ({wc}w)")

        state["writing_session"] = {
            "active": True,
            "current_section": section,
            "last_file_modified": filename,
            "last_operation": operation,
            "word_count": word_count,
            "sections_on_disk": sections_on_disk,
            "timestamp": datetime.now().isoformat(),
            "agent_context": agent_context,
        }

        # Also update recovery hints as double-safety
        state["recovery_hints"]["agent_was_doing"] = (
            f"Writing {section} ({operation} → {filename})"
        )
        state["last_activity"] = datetime.now().isoformat()

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
            lines.append(
                "\n💡 Use `read_draft` to review current content before continuing."
            )

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


# =========================================================================
# Singleton Instance
# =========================================================================

_workspace_state_manager: Optional[WorkspaceStateManager] = None


def get_workspace_state_manager(base_path: str = ".") -> WorkspaceStateManager:
    """
    Get the singleton WorkspaceStateManager instance.

    Args:
        base_path: Base directory (only used on first call).

    Returns:
        WorkspaceStateManager instance.
    """
    global _workspace_state_manager
    if _workspace_state_manager is None:
        _workspace_state_manager = WorkspaceStateManager(base_path)
    return _workspace_state_manager


def reset_workspace_state_manager() -> None:
    """Reset the singleton (for testing)."""
    global _workspace_state_manager
    _workspace_state_manager = None
