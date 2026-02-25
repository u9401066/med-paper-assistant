"""
Meta-Learning Engine — Hook D implementation for self-improvement.

Analyzes hook effectiveness and quality scorecard data to produce:
  - D1: Performance statistics analysis
  - D3: Automatic threshold adjustments (within ±20% bounds)
  - D4-D5: SKILL.md / AGENTS.md improvement suggestions
  - D6: Audit trail generation

Architecture:
  Infrastructure layer service. Called during Phase 10 of auto-paper pipeline.
  Reads from HookEffectivenessTracker and QualityScorecard.
  Writes to .audit/ and SKILL.md Lessons Learned section.

CONSTITUTION §23 Boundaries:
  - L1 (auto): Update SKILL.md Lessons Learned
  - L2 (auto): Adjust thresholds ±20%
  - L3 (logged): Factual instruction changes → decisionLog
  - FORBIDDEN: Modify CONSTITUTION, 🔒 rules, save_reference_mcp priority, Hook D itself
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .hook_effectiveness_tracker import HookEffectivenessTracker
from .quality_scorecard import QualityScorecard

logger = logging.getLogger(__name__)

# Threshold adjustment limits (CONSTITUTION §23)
MAX_THRESHOLD_ADJUSTMENT = 0.20  # ±20%


class ThresholdAdjustment:
    """A recommended threshold change."""

    def __init__(
        self,
        hook_id: str,
        parameter: str,
        current_value: float,
        suggested_value: float,
        reason: str,
        auto_apply: bool = True,
    ) -> None:
        self.hook_id = hook_id
        self.parameter = parameter
        self.current_value = current_value
        self.suggested_value = suggested_value
        self.reason = reason
        self.auto_apply = auto_apply

    @property
    def change_pct(self) -> float:
        """Percentage change from current to suggested."""
        if self.current_value == 0:
            return 0.0
        return (self.suggested_value - self.current_value) / self.current_value

    @property
    def within_bounds(self) -> bool:
        """Check if adjustment is within ±20% limit."""
        return abs(self.change_pct) <= MAX_THRESHOLD_ADJUSTMENT

    def to_dict(self) -> dict[str, Any]:
        return {
            "hook_id": self.hook_id,
            "parameter": self.parameter,
            "current_value": self.current_value,
            "suggested_value": self.suggested_value,
            "change_pct": f"{self.change_pct:+.0%}",
            "within_bounds": self.within_bounds,
            "auto_apply": self.auto_apply and self.within_bounds,
            "reason": self.reason,
        }


class LessonLearned:
    """A lesson to record in SKILL.md."""

    def __init__(
        self,
        category: str,
        lesson: str,
        source: str,
        severity: str = "info",
    ) -> None:
        self.category = category  # e.g., "hook_tuning", "writing_pattern", "tool_usage"
        self.lesson = lesson
        self.source = source  # e.g., "D1 analysis", "D3 threshold adjustment"
        self.severity = severity  # "info", "warning", "critical"
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "lesson": self.lesson,
            "source": self.source,
            "severity": self.severity,
            "timestamp": self.timestamp,
        }

    def to_markdown(self) -> str:
        icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}.get(self.severity, "•")
        return f"- {icon} **[{self.category}]** {self.lesson} _(source: {self.source}, {self.timestamp[:10]})_"


class MetaLearningEngine:
    """
    Hook D meta-learning engine.

    Analyzes hook effectiveness and quality data, then produces:
    - Threshold adjustments (auto-applicable within ±20%)
    - Lessons learned for SKILL.md
    - Improvement suggestions requiring user confirmation
    - Audit trail

    Usage:
        engine = MetaLearningEngine(audit_dir, tracker, scorecard)
        result = engine.analyze()
        # result contains adjustments, lessons, suggestions, audit_trail
    """

    AUDIT_FILE = "meta-learning-audit.json"

    def __init__(
        self,
        audit_dir: str | Path,
        tracker: HookEffectivenessTracker,
        scorecard: QualityScorecard,
    ) -> None:
        self._audit_dir = Path(audit_dir)
        self._tracker = tracker
        self._scorecard = scorecard
        self._audit_path = self._audit_dir / self.AUDIT_FILE

    def analyze(self) -> dict[str, Any]:
        """
        Run full meta-learning analysis (D1 through D6).

        Returns:
            {
                "adjustments": [...],      # ThresholdAdjustment dicts
                "lessons": [...],          # LessonLearned dicts
                "suggestions": [...],      # Requires user confirmation
                "audit_trail": {...},      # Full analysis record
                "summary": "..."           # Human-readable summary
            }
        """
        adjustments = self._d1_d3_analyze_hooks()
        quality_lessons = self._d1_analyze_quality()
        skill_suggestions = self._d4_d5_skill_suggestions()

        all_lessons = quality_lessons + [
            LessonLearned(
                category="hook_tuning",
                lesson=f"{a.hook_id}.{a.parameter}: {a.current_value} → {a.suggested_value} ({a.reason})",
                source="D3 threshold adjustment",
                severity="info" if a.within_bounds else "warning",
            )
            for a in adjustments
        ]

        audit_trail = self._d6_build_audit_trail(adjustments, all_lessons, skill_suggestions)
        summary = self._build_summary(adjustments, all_lessons, skill_suggestions)

        return {
            "adjustments": [a.to_dict() for a in adjustments],
            "lessons": [l.to_dict() for l in all_lessons],
            "suggestions": skill_suggestions,
            "audit_trail": audit_trail,
            "summary": summary,
        }

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
                adjustments.append(ThresholdAdjustment(
                    hook_id=hook_id,
                    parameter="threshold",
                    current_value=1.0,  # normalized
                    suggested_value=1.15,
                    reason=rec["reason"],
                    auto_apply=True,
                ))

            elif rec["type"] == "tighten":
                adjustments.append(ThresholdAdjustment(
                    hook_id=hook_id,
                    parameter="threshold",
                    current_value=1.0,
                    suggested_value=0.85,
                    reason=rec["reason"],
                    auto_apply=True,
                ))

            elif rec["type"] == "fix_logic":
                # Logic fixes need user confirmation
                adjustments.append(ThresholdAdjustment(
                    hook_id=hook_id,
                    parameter="logic",
                    current_value=stats.get("false_positive_rate", 0),
                    suggested_value=0.0,
                    reason=rec["reason"],
                    auto_apply=False,  # Requires human review
                ))

        return adjustments

    def _d1_analyze_quality(self) -> list[LessonLearned]:
        """D1: Derive lessons from quality scorecard patterns."""
        lessons = []
        sc = self._scorecard.get_scorecard()

        # Check for weak dimensions
        weak = self._scorecard.get_weak_dimensions(min_score=6.0)
        for w in weak:
            lessons.append(LessonLearned(
                category="quality_gap",
                lesson=f"{w['dimension']} scored {w['score']}/10: {w['explanation']}",
                source="D1 quality analysis",
                severity="warning" if w["score"] < 5 else "info",
            ))

        # Check if all standard dimensions are evaluated
        missing = sc.get("missing_dimensions", [])
        if missing:
            lessons.append(LessonLearned(
                category="process_gap",
                lesson=f"Missing quality evaluations: {', '.join(missing)}",
                source="D1 quality analysis",
                severity="warning",
            ))

        # Average score trend
        avg = sc.get("average_score", 0)
        if avg >= 8:
            lessons.append(LessonLearned(
                category="achievement",
                lesson=f"Average quality score {avg}/10 — excellent quality",
                source="D1 quality analysis",
                severity="info",
            ))
        elif avg < 6:
            lessons.append(LessonLearned(
                category="quality_gap",
                lesson=f"Average quality score {avg}/10 — below threshold, review needed",
                source="D1 quality analysis",
                severity="critical",
            ))

        return lessons

    def _d4_d5_skill_suggestions(self) -> list[dict[str, Any]]:
        """D4-D5: Suggest SKILL.md / instruction improvements."""
        suggestions = []
        all_stats = self._tracker.get_stats()

        # Check for recurring issues (same hook triggered > 2 times)
        for hook_id, stats in all_stats.items():
            if stats["trigger"] > 2 and stats["fix_rate"] < 0.5:
                suggestions.append({
                    "type": "add_pre_check",
                    "target": f"Hook {hook_id}",
                    "reason": f"Triggered {stats['trigger']} times with only {stats['fix_rate']:.0%} fix rate — consider adding a pre-check",
                    "requires_confirmation": True,
                })

        # Check quality gaps that suggest skill improvements
        weak = self._scorecard.get_weak_dimensions(min_score=5.0)
        for w in weak:
            if w["dimension"] == "methodology_reproducibility":
                suggestions.append({
                    "type": "strengthen_skill",
                    "target": "Hook B5 (methodology checklist)",
                    "reason": f"Methodology score {w['score']}/10 — B5 checklist may need expansion",
                    "requires_confirmation": True,
                })
            elif w["dimension"] == "text_quality":
                suggestions.append({
                    "type": "strengthen_skill",
                    "target": "Hook A3 (Anti-AI detection)",
                    "reason": f"Text quality {w['score']}/10 — Anti-AI patterns may need updating",
                    "requires_confirmation": True,
                })

        return suggestions

    def _d6_build_audit_trail(
        self,
        adjustments: list[ThresholdAdjustment],
        lessons: list[LessonLearned],
        suggestions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """D6: Build and persist audit trail."""
        trail = {
            "timestamp": datetime.now().isoformat(),
            "run_number": self._tracker.get_run_count(),
            "adjustments_count": len(adjustments),
            "auto_adjustments": sum(1 for a in adjustments if a.auto_apply and a.within_bounds),
            "manual_adjustments": sum(1 for a in adjustments if not (a.auto_apply and a.within_bounds)),
            "lessons_count": len(lessons),
            "suggestions_count": len(suggestions),
            "adjustments": [a.to_dict() for a in adjustments],
            "lessons": [l.to_dict() for l in lessons],
            "suggestions": suggestions,
        }

        # Append to audit file
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        existing = []
        if self._audit_path.is_file():
            try:
                existing = json.loads(self._audit_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = []

        existing.append(trail)
        self._audit_path.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return trail

    def _build_summary(
        self,
        adjustments: list[ThresholdAdjustment],
        lessons: list[LessonLearned],
        suggestions: list[dict[str, Any]],
    ) -> str:
        """Build human-readable summary."""
        lines = [
            "## Hook D Meta-Learning Summary",
            "",
            f"**Analysis Time**: {datetime.now().isoformat()}",
            "",
        ]

        # Adjustments
        auto = [a for a in adjustments if a.auto_apply and a.within_bounds]
        manual = [a for a in adjustments if not (a.auto_apply and a.within_bounds)]

        if auto:
            lines.append(f"### Auto-Applied Adjustments ({len(auto)})")
            lines.append("")
            for a in auto:
                lines.append(f"- **{a.hook_id}** {a.parameter}: {a.change_pct:+.0%} — {a.reason}")
            lines.append("")

        if manual:
            lines.append(f"### ⚠️ Requires Confirmation ({len(manual)})")
            lines.append("")
            for a in manual:
                lines.append(f"- **{a.hook_id}** {a.parameter} — {a.reason}")
            lines.append("")

        # Lessons
        if lessons:
            lines.append(f"### Lessons Learned ({len(lessons)})")
            lines.append("")
            for l in lessons:
                lines.append(l.to_markdown())
            lines.append("")

        # Suggestions
        if suggestions:
            lines.append(f"### Improvement Suggestions ({len(suggestions)})")
            lines.append("")
            for s in suggestions:
                lines.append(f"- 💡 **{s['target']}** [{s['type']}]: {s['reason']}")
            lines.append("")

        if not adjustments and not lessons and not suggestions:
            lines.append("_No issues detected. All hooks performing within expected parameters._")

        return "\n".join(lines) + "\n"

    def format_lessons_for_skill(self, lessons: list[dict[str, Any]] | None = None) -> str:
        """
        Format lessons as Markdown for insertion into SKILL.md Lessons Learned section.

        Args:
            lessons: List of lesson dicts, or None to use latest analysis.
        """
        if lessons is None:
            result = self.analyze()
            lessons = result["lessons"]

        if not lessons:
            return "_尚無記錄。首次全自動執行後將自動填入。_"

        lines = []
        by_category: dict[str, list[dict[str, Any]]] = {}
        for l in lessons:
            cat = l["category"]
            by_category.setdefault(cat, []).append(l)

        for cat, items in sorted(by_category.items()):
            lines.append(f"### {cat}")
            for item in items:
                icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}.get(
                    item.get("severity", "info"), "•"
                )
                ts = item.get("timestamp", "")[:10]
                lines.append(f"- {icon} {item['lesson']} _(source: {item['source']}, {ts})_")
            lines.append("")

        return "\n".join(lines)
