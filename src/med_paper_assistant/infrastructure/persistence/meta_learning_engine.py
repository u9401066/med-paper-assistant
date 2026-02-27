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
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

from .hook_effectiveness_tracker import HookEffectivenessTracker
from .quality_scorecard import QualityScorecard

logger = structlog.get_logger()

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

    AUDIT_FILE = "meta-learning-audit.yaml"

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

    # All expected hooks in the framework (A/B/C/E/F/P layers)
    EXPECTED_HOOKS = [
        "A1",
        "A2",
        "A3",
        "A4",
        "A5",
        "A6",
        "B1",
        "B2",
        "B3",
        "B4",
        "B5",
        "B6",
        "B7",
        "B8",
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
        "C6",
        "C7",
        "C8",
        "C9",
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
    ]

    def analyze(self) -> dict[str, Any]:
        """
        Run full meta-learning analysis (D1 through D8).

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

        audit_trail = self._d6_build_audit_trail(adjustments, all_lessons, skill_suggestions)
        summary = self._build_summary(adjustments, all_lessons, skill_suggestions)

        return {
            "adjustments": [a.to_dict() for a in adjustments],
            "lessons": [lesson.to_dict() for lesson in all_lessons],
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

    def _d2_analyze_quality(self) -> list[LessonLearned]:
        """D2: Derive lessons from quality scorecard patterns."""
        lessons = []
        sc = self._scorecard.get_scorecard()

        # Check for weak dimensions (absolute threshold)
        weak = self._scorecard.get_weak_dimensions(min_score=6.0)
        for w in weak:
            lessons.append(
                LessonLearned(
                    category="quality_gap",
                    lesson=f"{w['dimension']} scored {w['score']}/10: {w['explanation']}",
                    source="D2 quality analysis",
                    severity="warning" if w["score"] < 5 else "info",
                )
            )

        # Check if all standard dimensions are evaluated
        missing = sc.get("missing_dimensions", [])
        if missing:
            lessons.append(
                LessonLearned(
                    category="process_gap",
                    lesson=f"Missing quality evaluations: {', '.join(missing)}",
                    source="D2 quality analysis",
                    severity="warning",
                )
            )

        # Average score trend
        avg = sc.get("average_score", 0)
        if avg >= 8:
            lessons.append(
                LessonLearned(
                    category="achievement",
                    lesson=f"Average quality score {avg}/10 — excellent quality",
                    source="D2 quality analysis",
                    severity="info",
                )
            )
        elif avg < 6:
            lessons.append(
                LessonLearned(
                    category="quality_gap",
                    lesson=f"Average quality score {avg}/10 — below threshold, review needed",
                    source="D2 quality analysis",
                    severity="critical",
                )
            )

        # Relative weakness: even if all pass, flag the lowest-scoring dimension
        # This ensures there is ALWAYS something to improve
        dimensions = sc.get("dimensions", {})
        if dimensions and not weak:
            sorted_dims = sorted(dimensions.items(), key=lambda x: x[1].get("score", 10))
            lowest_name, lowest_data = sorted_dims[0]
            lowest_score = lowest_data.get("score", 0)
            if lowest_score < 10:  # Perfect 10 needs no improvement
                lessons.append(
                    LessonLearned(
                        category="improvement_opportunity",
                        lesson=(
                            f"{lowest_name} is the weakest dimension at {lowest_score}/10 "
                            f"— prioritize for next iteration"
                        ),
                        source="D2 relative weakness analysis",
                        severity="info",
                    )
                )

        return lessons

    def _d4_d5_skill_suggestions(self) -> list[dict[str, Any]]:
        """D4-D5: Suggest SKILL.md / instruction improvements."""
        suggestions = []
        all_stats = self._tracker.get_stats()

        # Check for recurring issues (same hook triggered > 2 times)
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

        # First-run awareness: lower threshold for suggestions
        # If hooks only have 1-2 evaluations, still flag notable patterns
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

        # Check quality gaps that suggest skill improvements
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
            "manual_adjustments": sum(
                1 for a in adjustments if not (a.auto_apply and a.within_bounds)
            ),
            "lessons_count": len(lessons),
            "suggestions_count": len(suggestions),
            "adjustments": [a.to_dict() for a in adjustments],
            "lessons": [lesson.to_dict() for lesson in lessons],
            "suggestions": suggestions,
        }

        # Append to audit file
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

    def _d5_check_project_completeness(self) -> list[LessonLearned]:
        """D5 extension: Check project-level file completeness and configuration."""
        lessons = []

        # Check journal-profile.yaml
        profile_path = self._audit_dir.parent / "journal-profile.yaml"
        if profile_path.is_file():
            try:
                profile = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
                journal_name = profile.get("journal", {}).get("name", "")
                if not journal_name:
                    lessons.append(
                        LessonLearned(
                            category="configuration_gap",
                            lesson="journal-profile.yaml: journal name is blank — export and formatting cannot enforce journal style",
                            source="D5 completeness check",
                            severity="warning",
                        )
                    )
                ref_style = profile.get("references", {}).get("style", "")
                if not ref_style:
                    lessons.append(
                        LessonLearned(
                            category="configuration_gap",
                            lesson="journal-profile.yaml: references.style not set — bibliography format unknown",
                            source="D5 completeness check",
                            severity="warning",
                        )
                    )
            except (yaml.YAMLError, OSError):
                lessons.append(
                    LessonLearned(
                        category="configuration_gap",
                        lesson="journal-profile.yaml exists but cannot be parsed",
                        source="D5 completeness check",
                        severity="warning",
                    )
                )
        else:
            lessons.append(
                LessonLearned(
                    category="configuration_gap",
                    lesson="journal-profile.yaml missing — no journal-specific formatting rules",
                    source="D5 completeness check",
                    severity="warning",
                )
            )

        # Check .memory/ files
        memory_dir = self._audit_dir.parent / ".memory"
        for mf in ["activeContext.md", "progress.md"]:
            mpath = memory_dir / mf
            if not mpath.is_file():
                lessons.append(
                    LessonLearned(
                        category="documentation_gap",
                        lesson=f".memory/{mf} missing — project memory not initialized",
                        source="D5 completeness check",
                        severity="info",
                    )
                )

        # Check concept.md exists
        concept = self._audit_dir.parent / "concept.md"
        if not concept.is_file():
            lessons.append(
                LessonLearned(
                    category="documentation_gap",
                    lesson="concept.md missing or not created — paper lacks concept foundation",
                    source="D5 completeness check",
                    severity="warning",
                )
            )

        return lessons

    def _d7_review_retrospective(self) -> list[LessonLearned]:
        """D7: Analyze review-report + author-response to evolve reviewer instructions."""
        lessons = []
        audit_dir = self._audit_dir

        # Find review round artifacts
        review_reports = sorted(audit_dir.glob("review-report-*.md"))
        author_responses = sorted(audit_dir.glob("author-response-*.md"))

        if not review_reports:
            lessons.append(
                LessonLearned(
                    category="review_gap",
                    lesson="No review-report artifacts found — review stage may not have executed",
                    source="D7 review retrospective",
                    severity="warning",
                )
            )
            return lessons

        # Check review loop data for hash integrity
        loop_file = audit_dir / "audit-loop-review.json"
        if loop_file.is_file():
            try:
                loop_data = json.loads(loop_file.read_text(encoding="utf-8"))
                rounds = loop_data.get("rounds", [])
                for r in rounds:
                    h_start = r.get("artifact_hash_start", "")
                    h_end = r.get("artifact_hash_end", "")
                    rnum = r.get("round_number", "?")

                    if h_start and h_end and h_start == h_end:
                        lessons.append(
                            LessonLearned(
                                category="review_integrity",
                                lesson=(
                                    f"Round {rnum}: manuscript hash unchanged — "
                                    f"review round did NOT modify the manuscript"
                                ),
                                source="D7 review retrospective",
                                severity="critical",
                            )
                        )
                    elif not h_start and not h_end:
                        lessons.append(
                            LessonLearned(
                                category="review_integrity",
                                lesson=(
                                    f"Round {rnum}: no artifact hash recorded — "
                                    f"cannot verify manuscript was modified"
                                ),
                                source="D7 review retrospective",
                                severity="warning",
                            )
                        )

                    # Check if issues were found but none fixed
                    issues = r.get("issues", [])
                    fixes = r.get("fixes", [])
                    if len(issues) > 0 and len(fixes) == 0:
                        lessons.append(
                            LessonLearned(
                                category="review_integrity",
                                lesson=(
                                    f"Round {rnum}: {len(issues)} issues found but 0 fixes applied — "
                                    f"review feedback was not acted upon"
                                ),
                                source="D7 review retrospective",
                                severity="warning",
                            )
                        )
            except (json.JSONDecodeError, OSError):
                pass

        # Analyze response patterns
        if len(review_reports) != len(author_responses):
            lessons.append(
                LessonLearned(
                    category="review_gap",
                    lesson=(
                        f"Mismatch: {len(review_reports)} review-report(s) vs "
                        f"{len(author_responses)} author-response(s)"
                    ),
                    source="D7 review retrospective",
                    severity="warning",
                )
            )

        return lessons

    def _d8_equator_retrospective(self) -> list[LessonLearned]:
        """D8: Analyze EQUATOR compliance reports to evolve detection logic."""
        lessons = []
        audit_dir = self._audit_dir

        equator_reports = sorted(audit_dir.glob("equator-compliance-*.md"))
        if not equator_reports:
            lessons.append(
                LessonLearned(
                    category="equator_gap",
                    lesson="No EQUATOR compliance reports found — reporting guideline check may not have run",
                    source="D8 EQUATOR retrospective",
                    severity="info",
                )
            )
            return lessons

        # Read latest EQUATOR compliance and check for gaps
        try:
            latest = equator_reports[-1]
            content = latest.read_text(encoding="utf-8")
            # Look for non-compliant items
            non_compliant_count = content.lower().count("non-compliant") + content.lower().count(
                "not reported"
            )
            partial_count = content.lower().count("partial")

            if non_compliant_count > 0:
                lessons.append(
                    LessonLearned(
                        category="equator_finding",
                        lesson=(
                            f"{non_compliant_count} non-compliant EQUATOR items found — "
                            f"review checklist and strengthen weak sections"
                        ),
                        source="D8 EQUATOR retrospective",
                        severity="warning" if non_compliant_count > 3 else "info",
                    )
                )
            if partial_count > 0:
                lessons.append(
                    LessonLearned(
                        category="equator_finding",
                        lesson=f"{partial_count} partially compliant EQUATOR items — can be improved",
                        source="D8 EQUATOR retrospective",
                        severity="info",
                    )
                )
        except OSError:
            pass

        return lessons

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

        suggestions: list[dict[str, Any]] = []
        lessons = analysis_result.get("lessons", [])
        adjustments = analysis_result.get("adjustments", [])

        # Pattern 1: Hook with high trigger rate → add matching constraint
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

        # Pattern 2: Critical lessons → potential constraints
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

        logger.info(
            "constraint_suggestions_generated",
            count=len(suggestions),
        )
        return suggestions


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
