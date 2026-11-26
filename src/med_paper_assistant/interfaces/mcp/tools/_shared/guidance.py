"""
Proactive Guidance Hints — Lightweight next-step suggestions appended to tool output.

Design philosophy:
    Stateless helper function (not a class). Appends a minimal GUIDANCE line to
    tool return values so agents receive proactive direction without extra tool calls.

    Applied only to high-value pipeline transition points (write_draft,
    validate_concept, run_meta_learning) to avoid token overhead on every tool.

Output format example:
    Draft saved at: /path/to/file
    GUIDANCE: next→run_writing_hooks | warn: novelty 68/100 below threshold

CONSTITUTION compliance:
    Advisory text appended to tool output — does not modify any rules,
    protected content, or CONSTITUTION principles.
"""

from __future__ import annotations

from pathlib import Path

from med_paper_assistant.interfaces.mcp.tool_surface import uses_compact_tool_surface

_COMPACT_TOOL_MAP: dict[str, str] = {
    "write_draft": 'draft_action(action="write")',
    "patch_draft": 'draft_action(action="patch")',
    "draft_section": 'draft_action(action="draft_section")',
    "read_draft": 'draft_action(action="read")',
    "list_drafts": 'draft_action(action="list_drafts")',
    "sync_references": 'draft_action(action="sync_references")',
    "run_writing_hooks": 'run_quality_checks(action="writing_hooks")',
    "evolve_constraint": 'run_quality_checks(action="evolve_constraint")',
    "apply_pending_evolutions": 'run_quality_checks(action="pending_evolutions")',
    "run_meta_learning": 'run_quality_checks(action="meta_learning")',
    "validate_concept": 'validation_action(action="concept")',
    "validate_wikilinks": 'validation_action(action="wikilinks")',
    "get_workspace_state": 'workspace_state_action(action="get")',
    "sync_workspace_state": 'workspace_state_action(action="sync")',
    "list_projects": 'project_action(action="list")',
    "create_project": 'project_action(action="create")',
    "save_reference": 'reference_action(action="save_agent")',
}


def compact_tool_hint(full_name: str) -> str:
    """Map a legacy full-surface verb to its compact facade call when compact is active."""
    if uses_compact_tool_surface():
        return _COMPACT_TOOL_MAP.get(full_name, full_name)
    return full_name


def build_guidance_hint(
    result: str,
    next_tool: str | None = None,
    warnings: list[str] | None = None,
    context_hints: list[str] | None = None,
) -> str:
    """
    Append a proactive guidance line to a tool result string.

    Returns the result unchanged if no hints are provided.

    Args:
        result: The tool's existing return value.
        next_tool: Suggested next MCP tool to call (e.g., "run_writing_hooks").
        warnings: Short warning messages (e.g., ["novelty 68/100 below threshold"]).
        context_hints: Additional context hints (e.g., ["3 suggestions require confirmation"]).

    Returns:
        result with '\\nGUIDANCE: ...' appended, or result unchanged if no hints.
    """
    if not result:
        return result

    parts: list[str] = []
    if next_tool:
        parts.append(f"next\u2192{next_tool}")
    if warnings:
        for w in warnings:
            parts.append(f"warn: {w}")
    if context_hints:
        parts.extend(context_hints)

    if not parts:
        return result

    return result + "\nGUIDANCE: " + " | ".join(parts)


def build_startup_guidance(workspace_root: Path) -> str | None:
    """
    Check for pending evolution items and return a guidance string for conversation start.

    Called by get_workspace_state() to append pending evolution info to the recovery summary.
    Returns None if there are no pending items.

    Args:
        workspace_root: Path to the workspace root directory.

    Returns:
        Guidance string summarising pending evolution items, or None.
    """
    try:
        from med_paper_assistant.infrastructure.persistence.pending_evolution_store import (
            PendingEvolutionStore,
        )

        store = PendingEvolutionStore(workspace_root)
        stats = store.summary()
        pending_count = stats.get("pending", 0)

        if pending_count == 0:
            return None

        by_type = stats.get("pending_by_type", {})
        type_parts = [f"{count} {t}" for t, count in sorted(by_type.items())]
        type_summary = ", ".join(type_parts) if type_parts else "mixed"

        stale = store.get_stale(days=7)
        stale_warning = f" ({len(stale)} stale >7d)" if stale else ""

        preview_call = (
            'run_quality_checks(action="pending_evolutions", reason="preview")'
            if uses_compact_tool_surface()
            else 'apply_pending_evolutions(action="preview")'
        )
        apply_call = (
            'run_quality_checks(action="pending_evolutions", reason="apply_all")'
            if uses_compact_tool_surface()
            else 'apply_pending_evolutions(action="apply_all")'
        )
        return (
            f"\n### \u26a0\ufe0f Pending Evolutions\n\n"
            f"**{pending_count} pending item(s)**: {type_summary}{stale_warning}\n"
            f"Use `{preview_call}` to review, "
            f"or `{apply_call}` to auto-apply safe items."
        )
    except Exception:
        return None
