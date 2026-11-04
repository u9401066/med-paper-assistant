"""Phase 7 gate: autonomous review loop state, artifacts, evidence and termination."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._base import GateBase
from ._review_evidence import (
    final_artifact_check,
    hash_chain_check,
    review_events_check,
    round_hook_checks,
    run_round_hooks,
)
from ._types import GateCheck, GateResult

_TERMINAL_ESCALATIONS = {"max_rounds", "stagnated", "user_needed"}


@dataclass
class _LoopSnapshot:
    state: dict[str, Any] = field(default_factory=dict)
    state_errors: list[str] = field(default_factory=list)
    rounds: list[dict[str, Any]] = field(default_factory=list)
    rounds_completed: int = 0
    loop_verdict: str = "unknown"
    max_rounds: int = 3
    min_rounds: int = 2


def _read_loop_state(loop_state: Path) -> tuple[dict[str, Any], list[str]]:
    state: dict[str, Any] = {}
    state_errors: list[str] = []
    if loop_state.is_file():
        try:
            raw_state = json.loads(loop_state.read_text(encoding="utf-8"))
            if isinstance(raw_state, dict):
                state = raw_state
            else:
                state_errors.append("audit loop state must be a JSON object")
        except (json.JSONDecodeError, OSError):
            state_errors.append("audit-loop-review.json is corrupt or unreadable")
    return state, state_errors


def _apply_state_details(snapshot: _LoopSnapshot) -> None:
    from med_paper_assistant.infrastructure.persistence.autonomous_audit_loop import (
        AutonomousAuditLoop,
    )

    state = snapshot.state
    snapshot.state_errors.extend(AutonomousAuditLoop.validate_serialized_state(state))
    raw_rounds = state.get("rounds")
    if isinstance(raw_rounds, list):
        snapshot.rounds = [item for item in raw_rounds if isinstance(item, dict)]
        snapshot.rounds_completed = len(raw_rounds)
    raw_config = state.get("config")
    if isinstance(raw_config, dict):
        if raw_config.get("context") != "review":
            snapshot.state_errors.append("audit loop config.context must be 'review'")
        raw_max = raw_config.get("max_rounds")
        raw_min = raw_config.get("min_rounds")
        if isinstance(raw_max, int) and not isinstance(raw_max, bool):
            snapshot.max_rounds = raw_max
        if isinstance(raw_min, int) and not isinstance(raw_min, bool):
            snapshot.min_rounds = raw_min
    if snapshot.rounds and len(snapshot.rounds) == snapshot.rounds_completed:
        snapshot.loop_verdict = str(snapshot.rounds[-1].get("verdict", "unknown"))


def _load_snapshot(loop_state: Path) -> _LoopSnapshot:
    state, state_errors = _read_loop_state(loop_state)
    snapshot = _LoopSnapshot(state=state, state_errors=state_errors)
    if state:
        _apply_state_details(snapshot)
    return snapshot


def _state_checks(snapshot: _LoopSnapshot) -> list[GateCheck]:
    state, state_errors = snapshot.state, snapshot.state_errors
    return [
        GateCheck(
            name="review:state_integrity",
            description="Review state scores and verdicts recompute from the state machine",
            passed=bool(state) and not state_errors,
            details=(
                "scores, weighted averages, and verdicts recomputed successfully"
                if state and not state_errors
                else "; ".join(state_errors[:5]) or "MISSING"
            ),
        ),
        GateCheck(
            name="review:rounds_completed",
            description=f"At least {snapshot.min_rounds} review rounds completed (code-enforced)",
            passed=snapshot.rounds_completed >= snapshot.min_rounds,
            details=(
                f"{snapshot.rounds_completed}/{snapshot.min_rounds} minimum rounds completed "
                f"(max={snapshot.max_rounds}), verdict={snapshot.loop_verdict}"
            ),
        ),
    ]


def _missing_round_one_checks(rounds_completed: int) -> list[GateCheck]:
    if rounds_completed != 0:
        return []
    return [
        GateCheck(
            name=f"review:{artifact}",
            description="Round 1 artifact (not yet created)",
            passed=False,
            details="MISSING — review has not started",
        )
        for artifact in [
            "review-report-1.md",
            "author-response-1.md",
            "equator-compliance-1.md",
        ]
    ]


class ReviewPhaseMixin(GateBase):
    """Validation of Phase 7 (autonomous review) — the most critical gate.

    Required artifacts per round: review-report-{N}.md, author-response-{N}.md and
    equator-compliance-{N}.md (or equator-na-{N}.md). The configured minimum number of
    rounds (hard floor: 2) must be completed, evolution-log.jsonl must contain
    review_round events and audit-loop-review.json must exist.
    """

    def _validate_phase_7(self) -> GateResult:
        """Phase 7: Autonomous Review — THE MOST CRITICAL GATE."""
        checks = []

        loop_state = self._audit_dir / "audit-loop-review.json"
        checks.append(
            GateCheck(
                name="audit-loop:state",
                description="Review loop state machine file exists",
                passed=loop_state.is_file(),
                details="exists"
                if loop_state.is_file()
                else "MISSING — AutonomousAuditLoop not used",
            )
        )

        snapshot = _load_snapshot(loop_state)
        checks.extend(_state_checks(snapshot))
        checks.extend(self._round_artifact_checks(snapshot.rounds_completed))
        checks.extend(self._round_evidence_checks(snapshot.rounds))
        checks.extend(_missing_round_one_checks(snapshot.rounds_completed))
        checks.append(
            review_events_check(
                self._audit_dir / "evolution-log.jsonl", snapshot.rounds, snapshot.rounds_completed
            )
        )
        checks.append(self._termination_check(loop_state, snapshot))

        return GateResult(phase=7, phase_name="Autonomous Review", checks=checks, passed=False)

    def _round_artifact_checks(self, rounds_completed: int) -> list[GateCheck]:
        checks = []
        for i in range(1, rounds_completed + 1):
            for artifact_pattern, desc in [
                (f"review-report-{i}.md", f"Round {i} review report"),
                (f"author-response-{i}.md", f"Round {i} author response"),
            ]:
                p = self._audit_dir / artifact_pattern
                checks.append(
                    GateCheck(
                        name=f"review:{artifact_pattern}",
                        description=desc,
                        passed=p.is_file(),
                        details="exists" if p.is_file() else "MISSING",
                    )
                )

            # EQUATOR compliance (may be N/A)
            equator_p = self._audit_dir / f"equator-compliance-{i}.md"
            equator_na = self._audit_dir / f"equator-na-{i}.md"
            equator_exists = equator_p.is_file() or equator_na.is_file()
            checks.append(
                GateCheck(
                    name=f"review:equator-{i}",
                    description=f"Round {i} EQUATOR compliance report (or N/A declaration)",
                    passed=equator_exists,
                    details="exists"
                    if equator_exists
                    else "MISSING — even N/A needs a formal report file",
                )
            )
        return checks

    def _round_evidence_checks(self, rounds: list[dict[str, Any]]) -> list[GateCheck]:
        """Re-run R1-R6 from current artifacts and verify the manuscript hash chain."""
        manuscript_path = self._drafts_dir / "manuscript.md"
        manuscript_content = ""
        manuscript_hash = self._compute_review_drafts_hash()
        if manuscript_path.is_file():
            try:
                manuscript_content = manuscript_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                manuscript_content = ""

        checks: list[GateCheck] = []
        previous_end_hash = ""
        for i, round_state in enumerate(rounds, start=1):
            chain_check, start_hash, end_hash = hash_chain_check(
                i, round_state, previous_end_hash, manuscript_hash
            )
            previous_end_hash = end_hash
            checks.append(chain_check)
            hook_results, hook_error = run_round_hooks(
                self._project_dir, i, round_state, start_hash, end_hash, manuscript_content
            )
            checks.extend(round_hook_checks(i, hook_results, hook_error))

        checks.append(final_artifact_check(rounds, manuscript_hash))
        return checks

    def _termination_check(self, loop_state: Path, snapshot: _LoopSnapshot) -> GateCheck:
        """Only a recomputed quality_met verdict is autonomous evidence of completion.

        Other terminal verdicts require an explicit, state-bound human receipt.
        """
        state_errors, loop_verdict, rounds = (
            snapshot.state_errors,
            snapshot.loop_verdict,
            snapshot.rounds,
        )
        override_valid = False
        override_details = "not required"
        if not state_errors and loop_verdict in _TERMINAL_ESCALATIONS and rounds:
            final_score = rounds[-1].get("weighted_avg")
            raw_threshold = snapshot.state.get("config", {}).get("quality_threshold")
            if (
                isinstance(final_score, (int, float))
                and not isinstance(final_score, bool)
                and (
                    isinstance(raw_threshold, (int, float)) and not isinstance(raw_threshold, bool)
                )
            ):
                override_valid, override_details = self._validate_review_completion_override(
                    loop_state,
                    verdict=loop_verdict,
                    weighted_score=float(final_score),
                    quality_threshold=float(raw_threshold),
                    final_completed_at=str(rounds[-1].get("completed_at") or ""),
                    final_artifact_sha256=str(rounds[-1].get("artifact_hash_end") or ""),
                )
        proper_termination = not state_errors and (loop_verdict == "quality_met" or override_valid)
        return GateCheck(
            name="review:proper_termination",
            description="Review met its quality target or has explicit human acceptance",
            passed=proper_termination,
            details=(
                f"verdict={loop_verdict}"
                if loop_verdict == "quality_met" and proper_termination
                else f"verdict={loop_verdict}; {override_details}"
            ),
        )
