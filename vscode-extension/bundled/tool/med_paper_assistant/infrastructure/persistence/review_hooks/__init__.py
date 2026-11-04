"""
Review Hooks Engine — Code-enforced quality checks for Phase 7 Autonomous Review.

R-series hooks verify that the review CONTENT is substantive, not just that
the review PROCESS was followed. Integrated into submit_review_round() as a
HARD GATE — the agent cannot submit a review round unless these pass.

Hooks:
  R1  Review Report Depth — report word count, reviewer perspectives, severity breakdown
  R2  Author Response Completeness — every issue addressed, DECLINE ratio ≤ 50%
  R3  EQUATOR Compliance Gate — equator file exists, checklist items ≥ 5
  R4  Review-Fix Traceability — ACCEPT'd issues have corresponding manuscript patches
  R5  Post-Review Anti-AI Gate — re-run A3/A3b after review edits, must PASS
  R6  Citation Budget Gate — total refs ≤ journal limit after review adds new ones;
                              if over, force prioritisation via citation_decisions.json

Architecture:
  - Standalone engine (not a WritingHooksEngine mixin)
  - Returns HookResult/HookIssue from writing_hooks._models
  - Records to HookEffectivenessTracker via the same "R1"…"R6" IDs
  - Called from submit_review_round() in interfaces/mcp/tools/review/pipeline_gate/
  - One module per hook (``_r1_*`` … ``_r6_*``) composed by ``engine.ReviewHooksEngine``
"""

from __future__ import annotations

from ._constants import (
    MAX_DECLINE_RATIO,
    MIN_EQUATOR_ITEMS,
    MIN_PERSPECTIVES,
    MIN_REVIEW_REPORT_WORDS,
    REF_BUDGET_HEADROOM,
    REVIEWER_PERSPECTIVES,
    SEVERITY_KEYWORDS,
)
from .engine import ReviewHooksEngine

__all__ = [
    "MAX_DECLINE_RATIO",
    "MIN_EQUATOR_ITEMS",
    "MIN_PERSPECTIVES",
    "MIN_REVIEW_REPORT_WORDS",
    "REF_BUDGET_HEADROOM",
    "REVIEWER_PERSPECTIVES",
    "SEVERITY_KEYWORDS",
    "ReviewHooksEngine",
]
