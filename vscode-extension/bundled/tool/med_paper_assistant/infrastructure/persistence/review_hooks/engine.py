"""ReviewHooksEngine — composes the R1–R6 check mixins."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from ..writing_hooks._models import HookResult
from ._r1_report_depth import ReportDepthMixin
from ._r2_author_response import AuthorResponseMixin
from ._r3_equator import EquatorComplianceMixin
from ._r4_traceability import FixTraceabilityMixin
from ._r5_anti_ai import PostReviewAntiAIMixin
from ._r6_citation_budget import CitationBudgetMixin

logger = structlog.get_logger()


class ReviewHooksEngine(
    ReportDepthMixin,
    AuthorResponseMixin,
    EquatorComplianceMixin,
    FixTraceabilityMixin,
    PostReviewAntiAIMixin,
    CitationBudgetMixin,
):
    """
    Code-enforced review quality hooks (R1–R6).

    Usage:
        engine = ReviewHooksEngine(project_dir)
        r1 = engine.check_review_report_depth(round_num)
        r2 = engine.check_author_response_completeness(round_num)
        ...
    """

    def __init__(self, project_dir: str | Path) -> None:
        self._project_dir = Path(project_dir)
        self._audit_dir = self._project_dir / ".audit"
        self._journal_profile: dict[str, Any] | None = None
        self._load_journal_profile()

    def _load_journal_profile(self) -> None:
        """Load journal-profile.yaml if available."""
        profile_path = self._project_dir / "journal-profile.yaml"
        if profile_path.is_file():
            try:
                import yaml

                with open(profile_path, encoding="utf-8") as f:
                    self._journal_profile = yaml.safe_load(f) or {}
            except Exception:
                logger.warning("Failed to load journal-profile.yaml")
                self._journal_profile = None

    # ── Batch Runner ───────────────────────────────────────────────

    def run_all(
        self,
        round_num: int,
        issues_fixed: int = 0,
        manuscript_changed: bool = True,
        manuscript_content: str = "",
    ) -> dict[str, HookResult]:
        """
        Run all R-series hooks for a review round.

        Returns dict mapping hook_id -> HookResult.
        """
        results: dict[str, HookResult] = {}
        results["R1"] = self.check_review_report_depth(round_num)
        results["R2"] = self.check_author_response_completeness(round_num)
        results["R3"] = self.check_equator_compliance(round_num)
        results["R4"] = self.check_review_fix_traceability(
            round_num,
            issues_fixed,
            manuscript_changed,
        )
        if manuscript_content:
            results["R5"] = self.check_post_review_anti_ai(manuscript_content)
            results["R6"] = self.check_citation_budget(manuscript_content)
        return results
