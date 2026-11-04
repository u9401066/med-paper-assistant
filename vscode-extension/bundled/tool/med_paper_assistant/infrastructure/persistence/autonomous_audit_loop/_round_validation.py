"""Per-round checks for ``AutonomousAuditLoop.validate_serialized_state``."""

from __future__ import annotations

import math
from dataclasses import fields
from datetime import datetime
from typing import Any

from ._models import AuditFix, AuditIssue, RoundRecord, RoundVerdict
from ._verdict import VerdictMixin


def _check_scores(
    prefix: str, raw_scores: Any, weights: dict[str, float], errors: list[str]
) -> tuple[dict[str, float], bool]:
    scores: dict[str, float] = {}
    scores_valid = False
    if not isinstance(raw_scores, dict) or set(raw_scores) != set(weights):
        errors.append(f"{prefix} scores must exactly match configured dimensions")
        return scores, scores_valid
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
        scores = {str(dimension): float(score) for dimension, score in raw_scores.items()}
    return scores, scores_valid


def _check_weighted_avg(
    prefix: str, stored_weighted: Any, computed_weighted: float, errors: list[str]
) -> None:
    if (
        isinstance(stored_weighted, bool)
        or not isinstance(stored_weighted, (int, float))
        or not math.isfinite(float(stored_weighted))
        or abs(float(stored_weighted) - round(computed_weighted, 2)) > 1e-6
    ):
        errors.append(f"{prefix} weighted_avg does not match the configured score calculation")


def _issue_values_invalid(raw_issue: dict[Any, Any], valid_severities: set[str]) -> bool:
    hook_id = raw_issue.get("hook_id")
    severity = raw_issue.get("severity")
    description = raw_issue.get("description")
    suggested_fix = raw_issue.get("suggested_fix")
    section = raw_issue.get("section")
    fixed = raw_issue.get("fixed")
    persistent_rounds = raw_issue.get("persistent_rounds")
    return (
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
    )


def _parse_issue(
    prefix: str,
    issue_index: int,
    raw_issue: Any,
    valid_severities: set[str],
    errors: list[str],
) -> AuditIssue | None:
    if not isinstance(raw_issue, dict):
        errors.append(f"{prefix} issue {issue_index} must be a JSON object")
        return None
    issue_fields = {item.name for item in fields(AuditIssue)}
    if set(raw_issue) != issue_fields:
        errors.append(f"{prefix} issue {issue_index} has an invalid schema")
        return None
    if _issue_values_invalid(raw_issue, valid_severities):
        errors.append(f"{prefix} issue {issue_index} has invalid field values")
        return None
    return AuditIssue(
        hook_id=raw_issue["hook_id"],
        severity=raw_issue["severity"],
        description=raw_issue["description"],
        suggested_fix=raw_issue["suggested_fix"],
        section=raw_issue["section"],
        fixed=raw_issue["fixed"],
        persistent_rounds=raw_issue["persistent_rounds"],
    )


def _check_issues(
    prefix: str, raw_issues: Any, valid_severities: set[str], errors: list[str]
) -> tuple[list[Any], list[AuditIssue]]:
    if not isinstance(raw_issues, list):
        errors.append(f"{prefix} issues must be a JSON array")
        raw_issues = []
    current_issues: list[AuditIssue] = []
    for issue_index, raw_issue in enumerate(raw_issues):
        issue = _parse_issue(prefix, issue_index, raw_issue, valid_severities, errors)
        if issue is not None:
            current_issues.append(issue)
    return raw_issues, current_issues


def _fix_values_invalid(raw_fix: dict[Any, Any], issue_count: int) -> bool:
    issue_index = raw_fix.get("issue_index")
    strategy = raw_fix.get("strategy")
    success = raw_fix.get("success")
    details = raw_fix.get("details")
    return (
        isinstance(issue_index, bool)
        or not isinstance(issue_index, int)
        or not 0 <= issue_index < issue_count
        or not isinstance(strategy, str)
        or not strategy.strip()
        or not isinstance(success, bool)
        or not isinstance(details, str)
    )


