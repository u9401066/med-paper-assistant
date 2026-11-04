"""Verdict, scoring and issue-tracking logic of the audit-loop state machine."""

from __future__ import annotations

from typing import Any

from ._base import LoopState
from ._models import RoundVerdict, Severity


class VerdictMixin(LoopState):
    """Decides whether a round continues, stops or escalates."""

    # ── Verdict Logic ──────────────────────────────────────────────

    def _determine_verdict(self, weighted_avg: float) -> RoundVerdict:
        """Determine whether to continue, stop, or escalate."""
        cfg = self._config

        # 0. Minimum rounds not yet reached → must continue
        if self._current_round < cfg.min_rounds:
            return RoundVerdict.CONTINUE

        # 1. Quality threshold met (only after min_rounds)
        if weighted_avg >= cfg.quality_threshold:
            return RoundVerdict.QUALITY_MET

        # 2. Max rounds reached
        if self._current_round >= cfg.max_rounds:
            return RoundVerdict.MAX_ROUNDS

        # 3. Persistent critical issues that can't be fixed → need user
        unfixed_critical = [
            i
            for i in self._current_issues
            if i.severity == Severity.CRITICAL.value and not i.fixed and i.persistent_rounds >= 2
        ]
        if unfixed_critical:
            return RoundVerdict.USER_NEEDED

        # 4. Stagnation detection
        if self._is_stagnated():
            return RoundVerdict.STAGNATED

        return RoundVerdict.CONTINUE

    def _is_stagnated(self) -> bool:
        """Check if scores have stagnated (no meaningful improvement)."""
        cfg = self._config
        n = cfg.stagnation_rounds

        # Need at least n+1 rounds to detect stagnation (current + n previous)
        total = len(self._rounds) + 1  # +1 for the round being completed
        if total <= n:
            return False

        # We check the already-recorded rounds
        if len(self._rounds) < n:
            return False

        recent = [r.weighted_avg for r in self._rounds[-n:]]
        # Check if all consecutive deltas are below threshold
        for i in range(1, len(recent)):
            if recent[i] - recent[i - 1] >= cfg.stagnation_delta:
                return False
        return True

    # ── Score Computation ──────────────────────────────────────────

    def _compute_weighted_avg(self, scores: dict[str, float]) -> float:
        """Compute weighted average from dimension scores."""
        weights = self._config.dimension_weights
        total_weight = 0.0
        total_score = 0.0

        for dim, weight in weights.items():
            if dim in scores:
                total_score += scores[dim] * weight
                total_weight += weight

        if total_weight == 0:
            return 0.0
        return total_score / total_weight

    # ── Issue Tracking Helpers ─────────────────────────────────────

    def _get_persistent_issues(self) -> list[dict[str, Any]]:
        """Get issues that persisted across previous rounds (unfixed criticals)."""
        if not self._rounds:
            return []

        last = self._rounds[-1]
        return [
            i
            for i in last.issues
            if i.get("severity") == Severity.CRITICAL.value and not i.get("fixed")
        ]

    def _count_persistent(self, hook_id: str, description: str) -> int:
        """Count how many previous rounds had a similar issue."""
        count = 0
        for r in self._rounds:
            for issue in r.issues:
                if issue.get("hook_id") == hook_id and not issue.get("fixed"):
                    # Fuzzy match: same hook + not fixed = likely persistent
                    count += 1
                    break
        return count

    def _get_weak_dimensions(self) -> list[str]:
        """Identify dimensions that need the most improvement."""
        if not self._rounds:
            return []

        last_scores = self._rounds[-1].scores
        threshold = self._config.quality_threshold

        weak = [(dim, score) for dim, score in last_scores.items() if score < threshold]
        # Sort by score ascending (weakest first)
        weak.sort(key=lambda x: x[1])
        return [dim for dim, _ in weak]
