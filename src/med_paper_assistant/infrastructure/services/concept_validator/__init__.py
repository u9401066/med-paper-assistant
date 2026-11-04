"""
Concept Validator - Service for validating research concept files.

This module provides comprehensive validation of concept.md files including:
1. Structural validation - Required sections present and non-empty
2. Novelty evaluation - LLM-based scoring (3 rounds, 75+ threshold)
3. Selling points quality check
4. Consistency validation - Alignment between sections
5. Citation support check

Key Design Decisions:
- Validation requirements vary by PAPER TYPE
- Section-specific validation: only check what's needed for that section
- Methods sections are RECOMMENDED, not REQUIRED (non-blocking)
- Results are cached to avoid redundant API calls

Requirements are read from ``domain.paper_types``. Novelty evaluation only
runs for profiles that require a novelty statement; proposals, closeout
reports, student papers, and theses use their own auditable concept contract.

Section-Specific Validation:
- Introduction: core + intro_required
- Methods: core + intro + methods_required (RECOMMENDED, non-blocking)
- Results: Methods done + data ready
- Discussion: core + Results done
"""

from ._models import SectionCheck, ValidationResult
from .engine import ConceptValidator

__all__ = ["ConceptValidator", "SectionCheck", "ValidationResult"]
