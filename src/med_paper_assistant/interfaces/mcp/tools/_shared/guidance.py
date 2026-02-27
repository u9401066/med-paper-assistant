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

        return (
            f"\n### \u26a0\ufe0f Pending Evolutions\n\n"
            f"**{pending_count} pending item(s)**: {type_summary}{stale_warning}\n"
            f'Use `apply_pending_evolutions(action="preview")` to review, '
            f'or `apply_pending_evolutions(action="apply_all")` to auto-apply safe items.'
        )
    except Exception:
        return None
