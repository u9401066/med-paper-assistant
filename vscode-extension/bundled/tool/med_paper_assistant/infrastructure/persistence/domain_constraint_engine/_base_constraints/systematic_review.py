"""Base constraint data for systematic reviews."""

from __future__ import annotations

from typing import Any

from .._models import ConstraintCategory
from .anti_ai import CORE_ANTI_AI_PATTERNS

SYSTEMATIC_REVIEW: dict[str, Any] = {
    "meta": {
        "paper_type": "systematic-review",
        "version": "1.1.0",
        "description": "Constraints for systematic reviews",
    },
    "constraints": [
        {
            "id": "R001",
            "category": ConstraintCategory.STRUCTURAL,
            "rule": "required_sections",
            "description": "Must have Introduction, Methods, Results, Discussion, Conclusion",
            "params": {
                "sections": [
                    "Introduction",
                    "Methods",
                    "Results",
                    "Discussion",
                    "Conclusion",
                ]
            },
            "severity": "CRITICAL",
            "provenance": "base",
        },
        {
            "id": "R002",
            "category": ConstraintCategory.STRUCTURAL,
            "rule": "methods_before_results",
            "description": "Methods section must appear before Results",
            "severity": "CRITICAL",
            "hook_ref": "B6",
            "provenance": "base",
        },
        {
            "id": "S001",
            "category": ConstraintCategory.STRUCTURAL,
            "rule": "prisma_flow_required",
            "description": "PRISMA flow diagram must be included",
            "severity": "CRITICAL",
            "provenance": "base",
        },
        {
            "id": "S002",
            "category": ConstraintCategory.STRUCTURAL,
            "rule": "search_strategy_documented",
            "description": "Full search strategy with databases and terms must be in Methods",
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
            "description": "Factual claims in Introduction/Discussion must have citations",
            "params": {"min_citations_per_paragraph": 1},
            "severity": "WARNING",
            "hook_ref": "A2",
            "provenance": "base",
        },
        {
            "id": "T001",
            "category": ConstraintCategory.TEMPORAL,
            "rule": "methods_past_tense",
            "description": "Methods section should primarily use past tense",
            "severity": "INFO",
            "provenance": "base",
        },
        {
            "id": "T002",
            "category": ConstraintCategory.TEMPORAL,
            "rule": "results_past_tense",
            "description": "Results section should primarily use past tense",
            "severity": "INFO",
            "provenance": "base",
        },
        {
            "id": "B001",
            "category": ConstraintCategory.BOUNDARY,
            "rule": "word_count_range",
            "description": "Total word count should be within typical range for systematic reviews",
            "params": {"min_words": 3000, "max_words": 8000},
            "severity": "WARNING",
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
            "description": "Minimum 40 references required for systematic reviews",
            "params": {"min_references": 40},
            "severity": "CRITICAL",
            "hook_ref": "Phase2Gate",
            "provenance": "base",
        },
        {
            "id": "P001",
            "category": ConstraintCategory.REPORTING,
            "rule": "equator_guideline_required",
            "description": "PRISMA guideline required for systematic reviews",
            "params": {"guidelines": ["PRISMA"]},
            "severity": "CRITICAL",
            "hook_ref": "E1",
            "provenance": "base",
        },
    ],
}
