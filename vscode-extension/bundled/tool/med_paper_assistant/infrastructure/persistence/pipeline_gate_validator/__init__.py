"""
Pipeline Gate Validator — Hard enforcement of phase completion criteria.

Unlike SKILL.md instructions (soft constraints the LLM can ignore),
this module enforces artifact existence via code-level checks.
Each phase transition MUST pass validation before proceeding.

Architecture:
  Infrastructure layer service. Exposed as MCP tool `validate_phase_gate`.
  Agent cannot bypass — the tool returns FAIL with specific missing artifacts.

Design rationale:
  - SKILL.md = "what to do" (soft, agent may skip)
  - This module = "did you actually do it?" (hard, code-enforced)
  - Prevents premature phase transitions
  - Prevents declaring "done" without required artifacts

Usage:
    validator = PipelineGateValidator(project_dir)
    result = validator.validate_phase(7)
    # result.passed == False → cannot proceed
    # result.missing == ["review-report-1.md", "author-response-1.md", ...]
"""

from __future__ import annotations

from ._constants import (
    _PIPELINE_PHASE_NAMES,
    _PIPELINE_PHASES,
    REFERENCE_ANALYSIS_TEXT_MINIMUMS,
)
from ._core import PipelineGateValidator
from ._reference_evidence import derive_reference_source_revision
from ._types import GateCheck, GateResult

__all__ = [
    "REFERENCE_ANALYSIS_TEXT_MINIMUMS",
    "_PIPELINE_PHASES",
    "_PIPELINE_PHASE_NAMES",
    "GateCheck",
    "GateResult",
    "PipelineGateValidator",
    "derive_reference_source_revision",
]
