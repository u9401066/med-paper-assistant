"""
ConstraintLedger — Monotonic constraint accounting for manuscript convergence.

Human paper-writing converges by *accumulating* constraints: every problem a
reviewer (or hook) raises must eventually be either satisfied or explicitly
waived with a reason — it cannot silently disappear. This ledger encodes that
ratchet so the harness can answer one decidable question:

    "Is the manuscript converged?"  ==  "Are there zero OPEN constraints?"

Design (mirrors PendingEvolutionStore / CheckpointManager conventions):
    Infrastructure layer service. Per-project. Persists to
    projects/{slug}/.audit/constraint-ledger.yaml

Monotonicity guarantee (the ratchet):
    - A constraint can be ADDED (status=open).
    - A constraint can move open -> satisfied (the problem was fixed) or
      open -> waived (explicitly accepted, reason REQUIRED).
    - A constraint can be re-opened (satisfied/waived -> open) ONLY with a
      recorded reason (e.g. a later edit regressed it). This is the single
      escape hatch and it is auditable.
    - Adding the same logical constraint twice (same key) does NOT duplicate;
      it is idempotent. This prevents the ledger from being gamed by churn.

CONSTITUTION §22 (auditable) + §25-26 (stepwise convergence) compliance:
    Every transition is timestamped and carries an actor + reason. The ledger
    is the manuscript's externalized, never-forgetting working memory — the
    thing the (forgetful) agent cannot hold in context.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()

# Allowed constraint lifecycle states.
STATUS_OPEN = "open"
STATUS_SATISFIED = "satisfied"
STATUS_WAIVED = "waived"
_VALID_STATUSES = {STATUS_OPEN, STATUS_SATISFIED, STATUS_WAIVED}

# Severity ranking for reporting / gating decisions.
SEVERITY_ORDER = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _derive_key(source: str, description: str, section: str) -> str:
    """Stable idempotency key so the same logical issue is not duplicated."""
    raw = f"{source}\u241f{section}\u241f{description}".lower().strip()
    digest = hashlib.sha1(raw.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    return f"c_{digest}"


@dataclass
class Constraint:
    """A single accumulated requirement the manuscript must resolve."""

    key: str
    source: str  # who raised it (e.g. "P7", "reviewer-round-2", "B13")
    description: str
    severity: str = "WARNING"  # CRITICAL | WARNING | INFO
    section: str = ""
    status: str = STATUS_OPEN
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    resolution_reason: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "source": self.source,
            "description": self.description,
            "severity": self.severity,
            "section": self.section,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolution_reason": self.resolution_reason,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Constraint:
        return cls(
            key=data["key"],
            source=data.get("source", ""),
            description=data.get("description", ""),
            severity=data.get("severity", "WARNING"),
            section=data.get("section", ""),
            status=data.get("status", STATUS_OPEN),
            created_at=data.get("created_at", _now()),
            updated_at=data.get("updated_at", _now()),
            resolution_reason=data.get("resolution_reason", ""),
            history=list(data.get("history", [])),
        )


class ConstraintLedger:
    """Per-project monotonic ledger of manuscript constraints.

    Usage:
        ledger = ConstraintLedger(project_dir / ".audit")
        ledger.add("P7", "Malformed DOI on smith2024", severity="CRITICAL")
        ledger.satisfy(key, reason="fixed DOI to 10.1001/...")
        if ledger.is_converged():  # zero open constraints
            ...
    """

    LEDGER_FILE = "constraint-ledger.yaml"

    def __init__(self, audit_dir: str | Path) -> None:
        self._audit_dir = Path(audit_dir)
        self._path = self._audit_dir / self.LEDGER_FILE
        self._constraints: dict[str, Constraint] = {}
        self._loaded = False

    # ── persistence ────────────────────────────────────────────────
    def _load(self) -> None:
        if self._loaded:
            return
        if self._path.is_file():
            try:
                data = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
                for entry in data.get("constraints", []):
                    c = Constraint.from_dict(entry)
                    self._constraints[c.key] = c
            except (yaml.YAMLError, OSError, KeyError) as exc:
                logger.warning("Failed to load constraint ledger: %s", exc)
        self._loaded = True

    def _save(self) -> None:
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": _now(),
            "constraints": [c.to_dict() for c in self._constraints.values()],
        }
        self._path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    # ── mutations (the ratchet) ────────────────────────────────────
    def add(
        self,
        source: str,
        description: str,
        *,
        severity: str = "WARNING",
        section: str = "",
    ) -> Constraint:
        """Add a constraint. Idempotent on (source, description, section).

        If the same logical constraint already exists and was previously
        satisfied/waived, re-opening requires going through ``reopen`` — a
        plain ``add`` of an existing key is a no-op that returns the existing
        record (so re-running a hook does not silently reset resolutions).
        """
        self._load()
        key = _derive_key(source, description, section)
        existing = self._constraints.get(key)
        if existing is not None:
            return existing

        constraint = Constraint(
            key=key,
            source=source,
            description=description,
            severity=severity,
            section=section,
        )
        constraint.history.append({"at": constraint.created_at, "action": "opened"})
        self._constraints[key] = constraint
        self._save()
        logger.info("Constraint added", key=key, source=source, severity=severity)
        return constraint

    def _transition(self, key: str, new_status: str, reason: str, actor: str) -> bool:
        self._load()
        if new_status not in _VALID_STATUSES:
            raise ValueError(f"invalid status: {new_status}")
        constraint = self._constraints.get(key)
        if constraint is None:
            return False
        if new_status == STATUS_WAIVED and not reason.strip():
            raise ValueError("waiving a constraint requires a reason")
        prev = constraint.status
        constraint.status = new_status
        constraint.resolution_reason = reason
        constraint.updated_at = _now()
        constraint.history.append(
            {
                "at": constraint.updated_at,
                "action": f"{prev}->{new_status}",
                "reason": reason,
                "actor": actor,
            }
        )
        self._save()
        logger.info("Constraint transition", key=key, frm=prev, to=new_status)
        return True

    def satisfy(self, key: str, reason: str = "", actor: str = "agent") -> bool:
        """Mark a constraint satisfied (the underlying problem was fixed)."""
        return self._transition(key, STATUS_SATISFIED, reason, actor)

    def waive(self, key: str, reason: str, actor: str = "human") -> bool:
        """Explicitly accept a constraint without fixing it. Reason REQUIRED."""
        return self._transition(key, STATUS_WAIVED, reason, actor)

    def reopen(self, key: str, reason: str, actor: str = "agent") -> bool:
        """Re-open a resolved constraint (e.g. a later edit regressed it).

        This is the single auditable escape hatch from the ratchet; a reason
        is required so re-opening cannot be used to silently churn state.
        """
        if not reason.strip():
            raise ValueError("reopening a constraint requires a reason")
        return self._transition(key, STATUS_OPEN, reason, actor)

    # ── queries ────────────────────────────────────────────────────
    def get(self, key: str) -> Constraint | None:
        self._load()
        return self._constraints.get(key)

    def all_constraints(self) -> list[Constraint]:
        self._load()
        return list(self._constraints.values())

    def open_constraints(self) -> list[Constraint]:
        return [c for c in self.all_constraints() if c.status == STATUS_OPEN]

    def open_critical(self) -> list[Constraint]:
        return [c for c in self.open_constraints() if c.severity == "CRITICAL"]

    def is_converged(self) -> bool:
        """Converged == zero OPEN constraints (all satisfied or waived)."""
        return len(self.open_constraints()) == 0

    def summary(self) -> dict[str, int]:
        self._load()
        counts = {STATUS_OPEN: 0, STATUS_SATISFIED: 0, STATUS_WAIVED: 0}
        open_critical = 0
        for c in self._constraints.values():
            counts[c.status] = counts.get(c.status, 0) + 1
            if c.status == STATUS_OPEN and c.severity == "CRITICAL":
                open_critical += 1
        return {
            "total": len(self._constraints),
            "open": counts[STATUS_OPEN],
            "satisfied": counts[STATUS_SATISFIED],
            "waived": counts[STATUS_WAIVED],
            "open_critical": open_critical,
        }

    def ingest_hook_issues(self, issues: list[Any]) -> int:
        """Convert hook issues (objects with hook_id/severity/section/message)
        into constraints. Returns the number of NEW constraints added.

        Accepts HookIssue-like objects or plain dicts. Idempotent: re-ingesting
        the same issues does not create duplicates.
        """
        added = 0
        for issue in issues:
            if isinstance(issue, dict):
                source = issue.get("hook_id", "hook")
                severity = issue.get("severity", "WARNING")
                section = issue.get("section", "")
                message = issue.get("message", "")
            else:
                source = getattr(issue, "hook_id", "hook")
                severity = getattr(issue, "severity", "WARNING")
                section = getattr(issue, "section", "")
                message = getattr(issue, "message", "")
            if not message:
                continue
            key = _derive_key(source, message, section)
            before = key in self._constraints if self._loaded else False
            self.add(source, message, severity=severity, section=section)
            if not before and self.get(key) is not None:
                added += 1
        return added

    def to_markdown(self) -> str:
        s = self.summary()
        lines = [
            "# Constraint Ledger",
            "",
            f"- **Converged**: {'✅ yes' if self.is_converged() else '❌ no'}",
            f"- **Open**: {s['open']} ({s['open_critical']} CRITICAL)",
            f"- **Satisfied**: {s['satisfied']}",
            f"- **Waived**: {s['waived']}",
            f"- **Total tracked**: {s['total']}",
        ]
        open_items = self.open_constraints()
        if open_items:
            lines.extend(["", "## Open constraints (must resolve)", ""])
            for c in sorted(
                open_items,
                key=lambda x: SEVERITY_ORDER.get(x.severity, 0),
                reverse=True,
            ):
                loc = f" [{c.section}]" if c.section else ""
                lines.append(f"- **{c.severity}** ({c.source}){loc}: {c.description} `({c.key})`")
        return "\n".join(lines)
