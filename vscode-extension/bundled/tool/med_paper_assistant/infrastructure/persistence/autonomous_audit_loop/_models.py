"""Enums and dataclasses shared by the autonomous audit loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ── Enums ──────────────────────────────────────────────────────────────


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class RoundVerdict(str, Enum):
    CONTINUE = "continue"
    QUALITY_MET = "quality_met"
    STAGNATED = "stagnated"
    MAX_ROUNDS = "max_rounds"
    USER_NEEDED = "user_needed"
    REWRITE_NEEDED = "rewrite_needed"


# ── Data Classes ───────────────────────────────────────────────────────


@dataclass
class AuditIssue:
    """A quality issue found during an audit round."""

    hook_id: str
    severity: str  # Severity value
    description: str
    suggested_fix: str
    section: str | None = None
    fixed: bool = False
    persistent_rounds: int = 0  # how many rounds this issue has persisted


@dataclass
class AuditFix:
    """A fix applied to address an issue."""

    issue_index: int
    strategy: str
    success: bool
    details: str = ""


@dataclass
class RoundRecord:
    """Complete record of one audit round."""

    round_number: int
    issues: list[dict[str, Any]] = field(default_factory=list)
    fixes: list[dict[str, Any]] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    weighted_avg: float = 0.0
    verdict: str = ""
    started_at: str = ""
    completed_at: str = ""
    artifact_hash_start: str = ""
    artifact_hash_end: str = ""


@dataclass
class AuditLoopConfig:
    """Configuration for the audit loop."""

    max_rounds: int = 5
    min_rounds: int = 2  # Minimum rounds before QUALITY_MET allowed
    quality_threshold: float = 7.0
    stagnation_rounds: int = 2
    stagnation_delta: float = 0.3
    auto_fix_severities: list[str] = field(
        default_factory=lambda: [Severity.CRITICAL.value, Severity.MAJOR.value]
    )
    context: str = "default"  # e.g. "hook-a-methods", "hook-c", "review"

    # Quality dimension weights (must sum to 1.0)
    dimension_weights: dict[str, float] = field(
        default_factory=lambda: {
            "citation_quality": 0.15,
            "methodology_reproducibility": 0.25,
            "text_quality": 0.20,
            "concept_consistency": 0.20,
            "format_compliance": 0.10,
            "figure_table_quality": 0.10,
        }
    )
