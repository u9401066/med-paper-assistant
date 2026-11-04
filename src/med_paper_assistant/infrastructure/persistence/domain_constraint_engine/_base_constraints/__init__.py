"""Base constraint templates per paper type.

These are the 'knowledge boundaries' — analogous to Triad Engine's
JSON Domain Guide that defines what exists and what doesn't.
"""

from __future__ import annotations

from typing import Any

from .anti_ai import CORE_ANTI_AI_PATTERNS
from .case_report import CASE_REPORT
from .formal_outputs import build_formal_output_sets
from .letter import LETTER
from .meta_analysis import META_ANALYSIS
from .original_research import ORIGINAL_RESEARCH
from .other import OTHER
from .review_article import REVIEW_ARTICLE
from .systematic_review import SYSTEMATIC_REVIEW

__all__ = ["BASE_CONSTRAINTS", "CORE_ANTI_AI_PATTERNS", "build_base_constraints"]


def build_base_constraints() -> dict[str, dict[str, Any]]:
    """
    Build base constraint templates per paper type.

    These are the 'knowledge boundaries' — analogous to Triad Engine's
    JSON Domain Guide that defines what exists and what doesn't.

    Returns:
        Dict mapping paper_type → constraint_set
    """
    return {
        "original-research": ORIGINAL_RESEARCH,
        "case-report": CASE_REPORT,
        "systematic-review": SYSTEMATIC_REVIEW,
        "meta-analysis": META_ANALYSIS,
        "review-article": REVIEW_ARTICLE,
        "letter": LETTER,
        **build_formal_output_sets(),
        "other": OTHER,
    }


# Pre-build at module load
BASE_CONSTRAINTS = build_base_constraints()
