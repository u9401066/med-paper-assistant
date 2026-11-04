"""Disk persistence (save / load / reset) for the audit-loop state machine."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

from ..state_io import atomic_write_text, load_json_state
from ._base import LoopState
from ._models import RoundRecord


class PersistenceMixin(LoopState):
    """Checkpoint persistence to ``.audit/audit-loop-{context}.json``."""

    # ── Persistence ────────────────────────────────────────────────

    def save(self) -> None:
        """Save loop state to disk."""
        data = {
            "version": 1,
            "config": asdict(self._config),
            "current_round": self._current_round,
            "completed": self._completed,
            "in_round": self._in_round,
            "artifact_hash_start": getattr(self, "_artifact_hash_start", ""),
            "round_start_time": self._round_start_time,
            "rounds": [asdict(r) for r in self._rounds],
            "rewrite_sections": self._rewrite_sections,
            "rewrite_reason": self._rewrite_reason,
            "saved_at": datetime.now().astimezone().isoformat(),
        }
        atomic_write_text(self._data_path, json.dumps(data, indent=2, ensure_ascii=False))

    def load(self) -> bool:
        """Load loop state from disk. Returns True if state was loaded."""
        data = load_json_state(self._data_path)
        if data is None:
            return False
        self._current_round = data.get("current_round", 0)
        self._completed = data.get("completed", False)
        self._in_round = data.get("in_round", False)
        self._artifact_hash_start = data.get("artifact_hash_start", "")
        self._round_start_time = data.get("round_start_time", "")
        self._rewrite_sections = data.get("rewrite_sections", [])
        self._rewrite_reason = data.get("rewrite_reason", "")

        self._rounds = []
        for r in data.get("rounds", []):
            self._rounds.append(
                RoundRecord(
                    round_number=r["round_number"],
                    issues=r.get("issues", []),
                    fixes=r.get("fixes", []),
                    scores=r.get("scores", {}),
                    weighted_avg=r.get("weighted_avg", 0.0),
                    verdict=r.get("verdict", ""),
                    started_at=r.get("started_at", ""),
                    completed_at=r.get("completed_at", ""),
                    artifact_hash_start=r.get("artifact_hash_start", ""),
                    artifact_hash_end=r.get("artifact_hash_end", ""),
                )
            )
        return True

    def reset(self) -> None:
        """Reset the loop state (start over)."""
        self._rounds = []
        self._current_issues = []
        self._current_fixes = []
        self._current_round = 0
        self._in_round = False
        self._completed = False
        self._rewrite_sections = []
        self._rewrite_reason = ""
        if self._data_path.is_file():
            self._data_path.unlink()
