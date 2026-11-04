"""D9 analysis: MCP tool telemetry → tool description improvement suggestions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class ToolTelemetryMixin:
    """Suggestions derived from ToolInvocationStore data."""

    _workspace_root: Path | None

    def _d9_tool_description_suggestions(self) -> list[dict[str, Any]]:
        """
        D9: Analyze MCP tool invocation telemetry to suggest description improvements.

        Reads ToolInvocationStore from workspace_root (if set).
        Returns L3 suggestions (requires_confirmation=True) for:
        - Tools with misuse_rate > 20% (≥2 misuse events): description confuses agents
        - Tools with error_count >= 3: parameters may need clarifying examples

        Returns:
            List of suggestion dicts with type="improve_tool_description".
            Empty list if workspace_root is not set or store has no data.

        CONSTITUTION §23 compliance:
            All D9 suggestions are L3 (requires_confirmation=True).
            D9 is additive — does not modify earlier analysis outputs.
            D9 failure never blocks earlier output generation (wrapped in try/except).
        """
        if self._workspace_root is None:
            return []

        all_stats = self._d9_read_tool_stats(self._workspace_root)
        suggestions: list[dict[str, Any]] = []
        for tool_name, stats in all_stats.items():
            suggestions.extend(self._d9_tool_suggestions(tool_name, stats))
        return suggestions

    @staticmethod
    def _d9_read_tool_stats(workspace_root: Path) -> dict[str, Any]:
        """Load per-tool stats; an unreadable store yields no data."""
        try:
            from ..tool_invocation_store import ToolInvocationStore

            store = ToolInvocationStore(workspace_root)
            all_stats = store.get_all_stats()
        except Exception as e:
            logger.warning("meta_learning.d9_store_read_failed", error=str(e))
            return {}
        return all_stats or {}

    @staticmethod
    def _d9_tool_suggestions(tool_name: str, stats: dict[str, Any]) -> list[dict[str, Any]]:
        """Misuse-rate and recurring-error suggestions for a single tool."""
        invocation_count = stats.get("invocation_count", 0)
        misuse_count = stats.get("misuse_count", 0)
        error_count = stats.get("error_count", 0)
        error_types = stats.get("error_types", [])

        if invocation_count <= 0:
            return []

        suggestions = []
        # High misuse rate: agent is confused by tool description
        misuse_rate = misuse_count / invocation_count
        if misuse_count >= 2 and misuse_rate > 0.20:
            suggestions.append(
                {
                    "type": "improve_tool_description",
                    "target": tool_name,
                    "reason": (
                        f"Misuse rate {misuse_rate:.0%} ({misuse_count}/{invocation_count} calls) "
                        f"— tool description may be ambiguous to agents"
                    ),
                    "requires_confirmation": True,
                }
            )

        # Recurring errors: parameter examples or edge case docs needed
        if error_count >= 3:
            error_summary = f"; error_types: [{', '.join(error_types)}]" if error_types else ""
            suggestions.append(
                {
                    "type": "improve_tool_description",
                    "target": tool_name,
                    "reason": (
                        f"{error_count} errors recorded — consider adding parameter examples "
                        f"or clarifying edge cases{error_summary}"
                    ),
                    "requires_confirmation": True,
                }
            )
        return suggestions
