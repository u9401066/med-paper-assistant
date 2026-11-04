"""D2/D5 analyses: quality scorecard retrospective and project completeness."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..quality_scorecard import QualityScorecard
from ._models import LessonLearned


class QualityAnalysisMixin:
    """Lessons derived from the quality scorecard and project files."""

    _audit_dir: Path
    _scorecard: QualityScorecard

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

        lessons.extend(self._d2_average_score_lessons(sc.get("average_score", 0)))
        if not weak:
            lessons.extend(self._d2_relative_weakness_lessons(sc.get("dimensions", {})))
        return lessons

    @staticmethod
    def _d2_average_score_lessons(avg: Any) -> list[LessonLearned]:
        """Average score trend."""
        if avg >= 8:
            return [
                LessonLearned(
                    category="achievement",
                    lesson=f"Average quality score {avg}/10 — excellent quality",
                    source="D2 quality analysis",
                    severity="info",
                )
            ]
        if avg < 6:
            return [
                LessonLearned(
                    category="quality_gap",
                    lesson=f"Average quality score {avg}/10 — below threshold, review needed",
                    source="D2 quality analysis",
                    severity="critical",
                )
            ]
        return []

    @staticmethod
    def _d2_relative_weakness_lessons(dimensions: dict[str, Any]) -> list[LessonLearned]:
        """Relative weakness: even if all pass, flag the lowest-scoring dimension.

        This ensures there is ALWAYS something to improve.
        """
        if not dimensions:
            return []
        sorted_dims = sorted(dimensions.items(), key=lambda x: x[1].get("score", 10))
        lowest_name, lowest_data = sorted_dims[0]
        lowest_score = lowest_data.get("score", 0)
        if lowest_score < 10:  # Perfect 10 needs no improvement
            return [
                LessonLearned(
                    category="improvement_opportunity",
                    lesson=(
                        f"{lowest_name} is the weakest dimension at {lowest_score}/10 "
                        f"— prioritize for next iteration"
                    ),
                    source="D2 relative weakness analysis",
                    severity="info",
                )
            ]
        return []

    def _d5_check_project_completeness(self) -> list[LessonLearned]:
        """D5 extension: Check project-level file completeness and configuration."""
        lessons = self._d5_journal_profile_lessons(self._audit_dir.parent / "journal-profile.yaml")

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

    @staticmethod
    def _d5_journal_profile_lessons(profile_path: Path) -> list[LessonLearned]:
        """Check journal-profile.yaml presence and mandatory fields."""
        lessons = []
        if not profile_path.is_file():
            lessons.append(
                LessonLearned(
                    category="configuration_gap",
                    lesson="journal-profile.yaml missing — no journal-specific formatting rules",
                    source="D5 completeness check",
                    severity="warning",
                )
            )
            return lessons

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
        return lessons
