"""Score validation for the autonomous audit loop."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any


def validate_round_scores(scores: Mapping[str, Any], dimensions: Iterable[str]) -> None:
    """Require exactly the configured dimensions, each a finite number in [0, 10].

    Raises ``ValueError`` so callers can reject a round before mutating state;
    partial score sets would otherwise be renormalized and inflate the average.
    """
    expected = set(dimensions)
    if not isinstance(scores, Mapping) or set(scores) != expected:
        raise ValueError(
            f"scores must exactly match configured dimensions: {sorted(expected)} "
            f"(got {sorted(scores) if isinstance(scores, Mapping) else type(scores).__name__})"
        )
    for dimension, score in scores.items():
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(float(score))
            or not 0 <= float(score) <= 10
        ):
            raise ValueError(f"score {dimension!r} must be a finite number between 0 and 10")
