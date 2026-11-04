"""Phase 7 review completion check and human-approval override validation."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from med_paper_assistant.infrastructure.external.approval_signatures import (
    REVIEW_APPROVAL_SCHEMA,
)

from ._approval import check_receipt_identity, check_receipt_preamble
from ._base import GateBase
from ._types import GateCheck

_LABEL = "human approval receipt"


def _failure_summary(phase7_failures: list[GateCheck]) -> str:
    """Summarise failed Phase 7 checks, preferring the most specific one."""
    state_check = next(
        (check for check in phase7_failures if check.name == "review:state_integrity"),
        None,
    )
    if state_check is not None:
        return f"Review state integrity failed: {state_check.details}"
    rounds_check = next(
        (check for check in phase7_failures if check.name == "review:rounds_completed"),
        None,
    )
    if rounds_check is not None:
        return rounds_check.details
    termination = next(
        (check for check in phase7_failures if check.name == "review:proper_termination"),
        None,
    )
    if termination is not None:
        return f"Review loop not properly terminated ({termination.details})."
    examples = ", ".join(c.name for c in phase7_failures[:5])
    return f"Phase 7 artifact gate failed: {examples}"


def _number_mismatch(stored: Any, expected: float) -> bool:
    return (
        isinstance(stored, bool)
        or not isinstance(stored, (int, float))
        or not math.isclose(float(stored), expected, abs_tol=1e-6)
    )


def _review_timestamp_failure(override: dict[str, Any], final_completed_at: str) -> str | None:
    try:
        approved_at = override.get("approved_at")
        if not isinstance(approved_at, str):
            raise TypeError("approved_at must be a string")
        approved_time = datetime.fromisoformat(approved_at)
        completed_time = datetime.fromisoformat(final_completed_at)
        if approved_time.utcoffset() is None or completed_time.utcoffset() is None:
            raise ValueError("timestamps must include a UTC offset")
        if approved_time < completed_time:
            return "human approval predates the final review round"
        if approved_time > datetime.now().astimezone() + timedelta(minutes=5):
            return "human approval receipt timestamp is in the future"
    except (TypeError, ValueError):
        return "human approval receipt timestamp is invalid"
    return None


def _review_binding_failure(
    override: dict[str, Any], verdict: str, state_hash: str, final_artifact_sha256: str
) -> str | None:
    if override.get("accepted_verdict") != verdict:
        return "human approval receipt verdict does not match review state"
    if override.get("audit_loop_sha256") != state_hash:
        return "human approval receipt is stale for the current review state"
    if override.get("final_artifact_sha256") != final_artifact_sha256:
        return "human approval receipt is stale for the current manuscript"
    return None


def _review_score_failure(
    override: dict[str, Any], weighted_score: float, quality_threshold: float
) -> str | None:
    if _number_mismatch(override.get("final_weighted_score"), weighted_score):
        return "human approval receipt score does not match review state"
    if _number_mismatch(override.get("quality_threshold"), quality_threshold):
        return "human approval receipt threshold does not match review config"
    return None


class ReviewCompletionMixin(GateBase):
    """Phase 7 completion summary and sub-threshold review override validation."""

    def _check_review_completed(self) -> tuple[bool, str]:
        """Check whether the Phase 7 review loop was completed.

        Validates:
        1. audit-loop-review.json exists
        2. At least min_rounds rounds were completed
        3. Loop terminated with a valid verdict

        Returns:
            (passed, details) tuple for use as a GateCheck.
        """
        loop_state_path = self._audit_dir / "audit-loop-review.json"
        if not loop_state_path.is_file():
            return (
                False,
                "MISSING — run start_review_round to begin Phase 7 review loop",
            )

        phase7_failures = self._validate_phase_7().critical_failures
        if phase7_failures:
            return False, _failure_summary(phase7_failures)

        state = json.loads(loop_state_path.read_text(encoding="utf-8"))
        rounds = state["rounds"]
        rounds_completed = len(rounds)
        config = state["config"]
        max_rounds = config["max_rounds"]
        last_verdict = rounds[-1]["verdict"]

        return (
            True,
            f"{rounds_completed}/{max_rounds} rounds completed, verdict={last_verdict}",
        )

    def _validate_review_completion_override(
        self,
        loop_state_path: Path,
        *,
        verdict: str,
        weighted_score: float,
        quality_threshold: float,
        final_completed_at: str,
        final_artifact_sha256: str,
    ) -> tuple[bool, str]:
        """Validate a human-collaboration receipt for a sub-threshold review loop.

        A terminal state such as ``max_rounds`` is an escalation condition, not
        proof that the manuscript met its quality target.  The receipt binds an
        explicit human decision to the exact persisted loop bytes and score so a
        stale approval cannot silently unlock Phase 8 after the state changes.
        """
        override_path = loop_state_path.parent / "review-completion-override.yaml"
        if not override_path.is_file():
            return False, "human approval receipt is missing"
        try:
            override = yaml.safe_load(override_path.read_text(encoding="utf-8"))
            state_hash = hashlib.sha256(loop_state_path.read_bytes()).hexdigest()
        except (OSError, yaml.YAMLError):
            return False, "human approval receipt is unreadable"
        if not isinstance(override, dict):
            return False, "human approval receipt must be a YAML object"

        failure, signature_details = check_receipt_preamble(
            override, _LABEL, REVIEW_APPROVAL_SCHEMA
        )
        if failure is None:
            failure = _review_binding_failure(override, verdict, state_hash, final_artifact_sha256)
        if failure is None:
            failure = check_receipt_identity(override, _LABEL, self._project_dir)
        if failure is None:
            failure = _review_score_failure(override, weighted_score, quality_threshold)
        if failure is None:
            failure = _review_timestamp_failure(override, final_completed_at)
        if failure is not None:
            return False, failure
        return (
            True,
            f"explicit human approval by {override.get('approved_by')} ({signature_details})",
        )
