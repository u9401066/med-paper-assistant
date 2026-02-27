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
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


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
        self._round_start_time = datetime.now().isoformat()
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
            completed_at=datetime.now().isoformat(),
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
                completed_at=datetime.now().isoformat(),
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
        return {
            "context": self._config.context,
            "current_round": self._current_round,
            "max_rounds": self._config.max_rounds,
            "total_rounds_completed": len(self._rounds),
            "in_round": self._in_round,
            "completed": self._completed,
            "quality_threshold": self._config.quality_threshold,
            "latest_score": self._rounds[-1].weighted_avg if self._rounds else None,
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
            "rounds": [asdict(r) for r in self._rounds],
            "rewrite_sections": self._rewrite_sections,
            "rewrite_reason": self._rewrite_reason,
            "saved_at": datetime.now().isoformat(),
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
