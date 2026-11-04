"""Base constraints for formal non-journal outputs (proposals, reports, theses, ...)."""

from __future__ import annotations

from typing import Any

from .._models import ConstraintCategory
from .anti_ai import CORE_ANTI_AI_PATTERNS


def _structure_constraint(description: str, required_sections: list[str]) -> dict[str, Any]:
    return {
        "id": "R001",
        "category": ConstraintCategory.STRUCTURAL,
        "rule": "required_sections",
        "description": f"Required structure for {description}",
        "params": {"sections": required_sections},
        "severity": "CRITICAL",
        "provenance": "base",
    }


def _vocabulary_constraints() -> list[dict[str, Any]]:
    return [
        {
            "id": "V001",
            "category": ConstraintCategory.VOCABULARY,
            "rule": "language_consistency",
            "description": "Must use a consistent language variety throughout",
            "severity": "WARNING",
            "hook_ref": "A5",
            "provenance": "base",
        },
        {
            "id": "V002",
            "category": ConstraintCategory.VOCABULARY,
            "rule": "anti_ai_vocabulary",
            "description": "Forbidden AI-typical phrases that undermine authorial voice",
            "params": {"forbidden_patterns": list(CORE_ANTI_AI_PATTERNS)},
            "severity": "WARNING",
            "hook_ref": "A3",
            "provenance": "base",
        },
    ]


def _evidence_constraint() -> dict[str, Any]:
    return {
        "id": "E001",
        "category": ConstraintCategory.EVIDENTIAL,
        "rule": "claim_requires_citation",
        "description": "Externally verifiable factual claims must cite independent evidence",
        "params": {"min_citations_per_paragraph": 1},
        "severity": "WARNING",
        "hook_ref": "A2",
        "provenance": "base",
    }


def _boundary_constraints(description: str, min_words: int, max_words: int) -> list[dict[str, Any]]:
    return [
        {
            "id": "B001",
            "category": ConstraintCategory.BOUNDARY,
            "rule": "word_count_range",
            "description": f"Word-count boundary for {description}",
            "params": {"min_words": min_words, "max_words": max_words},
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
    ]


def _minimum_references_constraint(min_references: int) -> dict[str, Any]:
    return {
        "id": "B003",
        "category": ConstraintCategory.BOUNDARY,
        "rule": "minimum_references",
        "description": f"Minimum {min_references} independently verified references required",
        "params": {"min_references": min_references},
        "severity": "WARNING",
        "hook_ref": "Phase2Gate",
        "provenance": "base",
    }


def build_formal_output_constraints(
    *,
    paper_type: str,
    description: str,
    required_sections: list[str],
    min_words: int,
    max_words: int,
    min_references: int = 0,
) -> dict[str, Any]:
    """Build the shared production constraints for non-journal outputs."""
    constraints: list[dict[str, Any]] = [
        _structure_constraint(description, required_sections),
        *_vocabulary_constraints(),
        _evidence_constraint(),
        *_boundary_constraints(description, min_words, max_words),
    ]
    if min_references:
        constraints.append(_minimum_references_constraint(min_references))

    return {
        "meta": {
            "paper_type": paper_type,
            "version": "1.0.0",
            "description": description,
        },
        "constraints": constraints,
    }


# Insertion order is part of the BASE_CONSTRAINTS ordering contract.
FORMAL_OUTPUT_SPECS: list[dict[str, Any]] = [
    {
        "paper_type": "research-proposal",
        "description": "research proposals and protocols",
        "required_sections": [
            "Executive Summary",
            "Background and Rationale",
            "Objectives",
            "Methods",
            "Timeline",
            "Ethics and Data Management",
            "Budget and Resources",
            "Expected Impact",
        ],
        "min_words": 1500,
        "max_words": 12000,
        "min_references": 10,
    },
    {
        "paper_type": "project-closeout-report",
        "description": "auditable project closeout reports",
        "required_sections": [
            "Executive Summary",
            "Objectives",
            "Activities and Methods",
            "Results and Deliverables",
            "Deviations and Corrective Actions",
            "Budget and Resources",
            "Lessons Learned",
            "Data and Artifact Disposition",
            "Conclusion",
        ],
        "min_words": 1500,
        "max_words": 15000,
    },
    {
        "paper_type": "student-paper",
        "description": "assessed student papers and capstones",
        "required_sections": [
            "Abstract",
            "Introduction",
            "Literature Review",
            "Main Analysis",
            "Discussion",
            "Conclusion",
            "References",
        ],
        "min_words": 1000,
        "max_words": 10000,
        "min_references": 5,
    },
    {
        "paper_type": "conference-paper",
        "description": "conference and proceedings papers",
        "required_sections": [
            "Abstract",
            "Introduction",
            "Methods",
            "Results",
            "Discussion",
            "Conclusion",
        ],
        "min_words": 1500,
        "max_words": 8000,
        "min_references": 10,
    },
    {
        "paper_type": "thesis-dissertation",
        "description": "degree theses and dissertations",
        "required_sections": [
            "Abstract",
            "Introduction",
            "Literature Review",
            "Methods",
            "Results",
            "Discussion",
            "Conclusion",
        ],
        "min_words": 10000,
        "max_words": 100000,
        "min_references": 40,
    },
    {
        "paper_type": "arxiv-preprint",
        "description": "versioned arXiv or repository preprints",
        "required_sections": [
            "Abstract",
            "Introduction",
            "Methods",
            "Results",
            "Discussion",
            "Conclusion",
            "Data and Code Availability",
            "Version Notes",
        ],
        "min_words": 2000,
        "max_words": 15000,
        "min_references": 15,
    },
]


def build_formal_output_sets() -> dict[str, dict[str, Any]]:
    """Build the constraint sets for every formal output type, in declaration order."""
    return {
        spec["paper_type"]: build_formal_output_constraints(**spec) for spec in FORMAL_OUTPUT_SPECS
    }
