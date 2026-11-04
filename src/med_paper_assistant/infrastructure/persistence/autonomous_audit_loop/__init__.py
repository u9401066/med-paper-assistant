"""
Autonomous Audit Loop — Multi-round self-improving paper quality audit engine.

Orchestrates iterative evaluate → fix → re-evaluate cycles until paper quality
meets the configured threshold, stagnates, or hits the round limit.

Architecture:
  Infrastructure layer service. Used by the Agent during Phase 5 (Hook A/B),
  Phase 6 (Hook C), and Phase 7 (Autonomous Review) of the auto-paper pipeline.

  The engine is a STATE MACHINE — it does NOT run checks or apply fixes itself.
  Instead, the Agent drives it:
    1. loop.start_round()       → get context for this round
    2. loop.record_issue(...)   → log each quality issue found
    3. loop.record_fix(...)     → log each fix applied
    4. loop.complete_round(scores) → submit scores, get verdict

  Integrates with:
    - QualityScorecard: score tracking per dimension
    - HookEffectivenessTracker: hook event recording

  Persists state to `.audit/audit-loop-{context}.json` for checkpoint recovery.

Stop conditions (Ralph Wiggum–proof):
  - QUALITY_MET:  weighted avg ≥ quality_threshold
  - MAX_ROUNDS:   reached max_rounds limit
  - STAGNATED:    score improved < stagnation_delta for N consecutive rounds
  - USER_NEEDED:  critical issues failed to fix across 2+ rounds
  - REWRITE_NEEDED: section(s) need major rewrite → regress to Phase 5
"""

from __future__ import annotations

from ._models import (
    AuditFix,
    AuditIssue,
    AuditLoopConfig,
    RoundRecord,
    RoundVerdict,
    Severity,
)
from ._policy import (
    REVIEW_MAX_ROUNDS_LIMIT,
    REVIEW_MIN_ROUNDS_FLOOR,
    REVIEW_QUALITY_THRESHOLD_FLOOR,
    validate_review_config_policy,
)
from .engine import AutonomousAuditLoop

__all__ = [
    "REVIEW_MAX_ROUNDS_LIMIT",
    "REVIEW_MIN_ROUNDS_FLOOR",
    "REVIEW_QUALITY_THRESHOLD_FLOOR",
    "AuditFix",
    "AuditIssue",
    "AuditLoopConfig",
    "AutonomousAuditLoop",
    "RoundRecord",
    "RoundVerdict",
    "Severity",
    "validate_review_config_policy",
]
