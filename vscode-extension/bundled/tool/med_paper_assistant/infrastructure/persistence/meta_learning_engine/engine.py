"""MetaLearningEngine — composes the D1-D9 analyses defined in sibling modules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..hook_effectiveness_tracker import HookEffectivenessTracker
from ..quality_scorecard import QualityScorecard
from ._audit_summary import AuditSummaryMixin
from ._constraint_bridge import ConstraintBridgeMixin
from ._hook_analysis import HookAnalysisMixin
from ._models import LessonLearned
from ._quality_analysis import QualityAnalysisMixin
from ._review_retrospective import ReviewRetrospectiveMixin
from ._tool_telemetry import ToolTelemetryMixin


class MetaLearningEngine(
    HookAnalysisMixin,
    QualityAnalysisMixin,
    ReviewRetrospectiveMixin,
    ToolTelemetryMixin,
    AuditSummaryMixin,
    ConstraintBridgeMixin,
):
    """
    Hook D meta-learning engine.

    Analyzes hook effectiveness and quality data, then produces:
    - Threshold adjustments (auto-applicable within ±20%)
    - Lessons learned for the auto-paper skill (references/lessons-learned.md)
    - Improvement suggestions requiring user confirmation
    - Audit trail

    Usage:
        engine = MetaLearningEngine(audit_dir, tracker, scorecard)
        result = engine.analyze()
        # result contains adjustments, lessons, suggestions, audit_trail
    """

    AUDIT_FILE = "meta-learning-audit.yaml"

    def __init__(
        self,
        audit_dir: str | Path,
        tracker: HookEffectivenessTracker,
        scorecard: QualityScorecard,
        workspace_root: str | Path | None = None,
    ) -> None:
        self._audit_dir = Path(audit_dir)
        self._tracker = tracker
        self._scorecard = scorecard
        self._audit_path = self._audit_dir / self.AUDIT_FILE
        self._workspace_root = Path(workspace_root) if workspace_root else None

    # All expected hooks in the framework (A/B/C/E/F/P layers)
    EXPECTED_HOOKS = [
        "A1",
        "A2",
        "A3",
        "A3b",
        "A3c",
        "A4",
        "A5",
        "A6",
        "A7",
        "B1",
        "B2",
        "B3",
        "B4",
        "B5",
        "B6",
        "B7",
        "B8",
        "B9",
        "B10",
        "B11",
        "B12",
        "B13",
        "B14",
        "B15",
        "B16",
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
        "C6",
        "C7a",
        "C7b",
        "C7d",
        "C8",
        "C9",
        "C10",
        "C11",
        "C12",
        "C13",
        "C14",
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "F1",
        "F2",
        "F3",
        "F4",
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P6",
        "P7",
        "P8",
        "R1",
        "R2",
        "R3",
        "R4",
        "R5",
        "R6",
    ]

    def analyze(self) -> dict[str, Any]:
        """
        Run full meta-learning analysis (D1 through D9).

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
        quality_lessons = self._d2_analyze_quality()
        coverage_lessons = self._d1_check_hook_coverage()
        completeness_lessons = self._d5_check_project_completeness()
        review_lessons = self._d7_review_retrospective()
        equator_lessons = self._d8_equator_retrospective()
        skill_suggestions = self._d4_d5_skill_suggestions()
        d9_suggestions = self._d9_tool_description_suggestions()
        all_suggestions = skill_suggestions + d9_suggestions

        all_lessons = (
            quality_lessons
            + coverage_lessons
            + completeness_lessons
            + review_lessons
            + equator_lessons
            + [
                LessonLearned(
                    category="hook_tuning",
                    lesson=f"{a.hook_id}.{a.parameter}: {a.current_value} → {a.suggested_value} ({a.reason})",
                    source="D3 threshold adjustment",
                    severity="info" if a.within_bounds else "warning",
                )
                for a in adjustments
            ]
        )

        audit_trail = self._d6_build_audit_trail(adjustments, all_lessons, all_suggestions)
        summary = self._build_summary(adjustments, all_lessons, all_suggestions)

        return {
            "adjustments": [a.to_dict() for a in adjustments],
            "lessons": [lesson.to_dict() for lesson in all_lessons],
            "suggestions": all_suggestions,
            "audit_trail": audit_trail,
            "summary": summary,
        }
