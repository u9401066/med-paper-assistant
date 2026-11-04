"""D6 audit trail persistence plus Markdown rendering of meta-learning results."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from ..hook_effectiveness_tracker import HookEffectivenessTracker
from ._models import LessonLearned, ThresholdAdjustment

_ANALYSIS_STEP_DESCRIPTIONS = (
    ("D1", "Hook coverage and effectiveness analysis"),
    ("D2", "Quality scorecard retrospective"),
    ("D3", "Bounded threshold adjustment analysis"),
    ("D4", "Skill improvement suggestion analysis"),
    ("D5", "Project completeness and configuration analysis"),
    ("D6", "Append-only audit trail persistence"),
    ("D7", "Autonomous review retrospective analysis"),
    ("D8", "EQUATOR/reporting checklist retrospective analysis"),
    ("D9", "Tool telemetry and description improvement analysis"),
)


def _analysis_steps() -> dict[str, dict[str, str]]:
    return {
        step: {"status": "completed", "description": description}
        for step, description in _ANALYSIS_STEP_DESCRIPTIONS
    }


def _is_auto_applied(adjustment: ThresholdAdjustment) -> bool:
    return adjustment.auto_apply and adjustment.within_bounds


class AuditSummaryMixin:
    """Audit-trail persistence, summaries and lessons-learned formatting."""

    _audit_dir: Path
    _audit_path: Path
    _tracker: HookEffectivenessTracker

    if TYPE_CHECKING:

        def analyze(self) -> dict[str, Any]: ...

    def _d6_build_audit_trail(
        self,
        adjustments: list[ThresholdAdjustment],
        lessons: list[LessonLearned],
        suggestions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """D6: Build and persist audit trail."""
        trail = {
            "schema": "mdpaper.meta_learning_audit.v2",
            "timestamp": datetime.now().isoformat(),
            "run_number": self._tracker.get_run_count(),
            "source_tool": "run_meta_learning",
            "analysis_steps": _analysis_steps(),
            "adjustments_count": len(adjustments),
            "auto_adjustments": sum(1 for a in adjustments if _is_auto_applied(a)),
            "manual_adjustments": sum(1 for a in adjustments if not _is_auto_applied(a)),
            "lessons_count": len(lessons),
            "suggestions_count": len(suggestions),
            "adjustments": [a.to_dict() for a in adjustments],
            "lessons": [lesson.to_dict() for lesson in lessons],
            "suggestions": suggestions,
        }
        self._append_audit_trail(trail)
        return trail

    def _append_audit_trail(self, trail: dict[str, Any]) -> None:
        """Append the trail to the audit file."""
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        existing = []
        if self._audit_path.is_file():
            try:
                loaded = yaml.safe_load(self._audit_path.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    existing = loaded
            except (yaml.YAMLError, OSError):
                existing = []

        existing.append(trail)
        self._audit_path.write_text(
            yaml.dump(existing, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

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
        lines.extend(self._summary_adjustment_lines(adjustments))

        # Lessons
        if lessons:
            lines.append(f"### Lessons Learned ({len(lessons)})")
            lines.append("")
            for lesson in lessons:
                lines.append(lesson.to_markdown())
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

    @staticmethod
    def _summary_adjustment_lines(adjustments: list[ThresholdAdjustment]) -> list[str]:
        """Auto-applied and confirmation-required adjustment sections."""
        lines: list[str] = []
        auto = [a for a in adjustments if _is_auto_applied(a)]
        manual = [a for a in adjustments if not _is_auto_applied(a)]

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
        return lines

    def format_lessons_for_skill(self, lessons: list[dict[str, Any]] | None = None) -> str:
        """
        Format lessons as Markdown for the auto-paper skill's
        ``references/lessons-learned.md`` file.

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
        for lesson in lessons:
            cat = lesson["category"]
            by_category.setdefault(cat, []).append(lesson)

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
