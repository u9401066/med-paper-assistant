"""Constants for the pipeline checkpoint manager."""

from __future__ import annotations

CHECKPOINT_FILE = "checkpoint.json"

# Maximum auto-resumable regressions before a human checkpoint is required.
# Mirrors the request_section_rewrite enforcement (max 2 regressions).
MAX_AUTONOMOUS_REGRESSIONS = 2

# Maximum consecutive unattended auto-resumes before a periodic human
# checkpoint is required (bounded-autonomy safeguard for the YOLO flow).
MAX_CONSECUTIVE_AUTO_RESUMES = 3
