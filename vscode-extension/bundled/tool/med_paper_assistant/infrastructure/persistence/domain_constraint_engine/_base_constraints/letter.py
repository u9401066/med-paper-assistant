"""Base constraint data for letters to the editor."""

from __future__ import annotations

from typing import Any

from .._models import ConstraintCategory
from .anti_ai import CORE_ANTI_AI_PATTERNS

LETTER: dict[str, Any] = {
    "meta": {
        "paper_type": "letter",
        "version": "1.0.0",
        "description": "Constraints for letters to the editor and brief communications",
    },
    "constraints": [
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
            "id": "B001",
            "category": ConstraintCategory.BOUNDARY,
            "rule": "word_count_range",
            "description": "Letters are typically very short",
            "params": {"min_words": 200, "max_words": 800},
            "severity": "WARNING",
            "hook_ref": "A1",
            "provenance": "base",
        },
        {
            "id": "B003",
            "category": ConstraintCategory.BOUNDARY,
            "rule": "minimum_references",
            "description": "Minimum 5 references required for letters",
            "params": {"min_references": 5},
            "severity": "WARNING",
            "hook_ref": "Phase2Gate",
            "provenance": "base",
        },
    ],
}
