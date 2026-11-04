"""D7/D8 analyses: review-loop and EQUATOR retrospectives over `.audit/` artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._models import LessonLearned


class ReviewRetrospectiveMixin:
    """Lessons derived from review reports, author responses and EQUATOR reports."""

    _audit_dir: Path

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

        lessons.extend(self._d7_review_loop_lessons(audit_dir / "audit-loop-review.json"))

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

    @classmethod
    def _d7_review_loop_lessons(cls, loop_file: Path) -> list[LessonLearned]:
        """Check review loop data for hash integrity and unaddressed issues."""
        if not loop_file.is_file():
            return []
        try:
            loop_data = json.loads(loop_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        lessons: list[LessonLearned] = []
        for r in loop_data.get("rounds", []):
            lessons.extend(cls._d7_round_lessons(r))
        return lessons

    @staticmethod
    def _d7_round_lessons(r: dict[str, Any]) -> list[LessonLearned]:
        """Lessons for one review round entry."""
        lessons = []
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
        return lessons

    def _d8_equator_retrospective(self) -> list[LessonLearned]:
        """D8: Analyze EQUATOR compliance reports to evolve detection logic."""
        equator_reports = sorted(self._audit_dir.glob("equator-compliance-*.md"))
        if not equator_reports:
            return [
                LessonLearned(
                    category="equator_gap",
                    lesson="No EQUATOR compliance reports found — reporting guideline check may not have run",
                    source="D8 EQUATOR retrospective",
                    severity="info",
                )
            ]

        # Read latest EQUATOR compliance and check for gaps
        try:
            content = equator_reports[-1].read_text(encoding="utf-8")
        except OSError:
            return []
        return self._d8_report_lessons(content)

    @staticmethod
    def _d8_report_lessons(content: str) -> list[LessonLearned]:
        """Look for non-compliant and partially compliant items."""
        lessons = []
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
        return lessons