def _successful_fix_indexes(
    prefix: str, raw_fixes: list[Any], issue_count: int, errors: list[str]
) -> set[int]:
    fix_fields = {item.name for item in fields(AuditFix)}
    successful_fix_indexes: set[int] = set()
    for fix_index, raw_fix in enumerate(raw_fixes):
        if set(raw_fix) != fix_fields:
            errors.append(f"{prefix} fix {fix_index} has an invalid schema")
            continue
        if _fix_values_invalid(raw_fix, issue_count):
            errors.append(f"{prefix} fix {fix_index} has invalid field values")
            continue
        if raw_fix.get("success"):
            successful_fix_indexes.add(raw_fix.get("issue_index"))
    return successful_fix_indexes


def _check_fixes(
    prefix: str, raw_fixes: Any, current_issues: list[AuditIssue], errors: list[str]
) -> list[Any]:
    if not isinstance(raw_fixes, list) or any(not isinstance(item, dict) for item in raw_fixes):
        errors.append(f"{prefix} fixes must be a JSON array of objects")
        return []
    successful_fix_indexes = _successful_fix_indexes(prefix, raw_fixes, len(current_issues), errors)
    fixed_issue_indexes = {
        issue_index for issue_index, issue in enumerate(current_issues) if issue.fixed
    }
    if successful_fix_indexes != fixed_issue_indexes:
        errors.append(f"{prefix} issue fixed flags do not match successful fix records")
    return raw_fixes


def _check_timestamps(prefix: str, raw_round: dict[Any, Any], errors: list[str]) -> None:
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


def _check_verdict(
    verifier: VerdictMixin,
    prefix: str,
    index: int,
    raw_round: dict[Any, Any],
    current_issues: list[AuditIssue],
    computed_weighted: float,
    errors: list[str],
) -> RoundVerdict:
    verifier._current_round = index
    verifier._current_issues = current_issues
    expected_verdict = verifier._determine_verdict(computed_weighted)
    stored_verdict = raw_round.get("verdict")
    if stored_verdict != expected_verdict.value:
        errors.append(
            f"{prefix} verdict={stored_verdict!r} does not match recomputed "
            f"verdict={expected_verdict.value!r}"
        )
    return expected_verdict


def _record_round(
    verifier: VerdictMixin,
    index: int,
    raw_round: dict[Any, Any],
    raw_issues: list[Any],
    raw_fixes: list[Any],
    scores: dict[str, float],
    computed_weighted: float,
    expected_verdict: RoundVerdict,
) -> None:
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


def validate_round(
    verifier: VerdictMixin,
    errors: list[str],
    index: int,
    raw_round: Any,
    weights: dict[str, float],
    valid_severities: set[str],
    terminal_seen: bool,
) -> bool:
    """Validate one serialized round and return the updated ``terminal_seen`` flag."""
    prefix = f"round {index}"
    if not isinstance(raw_round, dict):
        errors.append(f"{prefix} must be a JSON object")
        return terminal_seen
    if raw_round.get("round_number") != index:
        errors.append(f"{prefix} round_number must be {index}")
    if terminal_seen:
        errors.append(f"{prefix} appears after a terminal verdict")

    scores, scores_valid = _check_scores(prefix, raw_round.get("scores"), weights, errors)
    computed_weighted = verifier._compute_weighted_avg(scores) if scores_valid else 0.0
    _check_weighted_avg(prefix, raw_round.get("weighted_avg"), computed_weighted, errors)

    raw_issues, current_issues = _check_issues(
        prefix, raw_round.get("issues"), valid_severities, errors
    )
    raw_fixes = _check_fixes(prefix, raw_round.get("fixes"), current_issues, errors)
    _check_timestamps(prefix, raw_round, errors)

    expected_verdict = _check_verdict(
        verifier, prefix, index, raw_round, current_issues, computed_weighted, errors
    )
    _record_round(
        verifier,
        index,
        raw_round,
        raw_issues,
        raw_fixes,
        scores,
        computed_weighted,
        expected_verdict,
    )
    return expected_verdict is not RoundVerdict.CONTINUE
