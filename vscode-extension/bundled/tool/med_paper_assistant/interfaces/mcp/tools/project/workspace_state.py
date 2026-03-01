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
        Get workspace state for context recovery. Call at conversation START.
        Returns: current project, last activity, suggested next action.
        Also surfaces any pending evolution items from previous conversations.
        """
        state_manager = get_workspace_state_manager()
        summary = state_manager.get_recovery_summary()

        # Append pending evolutions guidance if any exist
        from pathlib import Path

        from med_paper_assistant.interfaces.mcp.tools._shared.guidance import (
            build_startup_guidance,
        )

        workspace_root = Path(state_manager.base_path)
        evolution_guidance = build_startup_guidance(workspace_root)
        if evolution_guidance:
            summary += "\n" + evolution_guidance

        return summary

    @mcp.tool()
    def sync_workspace_state(
        doing: Optional[str] = None,
        next_action: Optional[str] = None,
        context: Optional[str] = None,
        clear: bool = False,
    ) -> str:
        """
        Sync workspace state for future session recovery. Call before important ops or session end.

        Args:
            doing: Current activity description
            next_action: Suggested next action
            context: Important context (comma-separated)
            clear: If True, clear recovery hints instead of syncing
        """
        state_manager = get_workspace_state_manager()

        if clear:
            success = state_manager.clear_recovery_hints()
            if success:
                return "✅ Recovery hints cleared. Ready for new work!"
            else:
                return "❌ Failed to clear recovery hints."

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
- Doing: {doing or "(not specified)"}
- Next Action: {next_action or "(not specified)"}
- Context: {len(context_list) if context_list else 0} items saved

💡 This state will be available in future sessions via `get_workspace_state`."""
        else:
            return "❌ Failed to sync workspace state. Check file permissions."

    @mcp.tool()
    def checkpoint_writing_context(
        section: str,
        plan: str = "",
        notes: str = "",
        references_in_use: str = "",
    ) -> str:
        """
        Save detailed writing context to survive context compaction.
        Call PROACTIVELY during long writing sessions to prevent losing
        reasoning, plans, and style decisions when context is compacted.

        Best called:
        - Before starting each new paragraph
        - After completing a significant portion of a section
        - When switching between sections or references
        - Before any operation that may trigger compaction

        Args:
            section: Current section being written (e.g., "Introduction")
            plan: Writing plan/outline for the section (e.g., "P1: background, P2: gap, P3: aim")
            notes: Agent's reasoning/approach notes (e.g., "formal tone, avoiding first person")
            references_in_use: Key references currently being used (comma-separated citation keys)
        """
        state_manager = get_workspace_state_manager()

        # Build rich agent context
        context_parts = []
        if plan:
            context_parts.append(f"Plan: {plan}")
        if notes:
            context_parts.append(f"Notes: {notes}")
        if references_in_use:
            context_parts.append(f"Refs: {references_in_use}")
        agent_context = " | ".join(context_parts) if context_parts else None

        success = state_manager.sync_writing_session(
            section=section,
            filename=f"{section.lower().replace(' ', '-')}.md",
            operation="checkpoint",
            agent_context=agent_context,
        )

        if success:
            return (
                f"✅ Writing context checkpointed for **{section}**\n\n"
                "This context will survive context compaction and appear in "
                "`get_workspace_state()` recovery summary."
            )
        else:
            return "❌ Failed to checkpoint writing context."
