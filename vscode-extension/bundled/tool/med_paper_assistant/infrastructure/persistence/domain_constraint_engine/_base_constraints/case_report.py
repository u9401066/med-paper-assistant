"""Base constraint data for case reports."""

from __future__ import annotations

from typing import Any

from .._models import ConstraintCategory
from .anti_ai import CORE_ANTI_AI_PATTERNS

CASE_REPORT: dict[str, Any] = {
    "meta": {
        "paper_type": "case-report",
        "version": "1.1.0",
        "description": "Constraints for case reports and case series",
    },
    "constraints": [
        {
            "id": "R001",
            "category": ConstraintCategory.STRUCTURAL,
            "rule": "required_sections",
            "description": "Must have Introduction, Case Presentation, Discussion, Conclusion",
            "params": {
                "sections": [
                    "Introduction",
                    "Case Presentation",
                    "Discussion",
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
            "description": "Must use consistent British or American English",
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
            "rule": "patient_consent_mentioned",
            "description": "Case report should mention patient consent/IRB waiver",
            "severity": "CRITICAL",
            "provenance": "base",
        },
        {
            "id": "T001",
            "category": ConstraintCategory.TEMPORAL,
            "rule": "case_presentation_past_tense",
            "description": "Case Presentation section should primarily use past tense",
            "severity": "INFO",
            "provenance": "base",
        },
        {
            "id": "B001",
            "category": ConstraintCategory.BOUNDARY,
            "rule": "word_count_range",
            "description": "Case reports are typically shorter",
            "params": {"min_words": 800, "max_words": 2500},
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
            "description": "Minimum 8 references required for case reports",
            "params": {"min_references": 8},
            "severity": "CRITICAL",
            "hook_ref": "Phase2Gate",
            "provenance": "base",
        },
        {
            "id": "P001",
            "category": ConstraintCategory.REPORTING,
            "rule": "equator_guideline_required",
            "description": "CARE checklist required for case reports",
            "params": {"guidelines": ["CARE"]},
            "severity": "CRITICAL",
            "hook_ref": "E1",
            "provenance": "base",
        },
    ],
}
