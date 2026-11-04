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

from typing import Optional

from ._manager import WorkspaceStateManager

__all__ = [
    "WorkspaceStateManager",
    "get_workspace_state_manager",
    "reset_workspace_state_manager",
]

# =========================================================================
# Singleton Instance
# =========================================================================

# The singleton and its accessors live in this module so that code (and tests)
# reassigning the global keep working exactly as before the package split.
_workspace_state_manager: Optional[WorkspaceStateManager] = None


def get_workspace_state_manager(base_path: str | None = None) -> WorkspaceStateManager:
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
