"""Bridge from meta-learning results to DomainConstraintEngine evolution suggestions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

logger = structlog.get_logger()


def _hook_to_constraint_category(hook_id: str) -> str:
    """Map hook ID prefix to constraint category."""
    prefix = hook_id[0] if hook_id else ""
    return {
        "A": "vocabulary",  # A hooks: text-level
        "B": "structural",  # B hooks: section-level
        "C": "structural",  # C hooks: manuscript-level
        "E": "reporting",  # E hooks: EQUATOR
        "F": "evidential",  # F hooks: data artifacts
        "P": "boundary",  # P hooks: pre-commit
    }.get(prefix, "vocabulary")


def _lesson_to_constraint_category(lesson_category: str) -> str:
    """Map lesson category to constraint category."""
    return {
        "hook_tuning": "statistical",
        "writing_pattern": "vocabulary",
        "tool_usage": "boundary",
        "quality": "structural",
        "equator": "reporting",
        "data": "evidential",
    }.get(lesson_category, "vocabulary")


class ConstraintBridgeMixin:
    """Turns recurring analysis patterns into constraint suggestions."""

    if TYPE_CHECKING:

        def analyze(self) -> dict[str, Any]: ...

    def suggest_constraint_evolutions(
        self,
        analysis_result: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extract recurring patterns from meta-learning analysis and suggest constraints.

        Bridge between MetaLearningEngine and DomainConstraintEngine.
        Scans analysis results for patterns that should become JSON constraints.

        Args:
            analysis_result: Result from analyze(). If None, runs analyze() first.

        Returns:
            List of constraint suggestion dicts ready for DomainConstraintEngine.evolve().
        """
        if analysis_result is None:
            analysis_result = self.analyze()

        suggestions = self._suggest_from_adjustments(analysis_result.get("adjustments", []))
        suggestions.extend(self._suggest_from_critical_lessons(analysis_result.get("lessons", [])))

        logger.info(
            "constraint_suggestions_generated",
            count=len(suggestions),
        )
        return suggestions

    @staticmethod
    def _suggest_from_adjustments(adjustments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Pattern 1: Hook with high trigger rate → add matching constraint."""
        suggestions: list[dict[str, Any]] = []
        for adj in adjustments:
            hook_id = adj.get("hook_id", "")
            reason = adj.get("reason", "")
            if "high trigger" in reason.lower() or "frequent" in reason.lower():
                suggestions.append(
                    {
                        "constraint_id": f"ML-{hook_id}",
                        "rule": f"pattern_from_{hook_id.lower()}",
                        "category": _hook_to_constraint_category(hook_id),
                        "description": f"Auto-constraint from recurring {hook_id} triggers: {reason}",
                        "severity": "WARNING",
                        "reason": f"MetaLearning detected recurring pattern in {hook_id}",
                        "source_hook": hook_id,
                    }
                )
        return suggestions

    @staticmethod
    def _suggest_from_critical_lessons(lessons: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Pattern 2: Critical lessons → potential constraints."""
        suggestions: list[dict[str, Any]] = []
        critical_lessons = [ls for ls in lessons if ls.get("severity") == "critical"]
        for i, lesson in enumerate(critical_lessons):
            cat = lesson.get("category", "unknown")
            suggestions.append(
                {
                    "constraint_id": f"ML-CRT-{i:03d}",
                    "rule": f"critical_{cat}",
                    "category": _lesson_to_constraint_category(cat),
                    "description": lesson.get("lesson", ""),
                    "severity": "WARNING",
                    "reason": f"Critical lesson from {lesson.get('source', 'unknown')}",
                    "source_hook": "",
                }
            )
        return suggestions
