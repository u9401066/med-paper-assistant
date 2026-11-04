"""R5 — Post-Review Anti-AI Gate."""

from __future__ import annotations

from pathlib import Path

from ..writing_hooks._models import HookIssue, HookResult


def _elevate_issues(source_issues: list[HookIssue], label: str) -> list[HookIssue]:
    """Re-label A3/A3b/A3c issues as R5 issues."""
    return [
        HookIssue(
            hook_id="R5",
            severity=issue.severity,
            section=issue.section,
            message=f"[Post-Review {label}] {issue.message}",
            location=issue.location,
            suggestion=issue.suggestion,
        )
        for issue in source_issues
    ]


class PostReviewAntiAIMixin:
    """R5: re-run Anti-AI detection after review edits."""

    _project_dir: Path

    def check_post_review_anti_ai(self, manuscript_content: str) -> HookResult:
        """
        R5: Re-run Anti-AI detection after review edits.

        Review fixes can inadvertently re-introduce AI-characteristic language.
        Delegates to WritingHooksEngine A3/A3b/A3c and aggregates.
        """
        from ..writing_hooks import WritingHooksEngine

        engine = WritingHooksEngine(self._project_dir)
        a3_result = engine.check_anti_ai_patterns(manuscript_content)
        a3b_result = engine.check_ai_writing_signals(manuscript_content)
        a3c_result = engine.check_voice_consistency(manuscript_content)

        # Elevate A3/A3b/A3c issues as R5 issues
        issues: list[HookIssue] = []
        issues.extend(_elevate_issues(a3_result.issues, "A3"))
        issues.extend(_elevate_issues(a3b_result.issues, "A3b"))
        issues.extend(_elevate_issues(a3c_result.issues, "A3c"))

        passed = a3_result.passed and a3b_result.passed and a3c_result.passed
        stats = {
            "a3_passed": a3_result.passed,
            "a3b_passed": a3b_result.passed,
            "a3c_passed": a3c_result.passed,
            "a3_critical": a3_result.critical_count,
            "a3b_critical": a3b_result.critical_count,
            "a3c_outliers": a3c_result.stats.get("outlier_count", 0),
            "total_ai_issues": len(issues),
        }
        return HookResult(hook_id="R5", passed=passed, issues=issues, stats=stats)
