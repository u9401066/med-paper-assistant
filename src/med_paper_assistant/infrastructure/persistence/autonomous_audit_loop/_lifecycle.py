"""Round lifecycle of the audit loop: start, record issues/fixes, complete, rewrite."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

import structlog

from ..audit_scores import validate_round_scores
from ._models import AuditFix, AuditIssue, RoundRecord, RoundVerdict, Severity
from ._persistence import PersistenceMixin
from ._verdict import VerdictMixin

logger = structlog.get_logger()


class LifecycleMixin(VerdictMixin, PersistenceMixin):
    """Agent-driven round lifecycle (start → record → complete / request_rewrite)."""

    # ── Round Lifecycle ────────────────────────────────────────────

    def start_round(self, artifact_hash: str = "") -> dict[str, Any]:
        """Start a new audit round. Returns context for the Agent.

        Args:
            artifact_hash: Hash of the primary artifact (e.g. manuscript) at round start.
                          Used to verify the artifact was actually modified during the round.
        """
        if self._completed:
            raise RuntimeError("Audit loop already completed")
        if self._in_round:
            raise RuntimeError("Previous round not completed — call complete_round() first")

        self._current_round += 1
        self._current_issues = []
        self._current_fixes = []
        self._in_round = True
        self._round_start_time = datetime.now().astimezone().isoformat()
        self._artifact_hash_start = artifact_hash

        # Carry forward persistent critical issues from previous round
        persistent = self._get_persistent_issues()

        return {
            "round": self._current_round,
            "max_rounds": self._config.max_rounds,
            "quality_threshold": self._config.quality_threshold,
            "context": self._config.context,
            "previous_score": self._rounds[-1].weighted_avg if self._rounds else None,
            "persistent_issues": persistent,
            "focus_dimensions": self._get_weak_dimensions(),
        }

    def record_issue(
        self,
        hook_id: str,
        severity: Severity | str,
        description: str,
        suggested_fix: str,
        section: str | None = None,
    ) -> int:
        """Record a quality issue found during this round. Returns issue index."""
        if not self._in_round:
            raise RuntimeError("No active round — call start_round() first")

        sev = severity.value if isinstance(severity, Severity) else severity
        persistent_count = self._count_persistent(hook_id, description)

        issue = AuditIssue(
            hook_id=hook_id,
            severity=sev,
            description=description,
            suggested_fix=suggested_fix,
            section=section,
            persistent_rounds=persistent_count,
        )
        self._current_issues.append(issue)
        return len(self._current_issues) - 1

    def record_fix(
        self,
        issue_index: int,
        strategy: str,
        success: bool,
        details: str = "",
    ) -> None:
        """Record a fix applied for an issue."""
        if not self._in_round:
            raise RuntimeError("No active round — call start_round() first")
        if issue_index < 0 or issue_index >= len(self._current_issues):
            raise IndexError(f"Issue index {issue_index} out of range")

        fix = AuditFix(
            issue_index=issue_index,
            strategy=strategy,
            success=success,
            details=details,
        )
        self._current_fixes.append(fix)

        if success:
            self._current_issues[issue_index].fixed = True

    def complete_round(self, scores: dict[str, float], artifact_hash: str = "") -> RoundVerdict:
        """Complete the current round with quality scores. Returns verdict.

        Args:
            scores: Quality dimension scores.
            artifact_hash: Hash of the primary artifact at round end.
                          Compared with start hash to verify modification.
        """
        if not self._in_round:
            raise RuntimeError("No active round — call start_round() first")

        validate_round_scores(scores, self._config.dimension_weights)
        weighted_avg = self._compute_weighted_avg(scores)

        record = RoundRecord(
            round_number=self._current_round,
            issues=[asdict(i) for i in self._current_issues],
            fixes=[asdict(f) for f in self._current_fixes],
            scores=scores,
            weighted_avg=round(weighted_avg, 2),
            started_at=self._round_start_time,
            completed_at=datetime.now().astimezone().isoformat(),
            artifact_hash_start=getattr(self, "_artifact_hash_start", ""),
            artifact_hash_end=artifact_hash,
        )

        verdict = self._determine_verdict(weighted_avg)
        record.verdict = verdict.value
        self._rounds.append(record)
        self._in_round = False

        if verdict != RoundVerdict.CONTINUE:
            self._completed = True

        self.save()
        return verdict

    def request_rewrite(self, sections: list[str], reason: str) -> None:
        """Mark sections for rewrite regression to Phase 5.

        Called when review determines that patch_draft fixes are insufficient
        and a section needs a full rewrite. Sets the verdict to REWRITE_NEEDED
        and records which sections need rewriting.

        Args:
            sections: List of section names that need rewriting.
            reason: Explanation of why rewrite is needed.
        """
        if not sections:
            raise ValueError("Must specify at least one section to rewrite")
        self._rewrite_sections = list(sections)
        self._rewrite_reason = reason
        self._completed = True

        # Record a synthetic round record if we're mid-round
        if self._in_round:
            record = RoundRecord(
                round_number=self._current_round,
                issues=[asdict(i) for i in self._current_issues],
                fixes=[asdict(f) for f in self._current_fixes],
                scores={},
                weighted_avg=0.0,
                verdict=RoundVerdict.REWRITE_NEEDED.value,
                started_at=self._round_start_time,
                completed_at=datetime.now().astimezone().isoformat(),
            )
            self._rounds.append(record)
            self._in_round = False

        self.save()
        logger.info(
            "Rewrite requested",
            sections=sections,
            reason=reason,
            round=self._current_round,
        )

    @property
    def rewrite_sections(self) -> list[str]:
        """Sections that need rewriting (set by request_rewrite)."""
        return self._rewrite_sections

    @property
    def rewrite_reason(self) -> str:
        """Reason for rewrite request."""
        return self._rewrite_reason
