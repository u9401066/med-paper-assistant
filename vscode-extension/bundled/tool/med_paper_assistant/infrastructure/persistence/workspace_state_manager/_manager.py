"""Composed WorkspaceStateManager."""

from ._activity import ActivityMixin
from ._recovery import RecoveryMixin
from ._writing_session import WritingSessionMixin


class WorkspaceStateManager(ActivityMixin, WritingSessionMixin, RecoveryMixin):
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
