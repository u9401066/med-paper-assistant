"""Writing Hooks — Data artifact validation mixin (F-series: F1–F4)."""

from __future__ import annotations

from typing import Any

import structlog

from ._models import HookIssue, HookResult

logger = structlog.get_logger()

_SUB_HOOK_IDS: dict[str, str] = {
    "provenance_missing": "F1",
    "no_provenance_code": "F1",
    "asset_review_missing": "F1",
    "asset_review_incomplete": "F1",
    "caption_unreviewed": "F1",
    "manifest_missing": "F2",
    "phantom_file": "F2",
    "phantom_reference": "F3",
    "orphan_asset": "F3",
    "unverified_stats": "F4",
    "data_anchor_unverified": "F4",
    "data_anchor_untrusted_source": "F4",
    "data_anchor_uningested_source": "F4",
}


def _to_hook_issue(raw_issue: dict[str, Any]) -> HookIssue:
    category = raw_issue.get("category", "")
    return HookIssue(
        hook_id=_SUB_HOOK_IDS.get(category, "F"),
        severity=raw_issue.get("severity", "WARNING"),
        section="Data Artifacts",
        message=raw_issue.get("message", ""),
    )


class DataArtifactsMixin:
    """F-series hooks: data artifact traceability and consistency."""

    def validate_data_artifacts(
        self,
        draft_content: str | None = None,
    ) -> HookResult:
        """
        Hook F1-F4: Formal data artifact validation for pipeline integration.

        Wraps DataArtifactTracker.validate_cross_references() and adds
        severity classification matching the hook framework.

        F1: Provenance tracking (every artifact has tool + params + code)
        F2: Manifest ↔ file consistency (no phantom/orphan files)
        F3: Draft ↔ manifest cross-reference (no phantom/orphan references)
        F4: Statistical claim verification (claims backed by artifacts)

        Args:
            draft_content: Full manuscript text. If None, skips draft checks (F3, F4).

        Returns:
            HookResult with structured issues from all F sub-checks.
        """
        from ..data_artifact_tracker import DataArtifactTracker

        audit_dir = self._audit_dir
        tracker = DataArtifactTracker(audit_dir, self._project_dir)
        validation = tracker.validate_cross_references(draft_content)

        issues = [_to_hook_issue(raw_issue) for raw_issue in validation.get("issues", [])]

        passed = validation.get("passed", True)
        stats = validation.get("summary", {})

        logger.info(
            "Hook F complete",
            passed=passed,
            critical=stats.get("critical_issues", 0),
            warnings=stats.get("warning_issues", 0),
        )
        return HookResult(hook_id="F", passed=passed, issues=issues, stats=stats)
