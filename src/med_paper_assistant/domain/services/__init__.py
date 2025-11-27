"""
Domain Services

Domain services encapsulate business logic that doesn't naturally fit
within a single entity or value object.
"""

from .citation_formatter import CitationFormatter
from .novelty_scorer import (
    NoveltyDimension,
    NoveltyScore,
    NoveltyEvaluation,
    NoveltyVerdict,
    DEFAULT_SCORING_CONFIG,
    NOVELTY_SCORING_PROMPT,
    SELLING_POINTS_SCORING_PROMPT,
    CONSISTENCY_CHECK_PROMPT,
    CITATION_SUPPORT_PROMPT,
)

__all__ = [
    "CitationFormatter",
    "NoveltyDimension",
    "NoveltyScore",
    "NoveltyEvaluation",
    "NoveltyVerdict",
    "DEFAULT_SCORING_CONFIG",
    "NOVELTY_SCORING_PROMPT",
    "SELLING_POINTS_SCORING_PROMPT",
    "CONSISTENCY_CHECK_PROMPT",
    "CITATION_SUPPORT_PROMPT",
]
