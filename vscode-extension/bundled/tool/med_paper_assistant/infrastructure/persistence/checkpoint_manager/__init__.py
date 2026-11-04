"""
Pipeline Checkpoint Manager — Save/restore auto-paper pipeline state.

Implements the checkpoint.json spec from auto-paper SKILL.md.
Enables interrupted pipelines to resume from the last completed phase.
Supports phase regression, pause/resume with edit detection, and
per-section user approval tracking.

Architecture:
  Infrastructure layer service. Called by auto-paper pipeline at phase transitions.
  Stores to: projects/{slug}/.audit/checkpoint.json

Design rationale (CONSTITUTION §22):
  - Auditable: every phase transition is recorded
  - Recomposable: resume from any phase
"""

from __future__ import annotations

from ._manager import CheckpointManager

__all__ = ["CheckpointManager"]
