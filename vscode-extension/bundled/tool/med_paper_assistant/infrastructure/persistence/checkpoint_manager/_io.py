"""Checkpoint file persistence: construction, load/clear, empty state, atomic write."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from med_paper_assistant.infrastructure.persistence.state_io import (
    atomic_write_text,
    load_json_state,
)

from . import _models

logger = structlog.get_logger()


class CheckpointIOMixin:
    """Locate, load, clear, and atomically write ``checkpoint.json``."""

    CHECKPOINT_FILE = _models.CHECKPOINT_FILE

    def __init__(self, audit_dir: str | Path, project_dir: str | Path | None = None) -> None:
        self._audit_dir = Path(audit_dir)
        self._checkpoint_path = self._audit_dir / self.CHECKPOINT_FILE
        # project_dir is used for draft hash computation; inferred from audit_dir if not given
        if project_dir is not None:
            self._project_dir = Path(project_dir)
        else:
            # audit_dir is typically projects/{slug}/.audit
            self._project_dir = self._audit_dir.parent

    @property
    def checkpoint_path(self) -> Path:
        return self._checkpoint_path

    def exists(self) -> bool:
        """Check if a checkpoint file exists."""
        return self._checkpoint_path.is_file()

    def load(self) -> dict[str, Any] | None:
        """Load checkpoint state (None if missing; corrupt files are quarantined)."""
        data = load_json_state(self._checkpoint_path)
        if data is not None:
            logger.info(
                "Checkpoint loaded: Phase %d (%s)",
                data.get("last_completed_phase", -1),
                data.get("last_phase_name", "unknown"),
            )
        return data

    def clear(self) -> None:
        """Remove the checkpoint file (for full restart)."""
        if self._checkpoint_path.is_file():
            self._checkpoint_path.unlink()
            logger.info("Checkpoint cleared")

    def _empty_state(self) -> dict[str, Any]:
        """Create an empty checkpoint state."""
        return {
            "version": 2,
            "last_completed_phase": -1,
            "last_phase_name": "",
            "current_phase": -1,
            "current_phase_name": "",
            "current_section": "",
            "status": "not_started",
            "phase_outputs": {},
            "flagged_issues": [],
            "audit_stats": {},
            "section_progress": {},
            "history": [],
            "created_at": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat(),
        }

    def _write(self, state: dict[str, Any]) -> None:
        """Write state to disk."""
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._checkpoint_path, json.dumps(state, indent=2, ensure_ascii=False))
