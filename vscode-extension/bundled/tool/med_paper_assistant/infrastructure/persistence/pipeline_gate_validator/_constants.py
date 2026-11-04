"""Shared constants for the pipeline gate validator."""

from __future__ import annotations

import re

_GIT_GATE_TIMEOUT_SECONDS = 3
_PIPELINE_PHASES = [0, 1, 2, 21, 3, 4, 5, 6, 65, 7, 8, 9, 10, 11]
_PIPELINE_PHASE_NAMES = {
    0: "Configuration",
    1: "Setup",
    2: "Literature",
    21: "Fulltext Ingestion",
    3: "Concept",
    4: "Planning",
    5: "Writing",
    6: "Audit",
    65: "Evolution Gate",
    7: "Autonomous Review",
    8: "Reference Sync",
    9: "Export",
    10: "Retrospective",
    11: "Final Delivery",
}
_PIPELINE_PHASE_RANK = {phase: index for index, phase in enumerate(_PIPELINE_PHASES)}
_META_LEARNING_STEPS = tuple(f"D{i}" for i in range(1, 10))
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_MIN_REFERENCE_ARTIFACT_BYTES = 16
REFERENCE_ANALYSIS_TEXT_MINIMUMS = {
    "summary": 20,
    "methodology": 8,
    "key_findings": 8,
    "limitations": 8,
}
