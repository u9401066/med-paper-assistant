"""Base constraint data for narrative review articles."""

from __future__ import annotations

from typing import Any

from .._models import ConstraintCategory
from .anti_ai import CORE_ANTI_AI_PATTERNS

REVIEW_ARTICLE: dict[str, Any] = {
    "meta": {
        "paper_type": "review-article",
        "version": "1.0.0",
        "description": "Constraints for narrative reviews and invited reviews",
    },
    "constraints": [
        {
            "id": "R001",
            "category": ConstraintCategory.STRUCTURAL,
            "rule": "required_sections",
            "description": "Must have Introduction and Conclusion",
            "params": {
                "sections": [
                    "Introduction",
                    "Conclusion",
                ]
            },
            "severity": "CRITICAL",
            "provenance": "base",
        },
        {
            "id": "V001",
            "category": ConstraintCategory.VOCABULARY,
            "rule": "language_consistency",
            "description": "Must use consistent British or American English throughout",
            "severity": "WARNING",
            "hook_ref": "A5",
            "provenance": "base",
        },
        {
            "id": "V002",
            "category": ConstraintCategory.VOCABULARY,
            "rule": "anti_ai_vocabulary",
            "description": "Forbidden AI-typical phrases that trigger reviewer suspicion",
            "params": {
                "forbidden_patterns": list(CORE_ANTI_AI_PATTERNS),
            },
            "severity": "WARNING",
            "hook_ref": "A3",
            "provenance": "base",
        },
        {
            "id": "E001",
            "category": ConstraintCategory.EVIDENTIAL,
            "rule": "claim_requires_citation",
            "description": "Factual claims must have citations",
            "params": {"min_citations_per_paragraph": 1},
            "severity": "WARNING",
            "hook_ref": "A2",
            "provenance": "base",
        },
        {
            "id": "B001",
            "category": ConstraintCategory.BOUNDARY,
            "rule": "word_count_range",
            "description": "Total word count should be within typical range for review articles",
            "params": {"min_words": 3000, "max_words": 6000},
            "severity": "WARNING",
            "hook_ref": "A1",
            "provenance": "base",
        },
        {
            "id": "B002",
            "category": ConstraintCategory.BOUNDARY,
            "rule": "no_overlap_between_sections",
            "description": "Paragraphs should not be duplicated across sections",
            "severity": "WARNING",
            "hook_ref": "A6",
            "provenance": "base",
        },
        {
            "id": "B003",
            "category": ConstraintCategory.BOUNDARY,
            "rule": "minimum_references",
            "description": "Minimum 30 references required for review articles",
            "params": {"min_references": 30},
            "severity": "CRITICAL",
            "hook_ref": "Phase2Gate",
            "provenance": "base",
        },
    ],
}
