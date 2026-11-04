"""The ``AutonomousAuditLoop`` state machine composed from its mixins."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._lifecycle import LifecycleMixin
from ._models import AuditFix, AuditIssue, AuditLoopConfig, RoundRecord
from ._queries import QueryMixin
from ._report import ReportMixin
from ._state_validation import validate_serialized_state

# ── Main Engine ────────────────────────────────────────────────────────


class AutonomousAuditLoop(LifecycleMixin, QueryMixin, ReportMixin):
    """
    Multi-round autonomous paper quality audit engine.

    Usage by Agent:
        loop = AutonomousAuditLoop(audit_dir, config=AuditLoopConfig(
            max_rounds=3, quality_threshold=7.0, context="hook-a-methods"
        ))
        loop.load()  # resume from checkpoint if exists

        while True:
            ctx = loop.start_round()
            # Agent runs hooks, records issues...
            loop.record_issue("A1", Severity.CRITICAL, "Word count 20% over",
                              "Trim verbose sentences", section="Methods")
            # Agent applies fixes...
            loop.record_fix(0, "trim_sentences", True, "Reduced by 150 words")
            # Submit scores and get verdict
            scores = {"text_quality": 7.5, "citation_quality": 8.0, ...}
            verdict = loop.complete_round(scores)
            if verdict != RoundVerdict.CONTINUE:
                break

        report = loop.generate_report()
    """

    def __init__(
        self,
        audit_dir: str | Path,
        config: AuditLoopConfig | None = None,
    ) -> None:
        self._audit_dir = Path(audit_dir)
        self._config = config or AuditLoopConfig()
        ctx = self._config.context
        self._data_path = self._audit_dir / f"audit-loop-{ctx}.json"
        self._report_path = self._audit_dir / f"audit-loop-{ctx}.md"

        # State
        self._rounds: list[RoundRecord] = []
        self._current_issues: list[AuditIssue] = []
        self._current_fixes: list[AuditFix] = []
        self._current_round: int = 0
        self._in_round: bool = False
        self._round_start_time: str = ""
        self._completed: bool = False
        self._rewrite_sections: list[str] = []
        self._rewrite_reason: str = ""

    @classmethod
    def validate_serialized_state(cls, data: Any) -> list[str]:
        """Recompute persisted scores and verdicts instead of trusting JSON labels.

        The audit-loop file is intentionally human-readable, so a phase gate must
        treat it as untrusted input.  This verifier reconstructs the state machine
        round by round and returns every integrity error it finds.  It performs no
        writes and is safe to call from prerequisite and release gates.
        """
        return validate_serialized_state(cls, data)
