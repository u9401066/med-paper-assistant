"""Persistence of learned constraints and the evolution audit trail."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

VALID_SEVERITIES = ("INFO", "WARNING", "CRITICAL")


def validate_evolve_inputs(severity: str, constraint_id: str) -> None:
    """Reject invalid severities or constraint ids before anything is written."""
    if severity not in VALID_SEVERITIES:
        raise ValueError(
            f"Invalid severity '{severity}'. Must be one of: {', '.join(VALID_SEVERITIES)}"
        )
    if not re.match(r"^[A-Z]\d{3}$", constraint_id):
        raise ValueError(
            f"Invalid constraint_id '{constraint_id}'. Must match pattern [A-Z]NNN (e.g., L001)"
        )


def build_learned_constraint(
    constraint_id: str,
    rule: str,
    category: str,
    description: str,
    severity: str,
    params: dict[str, Any] | None,
    reason: str,
    source_hook: str,
) -> dict[str, Any]:
    """Create the constraint record stored for a learned constraint."""
    new_constraint: dict[str, Any] = {
        "id": constraint_id,
        "category": category,
        "rule": rule,
        "description": description,
        "severity": severity,
        "provenance": "learned",
        "source_hook": source_hook,
        "reason": reason,
        "learned_at": datetime.now().isoformat(),
    }
    if params:
        new_constraint["params"] = params
    return new_constraint


class LearnedConstraintStoreMixin:
    """Reads and writes `.constraints/` JSON files for DomainConstraintEngine."""

    _paper_type: str
    _constraints_dir: Path
    _learned_path: Path
    _evolution_log_path: Path

    def _load_learned_constraints(self) -> list[dict[str, Any]]:
        """Load project-specific learned constraints from disk."""
        if not self._learned_path.is_file():
            return []
        try:
            data = json.loads(self._learned_path.read_text(encoding="utf-8"))
            return data.get("constraints", [])
        except (json.JSONDecodeError, OSError):
            logger.warning("constraint_load_failed", path=str(self._learned_path))
            return []

    def _add_learned_constraint(self, new_constraint: dict[str, Any]) -> bool:
        """Persist a learned constraint and log it; False if its ID already exists."""
        current = self._load_learned_constraints()
        # Don't duplicate
        existing_ids = {c["id"] for c in current}
        if new_constraint["id"] in existing_ids:
            logger.info("constraint_already_exists", id=new_constraint["id"])
            return False

        current.append(new_constraint)
        self._save_learned_constraints(current)

        # Append to evolution log
        self._append_evolution_log(new_constraint)
        return True

    def _save_learned_constraints(self, constraints: list[dict[str, Any]]) -> None:
        """Persist learned constraints to disk."""
        self._constraints_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "paper_type": self._paper_type,
            "updated_at": datetime.now().isoformat(),
            "constraints": constraints,
        }
        self._learned_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _append_evolution_log(self, constraint: dict[str, Any]) -> None:
        """Append to evolution audit trail."""
        log: list[dict[str, Any]] = []
        if self._evolution_log_path.is_file():
            try:
                log = json.loads(self._evolution_log_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        log.append(
            {
                "action": "add",
                "constraint": constraint,
                "timestamp": datetime.now().isoformat(),
            }
        )

        self._evolution_log_path.write_text(
            json.dumps(log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _count_evolution_events(self) -> int:
        """Number of entries in the evolution log (0 when missing or unreadable)."""
        if self._evolution_log_path.is_file():
            try:
                return len(json.loads(self._evolution_log_path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        return 0

    def get_evolution_history(self) -> list[dict[str, Any]]:
        """
        Get the full constraint evolution log.

        Returns:
            List of evolution events (constraint additions/modifications).
        """
        if not self._evolution_log_path.is_file():
            return []
        try:
            return json.loads(self._evolution_log_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
