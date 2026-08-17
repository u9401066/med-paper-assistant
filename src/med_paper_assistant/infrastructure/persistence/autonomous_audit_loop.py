"""
Autonomous Audit Loop — Multi-round self-improving paper quality audit engine.

Orchestrates iterative evaluate → fix → re-evaluate cycles until paper quality
meets the configured threshold, stagnates, or hits the round limit.

Architecture:
  Infrastructure layer service. Used by the Agent during Phase 5 (Hook A/B),
  Phase 6 (Hook C), and Phase 7 (Autonomous Review) of the auto-paper pipeline.

  The engine is a STATE MACHINE — it does NOT run checks or apply fixes itself.
  Instead, the Agent drives it:
    1. loop.start_round()       → get context for this round
    2. loop.record_issue(...)   → log each quality issue found
    3. loop.record_fix(...)     → log each fix applied
    4. loop.complete_round(scores) → submit scores, get verdict

  Integrates with:
    - QualityScorecard: score tracking per dimension
    - HookEffectivenessTracker: hook event recording

  Persists state to `.audit/audit-loop-{context}.json` for checkpoint recovery.

Stop conditions (Ralph Wiggum–proof):
  - QUALITY_MET:  weighted avg ≥ quality_threshold
  - MAX_ROUNDS:   reached max_rounds limit
  - STAGNATED:    score improved < stagnation_delta for N consecutive rounds
  - USER_NEEDED:  critical issues failed to fix across 2+ rounds
  - REWRITE_NEEDED: section(s) need major rewrite → regress to Phase 5
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


# Phase 7 is a release-quality gate, so callers may make it stricter but may
# not lower these repository policy floors.  Keeping the policy beside the
# state machine also lets the persisted-state verifier reject hand-edited
# configurations instead of merely recomputing a verdict against an
# attacker-controlled threshold.
REVIEW_MIN_ROUNDS_FLOOR = 2
REVIEW_QUALITY_THRESHOLD_FLOOR = 7.0
REVIEW_MAX_ROUNDS_LIMIT = 10


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


def validate_review_config_policy(config: AuditLoopConfig) -> list[str]:
    """Return policy errors for a Phase 7 review configuration.

    Other audit-loop contexts intentionally retain their existing flexibility;
    only the ``review`` context is a Phase 7 hard gate.
    """

    if config.context != "review":
        return []

    errors: list[str] = []
    if (
        isinstance(config.min_rounds, bool)
        or not isinstance(config.min_rounds, int)
        or config.min_rounds < REVIEW_MIN_ROUNDS_FLOOR
    ):
        errors.append(f"review min_rounds must be at least {REVIEW_MIN_ROUNDS_FLOOR}")
    if (
        isinstance(config.max_rounds, bool)
        or not isinstance(config.max_rounds, int)
        or not isinstance(config.min_rounds, int)
        or config.max_rounds < config.min_rounds
        or config.max_rounds > REVIEW_MAX_ROUNDS_LIMIT
    ):
        errors.append(
            f"review max_rounds must be >= min_rounds and not exceed {REVIEW_MAX_ROUNDS_LIMIT}"
        )
    if (
        isinstance(config.quality_threshold, bool)
        or not isinstance(config.quality_threshold, (int, float))
        or not math.isfinite(float(config.quality_threshold))
        or float(config.quality_threshold) < REVIEW_QUALITY_THRESHOLD_FLOOR
        or float(config.quality_threshold) > 10.0
    ):
        errors.append(
            f"review quality_threshold must be at least {REVIEW_QUALITY_THRESHOLD_FLOOR:.1f}"
        )
    return errors


# ── Main Engine ────────────────────────────────────────────────────────


class AutonomousAuditLoop:
    """
    Multi-round autonomous paper quality audit engine.

    Usage by Agent:
        loop = AutonomousAuditLoop(audit_dir, config=AuditLoopConfig(
            max_rounds=3, quality_threshold=7.0, context="hook-a-methods"
        ))
        loop.load()  # resume from checkpoint if exists

        while True:
            ctx = loop.start_round()
            # Agent runs hooks, records issues...
            loop.record_issue("A1", Severity.CRITICAL, "Word count 20% over",
                              "Trim verbose sentences", section="Methods")
            # Agent applies fixes...
            loop.record_fix(0, "trim_sentences", True, "Reduced by 150 words")
            # Submit scores and get verdict
            scores = {"text_quality": 7.5, "citation_quality": 8.0, ...}
            verdict = loop.complete_round(scores)
            if verdict != RoundVerdict.CONTINUE:
                break

        report = loop.generate_report()
    """

    def __init__(
        self,
        audit_dir: str | Path,
        config: AuditLoopConfig | None = None,
    ) -> None:
        self._audit_dir = Path(audit_dir)
        self._config = config or AuditLoopConfig()
        ctx = self._config.context
        self._data_path = self._audit_dir / f"audit-loop-{ctx}.json"
        self._report_path = self._audit_dir / f"audit-loop-{ctx}.md"

        # State
        self._rounds: list[RoundRecord] = []
        self._current_issues: list[AuditIssue] = []
        self._current_fixes: list[AuditFix] = []
        self._current_round: int = 0
        self._in_round: bool = False
        self._round_start_time: str = ""
        self._completed: bool = False
        self._rewrite_sections: list[str] = []
        self._rewrite_reason: str = ""

    # ── Round Lifecycle ────────────────────────────────────────────

    def start_round(self, artifact_hash: str = "") -> dict[str, Any]:
        """Start a new audit round. Returns context for the Agent.

        Args:
            artifact_hash: Hash of the primary artifact (e.g. manuscript) at round start.
                          Used to verify the artifact was actually modified during the round.
        """
        if self._completed:
            raise RuntimeError("Audit loop already completed")
        if self._in_round:
            raise RuntimeError("Previous round not completed — call complete_round() first")

        self._current_round += 1
        self._current_issues = []
        self._current_fixes = []
        self._in_round = True
        self._round_start_time = datetime.now().astimezone().isoformat()
        self._artifact_hash_start = artifact_hash

        # Carry forward persistent critical issues from previous round
        persistent = self._get_persistent_issues()

        return {
            "round": self._current_round,
            "max_rounds": self._config.max_rounds,
            "quality_threshold": self._config.quality_threshold,
            "context": self._config.context,
            "previous_score": self._rounds[-1].weighted_avg if self._rounds else None,
            "persistent_issues": persistent,
            "focus_dimensions": self._get_weak_dimensions(),
        }

    def record_issue(
        self,
        hook_id: str,
        severity: Severity | str,
        description: str,
        suggested_fix: str,
        section: str | None = None,
    ) -> int:
        """Record a quality issue found during this round. Returns issue index."""
        if not self._in_round:
            raise RuntimeError("No active round — call start_round() first")

        sev = severity.value if isinstance(severity, Severity) else severity
        persistent_count = self._count_persistent(hook_id, description)

        issue = AuditIssue(
            hook_id=hook_id,
            severity=sev,
            description=description,
            suggested_fix=suggested_fix,
            section=section,
            persistent_rounds=persistent_count,
        )
        self._current_issues.append(issue)
        return len(self._current_issues) - 1

    def record_fix(
        self,
        issue_index: int,
        strategy: str,
        success: bool,
        details: str = "",
    ) -> None:
        """Record a fix applied for an issue."""
        if not self._in_round:
            raise RuntimeError("No active round — call start_round() first")
        if issue_index < 0 or issue_index >= len(self._current_issues):
            raise IndexError(f"Issue index {issue_index} out of range")

        fix = AuditFix(
            issue_index=issue_index,
            strategy=strategy,
            success=success,
            details=details,
        )
        self._current_fixes.append(fix)

        if success:
            self._current_issues[issue_index].fixed = True

    def complete_round(self, scores: dict[str, float], artifact_hash: str = "") -> RoundVerdict:
        """Complete the current round with quality scores. Returns verdict.

        Args:
            scores: Quality dimension scores.
            artifact_hash: Hash of the primary artifact at round end.
                          Compared with start hash to verify modification.
        """
        if not self._in_round:
            raise RuntimeError("No active round — call start_round() first")

        weighted_avg = self._compute_weighted_avg(scores)

        record = RoundRecord(
            round_number=self._current_round,
            issues=[asdict(i) for i in self._current_issues],
            fixes=[asdict(f) for f in self._current_fixes],
            scores=scores,
            weighted_avg=round(weighted_avg, 2),
            started_at=self._round_start_time,
            completed_at=datetime.now().astimezone().isoformat(),
            artifact_hash_start=getattr(self, "_artifact_hash_start", ""),
            artifact_hash_end=artifact_hash,
        )

        verdict = self._determine_verdict(weighted_avg)
        record.verdict = verdict.value
        self._rounds.append(record)
        self._in_round = False

        if verdict != RoundVerdict.CONTINUE:
            self._completed = True

        self.save()
        return verdict

    def request_rewrite(self, sections: list[str], reason: str) -> None:
        """Mark sections for rewrite regression to Phase 5.

        Called when review determines that patch_draft fixes are insufficient
        and a section needs a full rewrite. Sets the verdict to REWRITE_NEEDED
        and records which sections need rewriting.

        Args:
            sections: List of section names that need rewriting.
            reason: Explanation of why rewrite is needed.
        """
        if not sections:
            raise ValueError("Must specify at least one section to rewrite")
        self._rewrite_sections = list(sections)
        self._rewrite_reason = reason
        self._completed = True

        # Record a synthetic round record if we're mid-round
        if self._in_round:
            record = RoundRecord(
                round_number=self._current_round,
                issues=[asdict(i) for i in self._current_issues],
                fixes=[asdict(f) for f in self._current_fixes],
                scores={},
                weighted_avg=0.0,
                verdict=RoundVerdict.REWRITE_NEEDED.value,
                started_at=self._round_start_time,
                completed_at=datetime.now().astimezone().isoformat(),
            )
            self._rounds.append(record)
            self._in_round = False

        self.save()
        logger.info(
            "Rewrite requested",
            sections=sections,
            reason=reason,
            round=self._current_round,
        )

    @property
    def rewrite_sections(self) -> list[str]:
        """Sections that need rewriting (set by request_rewrite)."""
        return self._rewrite_sections

    @property
    def rewrite_reason(self) -> str:
        """Reason for rewrite request."""
        return self._rewrite_reason

    # ── Query Methods ──────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Get current loop status."""
        latest = self._rounds[-1].weighted_avg if self._rounds else None
        return {
            "context": self._config.context,
            "current_round": self._current_round,
            "max_rounds": self._config.max_rounds,
            "total_rounds_completed": len(self._rounds),
            "in_round": self._in_round,
            "completed": self._completed,
            "quality_threshold": self._config.quality_threshold,
            "latest_score": latest,
            "latest_weighted_score": latest,  # alias used by pipeline_gate.py
            "latest_verdict": self._rounds[-1].verdict if self._rounds else None,
            "score_trend": [r.weighted_avg for r in self._rounds],
        }

    def get_score_trend(self) -> list[dict[str, Any]]:
        """Get score progression across rounds."""
        return [
            {
                "round": r.round_number,
                "weighted_avg": r.weighted_avg,
                "scores": r.scores,
                "issues_count": len(r.issues),
                "fixes_count": len(r.fixes),
                "verdict": r.verdict,
            }
            for r in self._rounds
        ]

    @classmethod
    def validate_serialized_state(cls, data: Any) -> list[str]:
        """Recompute persisted scores and verdicts instead of trusting JSON labels.

        The audit-loop file is intentionally human-readable, so a phase gate must
        treat it as untrusted input.  This verifier reconstructs the state machine
        round by round and returns every integrity error it finds.  It performs no
        writes and is safe to call from prerequisite and release gates.
        """
        errors: list[str] = []
        if not isinstance(data, dict):
            return ["audit loop state must be a JSON object"]
        if data.get("version") != 1:
            errors.append("audit loop version must be 1")

        raw_config = data.get("config")
        if not isinstance(raw_config, dict):
            return [*errors, "audit loop config must be a JSON object"]

        config_fields = {item.name for item in fields(AuditLoopConfig)}
        missing_config = sorted(config_fields - raw_config.keys())
        unknown_config = sorted(raw_config.keys() - config_fields)
        if missing_config:
            errors.append(f"audit loop config missing fields: {', '.join(missing_config)}")
        if unknown_config:
            errors.append(f"audit loop config has unknown fields: {', '.join(unknown_config)}")

        try:
            config = AuditLoopConfig(
                **{name: raw_config[name] for name in config_fields if name in raw_config}
            )
        except (TypeError, ValueError) as exc:
            return [*errors, f"audit loop config is invalid: {exc}"]

        min_rounds_valid = not (
            isinstance(config.min_rounds, bool)
            or not isinstance(config.min_rounds, int)
            or config.min_rounds < 1
        )
        if not min_rounds_valid:
            errors.append("config.min_rounds must be a positive integer")
        max_rounds_valid = not (
            isinstance(config.max_rounds, bool)
            or not isinstance(config.max_rounds, int)
            or not min_rounds_valid
            or config.max_rounds < config.min_rounds
        )
        if not max_rounds_valid:
            errors.append("config.max_rounds must be an integer >= min_rounds")
        if (
            isinstance(config.quality_threshold, bool)
            or not isinstance(config.quality_threshold, (int, float))
            or not math.isfinite(float(config.quality_threshold))
            or not 0 <= float(config.quality_threshold) <= 10
        ):
            errors.append("config.quality_threshold must be between 0 and 10")
        if (
            isinstance(config.stagnation_rounds, bool)
            or not isinstance(config.stagnation_rounds, int)
            or config.stagnation_rounds < 1
        ):
            errors.append("config.stagnation_rounds must be a positive integer")
        if (
            isinstance(config.stagnation_delta, bool)
            or not isinstance(config.stagnation_delta, (int, float))
            or not math.isfinite(float(config.stagnation_delta))
            or not 0 <= float(config.stagnation_delta) <= 10
        ):
            errors.append("config.stagnation_delta must be between 0 and 10")
        valid_severities = {severity.value for severity in Severity}
        if (
            not isinstance(config.auto_fix_severities, list)
            or not config.auto_fix_severities
            or any(
                not isinstance(severity, str) or severity not in valid_severities
                for severity in config.auto_fix_severities
            )
        ):
            errors.append("config.auto_fix_severities must contain known severity strings")
        if not isinstance(config.context, str) or not config.context.strip():
            errors.append("config.context must be a non-empty string")

        weights = config.dimension_weights
        valid_weights = isinstance(weights, dict) and bool(weights)
        if valid_weights:
            for name, weight in weights.items():
                if (
                    not isinstance(name, str)
                    or not name
                    or isinstance(weight, bool)
                    or not isinstance(weight, (int, float))
                    or not math.isfinite(float(weight))
                    or float(weight) <= 0
                ):
                    valid_weights = False
                    break
        if not valid_weights:
            errors.append("config.dimension_weights must contain positive numeric weights")
            weights = {}
        elif abs(sum(float(weight) for weight in weights.values()) - 1.0) > 1e-6:
            errors.append("config.dimension_weights must sum to 1.0")

        errors.extend(validate_review_config_policy(config))

        if errors:
            return errors

        raw_rounds = data.get("rounds")
        if not isinstance(raw_rounds, list):
            return [*errors, "audit loop rounds must be a JSON array"]
        if isinstance(config.max_rounds, int) and len(raw_rounds) > config.max_rounds:
            errors.append(
                f"audit loop contains {len(raw_rounds)} rounds, above max_rounds={config.max_rounds}"
            )

        verifier = cls(Path("."), config=config)
        terminal_seen = False
        for index, raw_round in enumerate(raw_rounds, start=1):
            prefix = f"round {index}"
            if not isinstance(raw_round, dict):
                errors.append(f"{prefix} must be a JSON object")
                continue
            if raw_round.get("round_number") != index:
                errors.append(f"{prefix} round_number must be {index}")
            if terminal_seen:
                errors.append(f"{prefix} appears after a terminal verdict")

            raw_scores = raw_round.get("scores")
            scores: dict[str, float] = {}
            scores_valid = False
            if not isinstance(raw_scores, dict) or set(raw_scores) != set(weights):
                errors.append(f"{prefix} scores must exactly match configured dimensions")
            else:
                scores_valid = True
                for dimension, score in raw_scores.items():
                    if (
                        isinstance(score, bool)
                        or not isinstance(score, (int, float))
                        or not math.isfinite(float(score))
                        or not 0 <= float(score) <= 10
                    ):
                        errors.append(f"{prefix} score {dimension!r} must be between 0 and 10")
                        scores_valid = False
                if scores_valid:
                    scores = {
                        str(dimension): float(score) for dimension, score in raw_scores.items()
                    }

            computed_weighted = verifier._compute_weighted_avg(scores) if scores_valid else 0.0
            stored_weighted = raw_round.get("weighted_avg")
            if (
                isinstance(stored_weighted, bool)
                or not isinstance(stored_weighted, (int, float))
                or not math.isfinite(float(stored_weighted))
                or abs(float(stored_weighted) - round(computed_weighted, 2)) > 1e-6
            ):
                errors.append(
                    f"{prefix} weighted_avg does not match the configured score calculation"
                )

            raw_issues = raw_round.get("issues")
            if not isinstance(raw_issues, list):
                errors.append(f"{prefix} issues must be a JSON array")
                raw_issues = []
            current_issues: list[AuditIssue] = []
            for issue_index, raw_issue in enumerate(raw_issues):
                if not isinstance(raw_issue, dict):
                    errors.append(f"{prefix} issue {issue_index} must be a JSON object")
                    continue
                issue_fields = {item.name for item in fields(AuditIssue)}
                if set(raw_issue) != issue_fields:
                    errors.append(f"{prefix} issue {issue_index} has an invalid schema")
                    continue
                hook_id = raw_issue.get("hook_id")
                severity = raw_issue.get("severity")
                description = raw_issue.get("description")
                suggested_fix = raw_issue.get("suggested_fix")
                section = raw_issue.get("section")
                fixed = raw_issue.get("fixed")
                persistent_rounds = raw_issue.get("persistent_rounds")
                if (
                    not isinstance(hook_id, str)
                    or not hook_id.strip()
                    or severity not in valid_severities
                    or not isinstance(description, str)
                    or not description.strip()
                    or not isinstance(suggested_fix, str)
                    or not suggested_fix.strip()
                    or (section is not None and not isinstance(section, str))
                    or not isinstance(fixed, bool)
                    or isinstance(persistent_rounds, bool)
                    or not isinstance(persistent_rounds, int)
                    or persistent_rounds < 0
                ):
                    errors.append(f"{prefix} issue {issue_index} has invalid field values")
                    continue
                current_issues.append(
                    AuditIssue(
                        hook_id=hook_id,
                        severity=severity,
                        description=description,
                        suggested_fix=suggested_fix,
                        section=section,
                        fixed=fixed,
                        persistent_rounds=persistent_rounds,
                    )
                )

            raw_fixes = raw_round.get("fixes")
            if not isinstance(raw_fixes, list) or any(
                not isinstance(item, dict) for item in raw_fixes
            ):
                errors.append(f"{prefix} fixes must be a JSON array of objects")
                raw_fixes = []
            else:
                fix_fields = {item.name for item in fields(AuditFix)}
                successful_fix_indexes: set[int] = set()
                for fix_index, raw_fix in enumerate(raw_fixes):
                    if set(raw_fix) != fix_fields:
                        errors.append(f"{prefix} fix {fix_index} has an invalid schema")
                        continue
                    issue_index = raw_fix.get("issue_index")
                    strategy = raw_fix.get("strategy")
                    success = raw_fix.get("success")
                    details = raw_fix.get("details")
                    if (
                        isinstance(issue_index, bool)
                        or not isinstance(issue_index, int)
                        or not 0 <= issue_index < len(current_issues)
                        or not isinstance(strategy, str)
                        or not strategy.strip()
                        or not isinstance(success, bool)
                        or not isinstance(details, str)
                    ):
                        errors.append(f"{prefix} fix {fix_index} has invalid field values")
                        continue
                    if success:
                        successful_fix_indexes.add(issue_index)
                fixed_issue_indexes = {
                    issue_index for issue_index, issue in enumerate(current_issues) if issue.fixed
                }
                if successful_fix_indexes != fixed_issue_indexes:
                    errors.append(f"{prefix} issue fixed flags do not match successful fix records")

            started_at = raw_round.get("started_at")
            completed_at = raw_round.get("completed_at")
            try:
                if not isinstance(started_at, str) or not isinstance(completed_at, str):
                    raise TypeError("timestamps must be strings")
                started_time = datetime.fromisoformat(started_at)
                completed_time = datetime.fromisoformat(completed_at)
                if started_time.utcoffset() is None or completed_time.utcoffset() is None:
                    raise ValueError("timestamps must include a UTC offset")
                if completed_time < started_time:
                    raise ValueError("completion precedes start")
            except (TypeError, ValueError):
                errors.append(f"{prefix} timestamps are missing, invalid, or out of order")

            verifier._current_round = index
            verifier._current_issues = current_issues
            expected_verdict = verifier._determine_verdict(computed_weighted)
            stored_verdict = raw_round.get("verdict")
            if stored_verdict != expected_verdict.value:
                errors.append(
                    f"{prefix} verdict={stored_verdict!r} does not match recomputed "
                    f"verdict={expected_verdict.value!r}"
                )
            terminal_seen = expected_verdict is not RoundVerdict.CONTINUE

            verifier._rounds.append(
                RoundRecord(
                    round_number=index,
                    issues=raw_issues,
                    fixes=raw_fixes,
                    scores=scores,
                    weighted_avg=round(computed_weighted, 2),
                    verdict=expected_verdict.value,
                    started_at=str(raw_round.get("started_at", "")),
                    completed_at=str(raw_round.get("completed_at", "")),
                    artifact_hash_start=str(raw_round.get("artifact_hash_start", "")),
                    artifact_hash_end=str(raw_round.get("artifact_hash_end", "")),
                )
            )

        in_round = data.get("in_round")
        completed = data.get("completed")
        if not isinstance(in_round, bool):
            errors.append("audit loop in_round must be boolean")
            in_round = False
        if not isinstance(completed, bool):
            errors.append("audit loop completed must be boolean")
            completed = False
        expected_current_round = len(raw_rounds) + (1 if in_round else 0)
        current_round = data.get("current_round")
        if (
            isinstance(current_round, bool)
            or not isinstance(current_round, int)
            or current_round != expected_current_round
        ):
            errors.append(f"current_round must be {expected_current_round}")
        if completed != terminal_seen:
            errors.append("completed flag does not match the recomputed final verdict")
        if completed and in_round:
            errors.append("a completed audit loop cannot have an active round")

        return errors

    @property
    def is_completed(self) -> bool:
        return self._completed

    @property
    def current_round_number(self) -> int:
        return self._current_round

    @property
    def latest_verdict(self) -> RoundVerdict | None:
        if not self._rounds:
            return None
        return RoundVerdict(self._rounds[-1].verdict)

    # ── Verdict Logic ──────────────────────────────────────────────

    def _determine_verdict(self, weighted_avg: float) -> RoundVerdict:
        """Determine whether to continue, stop, or escalate."""
        cfg = self._config

        # 0. Minimum rounds not yet reached → must continue
        if self._current_round < cfg.min_rounds:
            return RoundVerdict.CONTINUE

        # 1. Quality threshold met (only after min_rounds)
        if weighted_avg >= cfg.quality_threshold:
            return RoundVerdict.QUALITY_MET

        # 2. Max rounds reached
        if self._current_round >= cfg.max_rounds:
            return RoundVerdict.MAX_ROUNDS

        # 3. Persistent critical issues that can't be fixed → need user
        unfixed_critical = [
            i
            for i in self._current_issues
            if i.severity == Severity.CRITICAL.value and not i.fixed and i.persistent_rounds >= 2
        ]
        if unfixed_critical:
            return RoundVerdict.USER_NEEDED

        # 4. Stagnation detection
        if self._is_stagnated():
            return RoundVerdict.STAGNATED

        return RoundVerdict.CONTINUE

    def _is_stagnated(self) -> bool:
        """Check if scores have stagnated (no meaningful improvement)."""
        cfg = self._config
        n = cfg.stagnation_rounds

        # Need at least n+1 rounds to detect stagnation (current + n previous)
        total = len(self._rounds) + 1  # +1 for the round being completed
        if total <= n:
            return False

        # We check the already-recorded rounds
        if len(self._rounds) < n:
            return False

        recent = [r.weighted_avg for r in self._rounds[-n:]]
        # Check if all consecutive deltas are below threshold
        for i in range(1, len(recent)):
            if recent[i] - recent[i - 1] >= cfg.stagnation_delta:
                return False
        return True

    # ── Score Computation ──────────────────────────────────────────

    def _compute_weighted_avg(self, scores: dict[str, float]) -> float:
        """Compute weighted average from dimension scores."""
        weights = self._config.dimension_weights
        total_weight = 0.0
        total_score = 0.0

        for dim, weight in weights.items():
            if dim in scores:
                total_score += scores[dim] * weight
                total_weight += weight

        if total_weight == 0:
            return 0.0
        return total_score / total_weight

    # ── Issue Tracking Helpers ─────────────────────────────────────

    def _get_persistent_issues(self) -> list[dict[str, Any]]:
        """Get issues that persisted across previous rounds (unfixed criticals)."""
        if not self._rounds:
            return []

        last = self._rounds[-1]
        return [
            i
            for i in last.issues
            if i.get("severity") == Severity.CRITICAL.value and not i.get("fixed")
        ]

    def _count_persistent(self, hook_id: str, description: str) -> int:
        """Count how many previous rounds had a similar issue."""
        count = 0
        for r in self._rounds:
            for issue in r.issues:
                if issue.get("hook_id") == hook_id and not issue.get("fixed"):
                    # Fuzzy match: same hook + not fixed = likely persistent
                    count += 1
                    break
        return count

    def _get_weak_dimensions(self) -> list[str]:
        """Identify dimensions that need the most improvement."""
        if not self._rounds:
            return []

        last_scores = self._rounds[-1].scores
        threshold = self._config.quality_threshold

        weak = [(dim, score) for dim, score in last_scores.items() if score < threshold]
        # Sort by score ascending (weakest first)
        weak.sort(key=lambda x: x[1])
        return [dim for dim, _ in weak]

    # ── Persistence ────────────────────────────────────────────────

    def save(self) -> None:
        """Save loop state to disk."""
        self._audit_dir.mkdir(parents=True, exist_ok=True)

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
        self._data_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load(self) -> bool:
        """Load loop state from disk. Returns True if state was loaded."""
        if not self._data_path.is_file():
            return False

        try:
            data = json.loads(self._data_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load audit loop state: %s", e)
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

    # ── Report Generation ──────────────────────────────────────────

    def generate_report(self) -> str:
        """Generate a Markdown audit report."""
        lines: list[str] = []
        ctx = self._config.context
        lines.append(f"# Autonomous Audit Loop Report: {ctx}")
        lines.append("")
        lines.append(f"- **Context**: {ctx}")
        lines.append(f"- **Max Rounds**: {self._config.max_rounds}")
        lines.append(f"- **Quality Threshold**: {self._config.quality_threshold}")
        lines.append(f"- **Rounds Completed**: {len(self._rounds)}")

        if self._rounds:
            final = self._rounds[-1]
            lines.append(f"- **Final Score**: {final.weighted_avg}")
            lines.append(f"- **Final Verdict**: {final.verdict}")
        lines.append("")

        # Score trend table
        if self._rounds:
            lines.append("## Score Trend")
            lines.append("")

            # Collect all dimension names
            all_dims: set[str] = set()
            for r in self._rounds:
                all_dims.update(r.scores.keys())
            dims_sorted = sorted(all_dims)

            header = "| Round | " + " | ".join(dims_sorted) + " | Avg | Verdict |"
            sep = "|-------|" + "|".join(["-------"] * len(dims_sorted)) + "|-----|---------|"
            lines.append(header)
            lines.append(sep)

            for r in self._rounds:
                scores_str = " | ".join(f"{r.scores.get(d, '-')}" for d in dims_sorted)
                lines.append(
                    f"| {r.round_number} | {scores_str} | {r.weighted_avg} | {r.verdict} |"
                )
            lines.append("")

        # Per-round details
        for r in self._rounds:
            lines.append(f"## Round {r.round_number}")
            lines.append("")

            if r.issues:
                lines.append("### Issues Found")
                lines.append("")
                lines.append("| # | Hook | Severity | Section | Description | Fixed |")
                lines.append("|---|------|----------|---------|-------------|-------|")
                for i, issue in enumerate(r.issues):
                    fixed = "✅" if issue.get("fixed") else "❌"
                    sec = issue.get("section") or "—"
                    lines.append(
                        f"| {i} | {issue['hook_id']} | {issue['severity']} "
                        f"| {sec} | {issue['description']} | {fixed} |"
                    )
                lines.append("")

            if r.fixes:
                lines.append("### Fixes Applied")
                lines.append("")
                lines.append("| Issue # | Strategy | Success | Details |")
                lines.append("|---------|----------|---------|---------|")
                for fix in r.fixes:
                    ok = "✅" if fix.get("success") else "❌"
                    lines.append(
                        f"| {fix['issue_index']} | {fix['strategy']} "
                        f"| {ok} | {fix.get('details', '')} |"
                    )
                lines.append("")

        report = "\n".join(lines)

        # Save report to disk
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._report_path.write_text(report, encoding="utf-8")

        return report
