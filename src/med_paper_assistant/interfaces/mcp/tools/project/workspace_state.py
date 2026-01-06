"""
Workspace State Tools

MCP tools for managing workspace state across sessions.

Solves the state inconsistency problem:
- Agent context gets summarized → state lost
- MCP tools are stateless → can't remember between calls
- Multiple entry points → file browser, git, scripts

Solution: Single source of truth in .mdpaper-state.json
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import (
    get_workspace_state_manager,
)


def register_workspace_state_tools(mcp: FastMCP):
    """Register workspace state management tools."""

    @mcp.tool()
    def get_workspace_state() -> str:
        """
        Get workspace state for context recovery.

        ⚠️ IMPORTANT: Agent should call this at the START of each conversation
        to recover context from previous sessions.

        Returns:
            - Current project
            - Last activity timestamp
            - What agent was doing before
            - Suggested next action
            - Important context to remember

        Example usage by Agent:
            1. New conversation starts
            2. Call get_workspace_state()
            3. Understand what was happening
            4. Continue seamlessly
        """
        state_manager = get_workspace_state_manager()
        return state_manager.get_recovery_summary()

    @mcp.tool()
    def sync_workspace_state(
        doing: Optional[str] = None,
        next_action: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """
        Sync workspace state for recovery in future sessions.

        ⚠️ IMPORTANT: Agent should call this BEFORE important operations
        or when conversation is about to end.

        This ensures that if the Agent gets summarized or a new session starts,
        the context can be recovered.

        Args:
            doing: What the agent is currently doing.
                   Example: "Writing introduction section for remimazolam study"
            next_action: Suggested next action after current task.
                        Example: "validate_concept" or "draft_section methods"
            context: Important context to preserve (comma-separated).
                    Example: "Found 5 key papers, novelty score 82"

        Returns:
            Confirmation message.

        Example:
            sync_workspace_state(
                doing="Drafting Methods section",
                next_action="validate_concept",
                context="Using RCT design, n=120, primary outcome is recovery time"
            )
        """
        state_manager = get_workspace_state_manager()

        # Parse context if provided
        context_list = None
        if context:
            context_list = [c.strip() for c in context.split(",") if c.strip()]

        success = state_manager.record_activity(
            tool_name="sync_workspace_state",
            doing=doing,
            next_action=next_action,
            context=context_list,
        )

        if success:
            return f"""✅ Workspace state synced!

**Current State:**
- Doing: {doing or '(not specified)'}
- Next Action: {next_action or '(not specified)'}
- Context: {len(context_list) if context_list else 0} items saved

💡 This state will be available in future sessions via `get_workspace_state`."""
        else:
            return "❌ Failed to sync workspace state. Check file permissions."

    @mcp.tool()
    def clear_recovery_state() -> str:
        """
        Clear recovery hints after successful context recovery.

        Call this after successfully resuming work to prevent stale hints
        from appearing in future sessions.

        Returns:
            Confirmation message.
        """
        state_manager = get_workspace_state_manager()
        success = state_manager.clear_recovery_hints()

        if success:
            return "✅ Recovery hints cleared. Ready for new work!"
        else:
            return "❌ Failed to clear recovery hints."
