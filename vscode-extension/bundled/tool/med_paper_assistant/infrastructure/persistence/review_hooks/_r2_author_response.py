"""R2 — Author Response Completeness."""

from __future__ import annotations

import re
from pathlib import Path

from ..writing_hooks._models import HookIssue, HookResult
from ._constants import MAX_DECLINE_RATIO
from ._report_parsing import ReportParsingMixin


def _count_accepts_with_evidence(content: str) -> int:
    """Count ACCEPT blocks that cite evidence, wikilinks or literature."""
    accept_sections = re.findall(
        r"(?:ACCEPT|accept)[^\n]*(?:\n(?!\s*(?:ACCEPT|DECLINE|#{1,3}\s)).*){0,5}",
        content,
    )
    accepts_with_evidence = 0
    for section in accept_sections:
        if re.search(
            r"\[\[.*?\]\]|doi|pmid|reference|evidence|support|literature|study|data",
            section,
            re.IGNORECASE,
        ):
            accepts_with_evidence += 1
    return accepts_with_evidence


def _decline_ratio_issue(decline_count: int, total_decisions: int) -> HookIssue | None:
    decline_ratio = decline_count / total_decisions
    if decline_ratio <= MAX_DECLINE_RATIO:
        return None
    return HookIssue(
        hook_id="R2",
        severity="CRITICAL",
        section="review",
        message=f"DECLINE ratio {decline_ratio:.0%} exceeds maximum {MAX_DECLINE_RATIO:.0%} ({decline_count}/{total_decisions} declined)",
        suggestion="Re-evaluate declined issues — provide stronger justification or accept more reviewer suggestions",
    )


def _missing_response_result(round_num: int) -> HookResult:
    issue = HookIssue(
        hook_id="R2",
        severity="CRITICAL",
        section="review",
        message=f"author-response-{round_num}.md not found",
        suggestion="Write the author response before submitting",
    )
    return HookResult(hook_id="R2", passed=False, issues=[issue])


class AuthorResponseMixin(ReportParsingMixin):
    """R2: every review issue answered, DECLINE ratio bounded."""

    _audit_dir: Path

    def check_author_response_completeness(self, round_num: int) -> HookResult:
        """
        R2: Verify author response addresses ALL review issues.

        Checks:
        - author-response-{N}.md exists
        - Every issue has ACCEPT or DECLINE with reason
        - DECLINE ratio ≤ 50% (can't just reject everything)
        - ACCEPTED issues should have evidence or reference support
        """
        issues: list[HookIssue] = []
        response_path = self._audit_dir / f"author-response-{round_num}.md"

        if not response_path.is_file():
            return _missing_response_result(round_num)

        content = response_path.read_text(encoding="utf-8")

        # Count ACCEPT / DECLINE
        accept_count = len(re.findall(r"\bACCEPT\b", content, re.IGNORECASE))
        decline_count = len(re.findall(r"\bDECLINE\b", content, re.IGNORECASE))
        total_decisions = accept_count + decline_count

        issues.extend(self._r2_decision_issues(round_num, decline_count, total_decisions))

        # Check for evidence/reference support in responses
        # Look for citation wikilinks or "evidence" / "reference" mentions near ACCEPT
        accepts_with_evidence = _count_accepts_with_evidence(content)
        if accept_count > 0 and accepts_with_evidence == 0:
            issues.append(self._r2_no_evidence_issue())

        passed = all(i.severity != "CRITICAL" for i in issues)
        stats = {
            "accept_count": accept_count,
            "decline_count": decline_count,
            "total_decisions": total_decisions,
            "decline_ratio": round(decline_count / total_decisions, 2)
            if total_decisions > 0
            else 0,
            "accepts_with_evidence": accepts_with_evidence,
        }
        return HookResult(hook_id="R2", passed=passed, issues=issues, stats=stats)

    def _r2_decision_issues(
        self, round_num: int, decline_count: int, total_decisions: int
    ) -> list[HookIssue]:
        """Missing decisions, unaddressed review issues and excessive DECLINE ratio."""
        if total_decisions == 0:
            return [
                HookIssue(
                    hook_id="R2",
                    severity="CRITICAL",
                    section="review",
                    message="No ACCEPT/DECLINE decisions found in author response",
                    suggestion="Each review issue must be explicitly ACCEPT'd or DECLINE'd with reasoning",
                )
            ]

        issues: list[HookIssue] = []
        # Cross-check with review report
        report_path = self._audit_dir / f"review-report-{round_num}.md"
        if report_path.is_file():
            report_content = report_path.read_text(encoding="utf-8")
            report_issue_count = self._count_total_issues_in_report(report_content)
            if report_issue_count > 0 and total_decisions < report_issue_count:
                issues.append(
                    HookIssue(
                        hook_id="R2",
                        severity="CRITICAL",
                        section="review",
                        message=f"Only {total_decisions}/{report_issue_count} review issues addressed in author response",
                        suggestion="Every issue in the review report must have an ACCEPT or DECLINE decision",
                    )
                )

        # DECLINE ratio check
        ratio_issue = _decline_ratio_issue(decline_count, total_decisions)
        if ratio_issue is not None:
            issues.append(ratio_issue)
        return issues

    @staticmethod
    def _r2_no_evidence_issue() -> HookIssue:
        return HookIssue(
            hook_id="R2",
            severity="WARNING",
            section="review",
            message="None of the ACCEPT'd fixes reference supporting evidence or literature",
            suggestion="When accepting reviewer comments, cite references or data to strengthen revisions (use [[wikilink]] or mention specific studies)",
        )
