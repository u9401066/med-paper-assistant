"""Phase 7 evidence checks: manuscript hash chain, R1-R6 revalidation, evolution log."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ._types import GateCheck

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def hash_chain_check(
    index: int,
    round_state: dict[str, Any],
    previous_end_hash: str,
    manuscript_hash: str,
) -> tuple[GateCheck, str, str]:
    """Verify one round's start/end hashes; return the check plus both hashes."""
    raw_start_hash = round_state.get("artifact_hash_start")
    raw_end_hash = round_state.get("artifact_hash_end")
    start_hash = raw_start_hash if isinstance(raw_start_hash, str) else ""
    end_hash = raw_end_hash if isinstance(raw_end_hash, str) else ""
    hash_errors: list[str] = []
    if not _HASH_PATTERN.fullmatch(start_hash):
        hash_errors.append("missing or invalid artifact_hash_start")
    if not _HASH_PATTERN.fullmatch(end_hash):
        hash_errors.append("missing or invalid artifact_hash_end")
    if previous_end_hash and start_hash != previous_end_hash:
        hash_errors.append("round start hash does not match the previous round end hash")
    check = GateCheck(
        name=f"review:hash-chain-{index}",
        description=f"Round {index} manuscript hashes form an auditable chain",
        passed=bool(manuscript_hash) and not hash_errors,
        details=(
            "start/end hashes verified"
            if manuscript_hash and not hash_errors
            else "; ".join(hash_errors) or "manuscript missing or unreadable"
        ),
    )
    return check, start_hash, end_hash


def run_round_hooks(
    project_dir: Path,
    index: int,
    round_state: dict[str, Any],
    start_hash: str,
    end_hash: str,
    manuscript_content: str,
) -> tuple[dict[str, Any], str]:
    """Re-run the R1-R6 review hooks; return their results and any failure reason."""
    raw_fixes = round_state.get("fixes", [])
    issues_fixed = (
        sum(1 for fix in raw_fixes if isinstance(fix, dict) and fix.get("success") is True)
        if isinstance(raw_fixes, list)
        else 0
    )
    hook_results: dict[str, Any] = {}
    hook_error = ""
    if manuscript_content:
        try:
            from med_paper_assistant.infrastructure.persistence.review_hooks import (
                ReviewHooksEngine,
            )

            hook_results = ReviewHooksEngine(project_dir).run_all(
                round_num=index,
                issues_fixed=issues_fixed,
                manuscript_changed=(bool(start_hash and end_hash) and start_hash != end_hash),
                manuscript_content=manuscript_content,
            )
        except Exception as exc:
            hook_error = f"hook execution failed: {type(exc).__name__}: {exc}"
    else:
        hook_error = "manuscript missing, empty, or unreadable"
    return hook_results, hook_error


def round_hook_checks(index: int, hook_results: dict[str, Any], hook_error: str) -> list[GateCheck]:
    checks = []
    for hook_id in ("R1", "R2", "R3", "R4", "R5", "R6"):
        result = hook_results.get(hook_id)
        issue_details = []
        if result is not None:
            issue_details = [
                issue.message for issue in result.issues if issue.severity == "CRITICAL"
            ]
        passed = result is not None and not issue_details and (result.passed or bool(result.issues))
        checks.append(
            GateCheck(
                name=f"review:{hook_id.lower()}-{index}",
                description=f"Round {index} {hook_id} review hook revalidation",
                passed=passed,
                details=(
                    "revalidated from current artifacts"
                    if passed
                    else "; ".join(issue_details[:3])
                    or hook_error
                    or f"{hook_id} did not return a result"
                ),
            )
        )
    return checks


def final_artifact_check(rounds: list[dict[str, Any]], manuscript_hash: str) -> GateCheck:
    final_recorded_hash = ""
    if rounds:
        raw_final_hash = rounds[-1].get("artifact_hash_end")
        if isinstance(raw_final_hash, str):
            final_recorded_hash = raw_final_hash
    current_hash_matches = bool(
        manuscript_hash
        and _HASH_PATTERN.fullmatch(final_recorded_hash)
        and final_recorded_hash == manuscript_hash
    )
    return GateCheck(
        name="review:final-artifact-current",
        description="Final reviewed artifact hash matches the current manuscript",
        passed=current_hash_matches,
        details=(
            f"current manuscript sha256={manuscript_hash[:12]}…"
            if current_hash_matches
            else (
                "current manuscript does not match the final reviewed hash "
                f"(recorded={final_recorded_hash[:12] or 'missing'}…, "
                f"current={manuscript_hash[:12] or 'missing'}…)"
            )
        ),
    )


def read_review_events(elog: Path) -> tuple[list[dict[str, Any]], list[str]]:
    review_events: list[dict[str, Any]] = []
    evolution_errors: list[str] = []
    if elog.is_file():
        try:
            for line_number, line in enumerate(
                elog.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if line.strip():
                    entry = json.loads(line)
                    if not isinstance(entry, dict):
                        evolution_errors.append(
                            f"evolution log line {line_number} is not an object"
                        )
                    elif entry.get("event") == "review_round":
                        review_events.append(entry)
        except json.JSONDecodeError as exc:
            evolution_errors.append(f"evolution log contains invalid JSON: {exc}")
        except OSError as exc:
            evolution_errors.append(f"evolution log is unreadable: {exc}")
    return review_events, evolution_errors


def _event_mismatches(index: int, round_state: dict[str, Any], event: dict[str, Any]) -> list[str]:
    errors = []
    if event.get("round") != index:
        errors.append(f"review event {index} has the wrong round number")
    if event.get("verdict") != round_state.get("verdict"):
        errors.append(f"review event {index} verdict does not match state")
    if event.get("scores") != round_state.get("scores"):
        errors.append(f"review event {index} scores do not match state")
    if event.get("weighted_score") != round_state.get("weighted_avg"):
        errors.append(f"review event {index} weighted score does not match state")
    try:
        event_timestamp = event.get("timestamp")
        if not isinstance(event_timestamp, str):
            raise TypeError("timestamp must be a string")
        datetime.fromisoformat(event_timestamp)
    except (TypeError, ValueError):
        errors.append(f"review event {index} timestamp is invalid")
    return errors


def review_events_check(
    elog: Path, rounds: list[dict[str, Any]], rounds_completed: int
) -> GateCheck:
    review_events, evolution_errors = read_review_events(elog)

    if len(review_events) < rounds_completed:
        evolution_errors.append(
            f"only {len(review_events)}/{rounds_completed} review_round events recorded"
        )
    elif rounds_completed:
        for index, (round_state, event) in enumerate(
            zip(rounds, review_events[-rounds_completed:], strict=True),
            start=1,
        ):
            evolution_errors.extend(_event_mismatches(index, round_state, event))

    return GateCheck(
        name="evolution-log:review_events",
        description="evolution-log.jsonl contains state-consistent review_round events",
        passed=rounds_completed > 0 and not evolution_errors,
        details=(
            f"{len(review_events)} state-consistent review_round events"
            if rounds_completed > 0 and not evolution_errors
            else "; ".join(evolution_errors[:5]) or "MISSING"
        ),
    )
