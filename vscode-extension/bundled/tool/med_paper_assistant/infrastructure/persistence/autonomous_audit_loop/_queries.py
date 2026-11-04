"""Read-only status and trend queries for the audit loop."""

from __future__ import annotations

from typing import Any

from ._base import LoopState
from ._models import RoundVerdict


class QueryMixin(LoopState):
    """Read-only accessors over the audit-loop state."""

    # ── Query Methods ──────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Get current loop status."""
        latest = self._rounds[-1].weighted_avg if self._rounds else None
        return {
            "context": self._config.context,
            "current_round": self._current_round,
            "max_rounds": self._config.max_rounds,
            "total_rounds_completed": len(self._rounds),
            "in_round": self._in_round,
            "completed": self._completed,
            "quality_threshold": self._config.quality_threshold,
            "latest_score": latest,
            "latest_weighted_score": latest,  # alias used by tools/review/pipeline_gate/
            "latest_verdict": self._rounds[-1].verdict if self._rounds else None,
            "score_trend": [r.weighted_avg for r in self._rounds],
        }

    def get_score_trend(self) -> list[dict[str, Any]]:
        """Get score progression across rounds."""
        return [
            {
                "round": r.round_number,
                "weighted_avg": r.weighted_avg,
                "scores": r.scores,
                "issues_count": len(r.issues),
                "fixes_count": len(r.fixes),
                "verdict": r.verdict,
            }
            for r in self._rounds
        ]

    @property
    def is_completed(self) -> bool:
        return self._completed

    @property
    def current_round_number(self) -> int:
        return self._current_round

    @property
    def latest_verdict(self) -> RoundVerdict | None:
        if not self._rounds:
            return None
        return RoundVerdict(self._rounds[-1].verdict)
