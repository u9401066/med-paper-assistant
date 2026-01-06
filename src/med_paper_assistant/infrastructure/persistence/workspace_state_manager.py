"""
Workspace State Manager - Cross-session state persistence

Solves the state inconsistency problem between:
1. Agent (gets summarized, loses context)
2. MCP Tools (stateless, each call independent)
3. File Browser (user can edit files directly)
4. External tools (git, scripts, etc.)

The workspace state file is the "single source of truth" for:
- Current active project
- Last activity timestamp
- What the agent was doing
- Suggested next action
- Cross-MCP state (e.g., last search PMIDs)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class WorkspaceStateManager:
    """
    Manages workspace-level state that persists across sessions.

    State File: .mdpaper-state.json

    This enables:
    - Agent to recover context after being summarized
    - MCP tools to know current project without asking
    - Coordination between multiple MCP servers
    - Recovery hints for interrupted workflows
    """

    STATE_FILE = ".mdpaper-state.json"
    STATE_VERSION = 1

    def __init__(self, base_path: str = "."):
        """
        Initialize WorkspaceStateManager.

        Args:
            base_path: Base directory for the med-paper-assistant workspace.
        """
        self.base_path = Path(base_path).resolve()
        self.state_file = self.base_path / self.STATE_FILE

    # =========================================================================
    # State Read/Write
    # =========================================================================

    def get_state(self) -> dict[str, Any]:
        """
        Get the current workspace state.

        Returns:
            State dictionary with defaults if file doesn't exist.
        """
        if not self.state_file.exists():
            return self._default_state()

        try:
            content = self.state_file.read_text(encoding="utf-8")
            state = json.loads(content)

            # Ensure all required keys exist
            default = self._default_state()
            for key in default:
                if key not in state:
                    state[key] = default[key]

            return state
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read state file: {e}")
            return self._default_state()

    def save_state(self, state: dict[str, Any]) -> bool:
        """
        Save the workspace state.

        Args:
            state: State dictionary to save.

        Returns:
            True if saved successfully.
        """
        try:
            state["version"] = self.STATE_VERSION
            state["last_updated"] = datetime.now().isoformat()

            content = json.dumps(state, indent=2, ensure_ascii=False)
            self.state_file.write_text(content, encoding="utf-8")
            return True
        except OSError as e:
            logger.error(f"Failed to save state file: {e}")
            return False

    def _default_state(self) -> dict[str, Any]:
        """Return default state structure."""
        return {
            "version": self.STATE_VERSION,
            "current_project": None,
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
        }

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def get_current_project(self) -> Optional[str]:
        """Get the current project slug."""
        state = self.get_state()
        return state.get("current_project")

    def set_current_project(self, slug: Optional[str]) -> bool:
        """
        Set the current project.

        Args:
            slug: Project slug, or None to clear.

        Returns:
            True if saved successfully.
        """
        state = self.get_state()
        state["current_project"] = slug
        state["last_activity"] = datetime.now().isoformat()
        return self.save_state(state)

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

    def get_recovery_summary(self) -> str:
        """
        Get a human-readable recovery summary.

        Returns:
            Markdown-formatted summary for agent consumption.
        """
        state = self.get_state()

        lines = ["## 🔄 Workspace State Recovery\n"]

        # Current project
        project = state.get("current_project")
        if project:
            lines.append(f"**Current Project:** `{project}`")
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
