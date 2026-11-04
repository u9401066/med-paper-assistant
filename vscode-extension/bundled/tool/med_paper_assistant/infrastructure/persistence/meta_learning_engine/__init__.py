"""
Meta-Learning Engine — Hook D implementation for self-improvement.

Analyzes hook effectiveness and quality scorecard data to produce:
  - D1: Performance statistics analysis
  - D3: Automatic threshold adjustments (within ±20% bounds)
  - D4-D5: SKILL.md / AGENTS.md improvement suggestions
  - D6: Audit trail generation

Architecture:
  Infrastructure layer service. Called during Phase 10 of auto-paper pipeline.
  Reads from HookEffectivenessTracker and QualityScorecard.
  Writes to .audit/ and the auto-paper skill's references/lessons-learned.md.

CONSTITUTION §23 Boundaries:
  - L1 (auto): Update the skill's Lessons Learned reference
  - L2 (auto): Adjust thresholds ±20%
  - L3 (logged): Factual instruction changes → decisionLog
  - FORBIDDEN: Modify CONSTITUTION, 🔒 rules, save_reference_mcp priority, Hook D itself
"""

from ._models import MAX_THRESHOLD_ADJUSTMENT, LessonLearned, ThresholdAdjustment
from .engine import MetaLearningEngine

__all__ = [
    "MAX_THRESHOLD_ADJUSTMENT",
    "LessonLearned",
    "MetaLearningEngine",
    "ThresholdAdjustment",
]
