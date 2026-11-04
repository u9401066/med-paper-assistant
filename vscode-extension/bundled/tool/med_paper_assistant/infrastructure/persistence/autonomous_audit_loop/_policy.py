"""Phase 7 review-configuration policy for the autonomous audit loop."""

from __future__ import annotations

import math

from ._models import AuditLoopConfig

# Phase 7 is a release-quality gate, so callers may make it stricter but may
# not lower these repository policy floors.  Keeping the policy beside the
# state machine also lets the persisted-state verifier reject hand-edited
# configurations instead of merely recomputing a verdict against an
# attacker-controlled threshold.
REVIEW_MIN_ROUNDS_FLOOR = 2
REVIEW_QUALITY_THRESHOLD_FLOOR = 7.0
REVIEW_MAX_ROUNDS_LIMIT = 10


def validate_review_config_policy(config: AuditLoopConfig) -> list[str]:
    """Return policy errors for a Phase 7 review configuration.

    Other audit-loop contexts intentionally retain their existing flexibility;
    only the ``review`` context is a Phase 7 hard gate.
    """

    if config.context != "review":
        return []

    errors: list[str] = []
    if (
        isinstance(config.min_rounds, bool)
        or not isinstance(config.min_rounds, int)
        or config.min_rounds < REVIEW_MIN_ROUNDS_FLOOR
    ):
        errors.append(f"review min_rounds must be at least {REVIEW_MIN_ROUNDS_FLOOR}")
    if (
        isinstance(config.max_rounds, bool)
        or not isinstance(config.max_rounds, int)
        or not isinstance(config.min_rounds, int)
        or config.max_rounds < config.min_rounds
        or config.max_rounds > REVIEW_MAX_ROUNDS_LIMIT
    ):
        errors.append(
            f"review max_rounds must be >= min_rounds and not exceed {REVIEW_MAX_ROUNDS_LIMIT}"
        )
    if (
        isinstance(config.quality_threshold, bool)
        or not isinstance(config.quality_threshold, (int, float))
        or not math.isfinite(float(config.quality_threshold))
        or float(config.quality_threshold) < REVIEW_QUALITY_THRESHOLD_FLOOR
        or float(config.quality_threshold) > 10.0
    ):
        errors.append(
            f"review quality_threshold must be at least {REVIEW_QUALITY_THRESHOLD_FLOOR:.1f}"
        )
    return errors
