"""Constraint value objects: categories and violations."""

from __future__ import annotations

from typing import Any

# ── Constraint Categories ─────────────────────────────────────────


class ConstraintCategory:
    """Constants for constraint categories."""

    STATISTICAL = "statistical"  # What tests/methods are valid
    STRUCTURAL = "structural"  # Required sections, ordering
    VOCABULARY = "vocabulary"  # Allowed/forbidden terms
    EVIDENTIAL = "evidential"  # What claims need what evidence level
    TEMPORAL = "temporal"  # Tense rules per section
    REPORTING = "reporting"  # EQUATOR guideline requirements
    BOUNDARY = "boundary"  # Hard limits (word count, figures, etc.)


class ConstraintViolation:
    """A single constraint violation found during validation."""

    def __init__(
        self,
        constraint_id: str,
        rule: str,
        category: str,
        severity: str,
        message: str,
        section: str = "",
        suggestion: str = "",
    ) -> None:
        self.constraint_id = constraint_id
        self.rule = rule
        self.category = category
        self.severity = severity
        self.message = message
        self.section = section
        self.suggestion = suggestion

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "rule": self.rule,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "section": self.section,
            "suggestion": self.suggestion,
        }
