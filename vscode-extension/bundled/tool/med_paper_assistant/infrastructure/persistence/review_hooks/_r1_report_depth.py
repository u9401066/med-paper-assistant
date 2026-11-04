"""R1 — Review Report Depth."""

from __future__ import annotations

from pathlib import Path

from ..writing_hooks._models import HookIssue, HookResult
from ._constants import MIN_PERSPECTIVES, MIN_REVIEW_REPORT_WORDS, REVIEWER_PERSPECTIVES
from ._report_parsing import ReportParsingMixin


def _severity_issue(major_count: int, minor_count: int) -> HookIssue | None:
    """Issue for a report that classifies nothing, or finds no major concern."""
    if major_count == 0 and minor_count == 0:
        return HookIssue(
            hook_id="R1",
            severity="CRITICAL",
            section="review",
            message="No issues classified by severity — review must identify issues as major/minor/optional",
            suggestion="Add severity classification to each issue (use YAML frontmatter or section headings)",
        )
    if major_count == 0:
        return HookIssue(
            hook_id="R1",
            severity="WARNING",
            section="review",
            message="No major issues found — a thorough review typically identifies at least one major concern",
            suggestion="Re-examine methodology, statistical approach, or conceptual gaps for potential major issues",
        )
    return None


def _missing_report_result(round_num: int) -> HookResult:
    issue = HookIssue(
        hook_id="R1",
        severity="CRITICAL",
        section="review",
        message=f"review-report-{round_num}.md not found",
        suggestion="Write the review report before submitting",
    )
    return HookResult(hook_id="R1", passed=False, issues=[issue])


class ReportDepthMixin(ReportParsingMixin):
    """R1: report word count, reviewer perspectives and severity breakdown."""

    _audit_dir: Path

    def check_review_report_depth(self, round_num: int) -> HookResult:
        """
        R1: Verify review report is substantive and multi-perspective.

        Checks:
        - Report word count ≥ MIN_REVIEW_REPORT_WORDS (300)
        - ≥ 3 reviewer perspectives mentioned
        - Issues categorised by severity (major/minor/optional)
        - At least 1 major issue identified (reviews always find something)
        """
        issues: list[HookIssue] = []
        report_path = self._audit_dir / f"review-report-{round_num}.md"

        if not report_path.is_file():
            return _missing_report_result(round_num)

        content = report_path.read_text(encoding="utf-8")
        words = len(content.split())
        content_lower = content.lower()
        found_perspectives = [p for p in REVIEWER_PERSPECTIVES if p in content_lower]

        # Severity breakdown — parse YAML frontmatter or headings
        major_count = self._count_severity_in_report(content, "major")
        minor_count = self._count_severity_in_report(content, "minor")

        for issue in (
            self._r1_length_issue(words),
            self._r1_perspective_issue(found_perspectives),
            _severity_issue(major_count, minor_count),
        ):
            if issue is not None:
                issues.append(issue)

        passed = all(i.severity != "CRITICAL" for i in issues)
        stats = {
            "report_words": words,
            "perspectives_found": found_perspectives,
            "perspective_count": len(found_perspectives),
            "major_issues": major_count,
            "minor_issues": minor_count,
        }
        return HookResult(hook_id="R1", passed=passed, issues=issues, stats=stats)

    @staticmethod
    def _r1_length_issue(words: int) -> HookIssue | None:
        if words >= MIN_REVIEW_REPORT_WORDS:
            return None
        return HookIssue(
            hook_id="R1",
            severity="CRITICAL",
            section="review",
            message=f"Review report too short: {words} words (minimum {MIN_REVIEW_REPORT_WORDS})",
            suggestion="Expand review with deeper analysis across methodology, domain, statistics, and writing quality",
        )

    @staticmethod
    def _r1_perspective_issue(found_perspectives: list[str]) -> HookIssue | None:
        if len(found_perspectives) >= MIN_PERSPECTIVES:
            return None
        return HookIssue(
            hook_id="R1",
            severity="CRITICAL",
            section="review",
            message=f"Only {len(found_perspectives)}/{MIN_PERSPECTIVES} reviewer perspectives found: {found_perspectives}",
            suggestion=f"Review must cover ≥{MIN_PERSPECTIVES} perspectives from: {REVIEWER_PERSPECTIVES}",
        )
