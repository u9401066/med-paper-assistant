"""R4 — Review-Fix Traceability."""

from __future__ import annotations

import re
from pathlib import Path

from ..writing_hooks._models import HookIssue, HookResult


def _manuscript_unchanged_issue(accept_count: int) -> HookIssue:
    return HookIssue(
        hook_id="R4",
        severity="CRITICAL",
        section="review",
        message=f"{accept_count} issues ACCEPT'd but manuscript was NOT modified",
        suggestion="Apply the accepted fixes to the manuscript using patch_draft()",
    )


def _inconsistent_fix_count_issue(accept_count: int) -> HookIssue:
    return HookIssue(
        hook_id="R4",
        severity="WARNING",
        section="review",
        message=f"{accept_count} issues ACCEPT'd but issues_fixed=0 — inconsistent",
        suggestion=f"Set issues_fixed={accept_count} or higher to reflect accepted changes",
    )


class FixTraceabilityMixin:
    """R4: ACCEPT'd issues must produce manuscript changes."""

    _audit_dir: Path

    def check_review_fix_traceability(
        self,
        round_num: int,
        issues_fixed: int,
        manuscript_changed: bool,
    ) -> HookResult:
        """
        R4: Verify ACCEPT'd issues actually produced manuscript changes.

        Checks:
        - If issues_fixed > 0, manuscript MUST have changed
        - ACCEPT'd issues should have corresponding changes described in response
        """
        issues: list[HookIssue] = []

        response_path = self._audit_dir / f"author-response-{round_num}.md"
        accept_count = 0
        if response_path.is_file():
            content = response_path.read_text(encoding="utf-8")
            accept_count = len(re.findall(r"\bACCEPT\b", content, re.IGNORECASE))

        # Core traceability: accepted issues should have produced changes
        if accept_count > 0 and not manuscript_changed:
            issues.append(_manuscript_unchanged_issue(accept_count))

        # Check issues_fixed vs accept_count consistency
        if accept_count > 0 and issues_fixed == 0:
            issues.append(_inconsistent_fix_count_issue(accept_count))

        # Check for change descriptions in response (look for "Changed:", "Fixed:", "Updated:", etc.)
        if response_path.is_file() and accept_count > 0:
            if not self._has_change_descriptions(response_path):
                issues.append(self._missing_change_description_issue())

        passed = all(i.severity != "CRITICAL" for i in issues)
        stats = {
            "accept_count": accept_count,
            "issues_fixed": issues_fixed,
            "manuscript_changed": manuscript_changed,
        }
        return HookResult(hook_id="R4", passed=passed, issues=issues, stats=stats)

    @staticmethod
    def _has_change_descriptions(response_path: Path) -> bool:
        content = response_path.read_text(encoding="utf-8")
        change_descriptors = len(
            re.findall(
                r"(?:changed|modified|updated|revised|added|removed|rewrote|corrected|fixed|edited)",
                content,
                re.IGNORECASE,
            )
        )
        return change_descriptors > 0

    @staticmethod
    def _missing_change_description_issue() -> HookIssue:
        return HookIssue(
            hook_id="R4",
            severity="WARNING",
            section="review",
            message="Author response lacks change descriptions — each ACCEPT should describe what was changed",
            suggestion="Add change descriptions (e.g., 'Changed: rewrote paragraph 3 of Discussion to clarify...')",
        )
