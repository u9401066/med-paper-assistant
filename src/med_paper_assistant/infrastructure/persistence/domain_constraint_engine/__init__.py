"""
Domain Constraint Engine — Structured JSON constraint system for paper writing.

Inspired by Triad Engine's JSON Domain Guide approach:
  Instead of relying solely on natural language instructions (SKILL.md),
  we enforce paper-type-specific constraints via structured JSON files.
  These constraints are **evolvable** — the MetaLearningEngine can add
  new constraints when hooks detect recurring error patterns.

Architecture:
  Infrastructure layer service. Works alongside WritingHooksEngine.
  - Constraints are stored as JSON files in `.constraints/` per project
  - Base constraints come from paper_types.py + built-in templates
  - Project-specific learned constraints are appended via evolve()
  - Each constraint has a provenance trail (source, timestamp, reason)

Triad Engine Mapping:
  - JSON Domain Guide → DomainConstraint files (per paper type)
  - Multi-Agent Deliberation → Hook layers A/B/C/E/F (already exist)
  - Sand Spreader → validate_against_constraints() (epistemic boundary check)

CONSTITUTION §22 Compliance:
  - Auditable: every constraint has provenance (who added it, why)
  - Decomposable: constraints are independent, testable units
  - Recomposable: JSON merge across base + project-learned

CONSTITUTION §23 Boundaries:
  - L1 (auto): Add learned constraints from hook patterns
  - L2 (auto): Adjust constraint severity within bounds
  - FORBIDDEN: Remove base constraints, weaken safety constraints

Package layout:
  _models.py            ConstraintCategory, ConstraintViolation
  _base_constraints/    pure-data base constraints, one module per paper-type family
  _validation.py        rule checkers behind validate_against_constraints()
  _learned_store.py     learned-constraint + evolution-log persistence
  engine.py             DomainConstraintEngine
"""

from __future__ import annotations

from ._base_constraints import BASE_CONSTRAINTS
from ._base_constraints import CORE_ANTI_AI_PATTERNS as _CORE_ANTI_AI_PATTERNS
from ._models import ConstraintCategory, ConstraintViolation
from .engine import DomainConstraintEngine

__all__ = [
    "BASE_CONSTRAINTS",
    "ConstraintCategory",
    "ConstraintViolation",
    "DomainConstraintEngine",
    "_CORE_ANTI_AI_PATTERNS",
]
