"""Writing Hooks — Data artifact validation mixin (F-series: F1–F4)."""

from __future__ import annotations

import structlog

from ._models import HookIssue, HookResult

logger = structlog.get_logger()


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

        issues: list[HookIssue] = []
        for raw_issue in validation.get("issues", []):
            category = raw_issue.get("category", "")
            # Map categories to hook sub-IDs
            if category in ("provenance_missing", "no_provenance_code"):
                hook_sub = "F1"
            elif category in ("manifest_missing", "phantom_file"):
                hook_sub = "F2"
            elif category in ("phantom_reference", "orphan_asset"):
                hook_sub = "F3"
            elif category == "unverified_stats":
                hook_sub = "F4"
            else:
                hook_sub = "F"

            issues.append(
                HookIssue(
                    hook_id=hook_sub,
                    severity=raw_issue.get("severity", "WARNING"),
                    section="Data Artifacts",
                    message=raw_issue.get("message", ""),
                )
            )

        passed = validation.get("passed", True)
        stats = validation.get("summary", {})

        logger.info(
            "Hook F complete",
            passed=passed,
            critical=stats.get("critical_issues", 0),
            warnings=stats.get("warning_issues", 0),
        )
        return HookResult(hook_id="F", passed=passed, issues=issues, stats=stats)
