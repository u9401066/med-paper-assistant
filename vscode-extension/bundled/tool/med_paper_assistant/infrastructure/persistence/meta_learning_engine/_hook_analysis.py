"""D1/D3/D4/D5 analyses: hook effectiveness, coverage and skill suggestions."""

from __future__ import annotations

from typing import Any

from ..hook_effectiveness_tracker import HookEffectivenessTracker
from ..quality_scorecard import QualityScorecard
from ._models import LessonLearned, ThresholdAdjustment


class HookAnalysisMixin:
    """Analyses derived from HookEffectivenessTracker statistics."""

    EXPECTED_HOOKS: list[str]
    _tracker: HookEffectivenessTracker
    _scorecard: QualityScorecard

    def _d1_d3_analyze_hooks(self) -> list[ThresholdAdjustment]:
        """D1 + D3: Analyze hook stats and propose threshold changes."""
        adjustments = []
        all_stats = self._tracker.get_stats()
        recommendations = self._tracker.get_recommendations()

        for rec in recommendations:
            hook_id = rec["hook_id"]
            stats = all_stats.get(hook_id, {})

            if rec["type"] == "loosen":
                # Suggest loosening threshold by 15% (within 20% limit)
                adjustments.append(
                    ThresholdAdjustment(
                        hook_id=hook_id,
                        parameter="threshold",
                        current_value=1.0,  # normalized
                        suggested_value=1.15,
                        reason=rec["reason"],
                        auto_apply=True,
                    )
                )

            elif rec["type"] == "tighten":
                adjustments.append(
                    ThresholdAdjustment(
                        hook_id=hook_id,
                        parameter="threshold",
                        current_value=1.0,
                        suggested_value=0.85,
                        reason=rec["reason"],
                        auto_apply=True,
                    )
                )

            elif rec["type"] == "fix_logic":
                # Logic fixes need user confirmation
                adjustments.append(
                    ThresholdAdjustment(
                        hook_id=hook_id,
                        parameter="logic",
                        current_value=stats.get("false_positive_rate", 0),
                        suggested_value=0.0,
                        reason=rec["reason"],
                        auto_apply=False,  # Requires human review
                    )
                )

        return adjustments

    def _d1_check_hook_coverage(self) -> list[LessonLearned]:
        """D1 extension: Check which expected hooks were never recorded."""
        lessons = []
        all_stats = self._tracker.get_stats()
        recorded_hooks = set(all_stats.keys())
        expected = set(self.EXPECTED_HOOKS)
        missing_hooks = sorted(expected - recorded_hooks)

        if missing_hooks:
            # Group by layer
            by_layer: dict[str, list[str]] = {}
            for h in missing_hooks:
                layer = h[0] if h else "?"
                by_layer.setdefault(layer, []).append(h)

            for layer, hooks in sorted(by_layer.items()):
                lessons.append(
                    LessonLearned(
                        category="hook_coverage_gap",
                        lesson=(
                            f"Layer {layer} hooks never evaluated: {', '.join(hooks)} "
                            f"— verify these hooks are being triggered during pipeline"
                        ),
                        source="D1 coverage analysis",
                        severity="warning",
                    )
                )

        # Summary stat
        coverage_pct = len(recorded_hooks & expected) / len(expected) * 100 if expected else 100
        if coverage_pct < 80:
            lessons.append(
                LessonLearned(
                    category="process_gap",
                    lesson=(
                        f"Hook coverage {coverage_pct:.0f}% ({len(recorded_hooks & expected)}/{len(expected)} hooks) "
                        f"— significant blind spots in quality assurance"
                    ),
                    source="D1 coverage analysis",
                    severity="warning" if coverage_pct >= 50 else "critical",
                )
            )

        return lessons

    def _d4_d5_skill_suggestions(self) -> list[dict[str, Any]]:
        """D4-D5: Suggest SKILL.md / instruction improvements."""
        suggestions: list[dict[str, Any]] = []
        all_stats = self._tracker.get_stats()
        suggestions.extend(self._d4_recurring_issue_suggestions(all_stats))
        suggestions.extend(self._d4_first_run_suggestions(all_stats))
        suggestions.extend(self._d4_quality_gap_suggestions())
        return suggestions

    @staticmethod
    def _d4_recurring_issue_suggestions(all_stats: dict[str, Any]) -> list[dict[str, Any]]:
        """Check for recurring issues (same hook triggered > 2 times)."""
        suggestions = []
        for hook_id, stats in all_stats.items():
            if stats["trigger"] > 2 and stats["fix_rate"] < 0.5:
                suggestions.append(
                    {
                        "type": "add_pre_check",
                        "target": f"Hook {hook_id}",
                        "reason": f"Triggered {stats['trigger']} times with only {stats['fix_rate']:.0%} fix rate — consider adding a pre-check",
                        "requires_confirmation": True,
                    }
                )
        return suggestions

    @staticmethod
    def _d4_first_run_suggestions(all_stats: dict[str, Any]) -> list[dict[str, Any]]:
        """First-run awareness: lower threshold for suggestions.

        If hooks only have 1-2 evaluations, still flag notable patterns.
        """
        suggestions = []
        for hook_id, stats in all_stats.items():
            total = stats["trigger"] + stats["pass"]
            if 1 <= total <= 4:  # Early data
                if stats["trigger"] > 0 and stats["fix"] == 0:
                    suggestions.append(
                        {
                            "type": "verify_fix_mechanism",
                            "target": f"Hook {hook_id}",
                            "reason": (
                                f"Triggered {stats['trigger']} time(s) with 0 fixes "
                                f"in first run — verify auto-fix mechanism works"
                            ),
                            "requires_confirmation": False,
                        }
                    )
        return suggestions

    def _d4_quality_gap_suggestions(self) -> list[dict[str, Any]]:
        """Check quality gaps that suggest skill improvements."""
        suggestions = []
        weak = self._scorecard.get_weak_dimensions(min_score=5.0)
        for w in weak:
            if w["dimension"] == "methodology_reproducibility":
                suggestions.append(
                    {
                        "type": "strengthen_skill",
                        "target": "Hook B5 (methodology checklist)",
                        "reason": f"Methodology score {w['score']}/10 — B5 checklist may need expansion",
                        "requires_confirmation": True,
                    }
                )
            elif w["dimension"] == "text_quality":
                suggestions.append(
                    {
                        "type": "strengthen_skill",
                        "target": "Hook A3 (Anti-AI detection)",
                        "reason": f"Text quality {w['score']}/10 — Anti-AI patterns may need updating",
                        "requires_confirmation": True,
                    }
                )
        return suggestions
