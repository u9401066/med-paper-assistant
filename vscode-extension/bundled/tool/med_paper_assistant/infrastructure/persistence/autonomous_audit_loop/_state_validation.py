"""Serialized-state validation entrypoint for ``AutonomousAuditLoop``."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._config_validation import build_config, check_config_values
from ._models import AuditLoopConfig, Severity
from ._policy import validate_review_config_policy
from ._round_validation import validate_round

if TYPE_CHECKING:
    from .engine import AutonomousAuditLoop


def _validate_rounds(
    loop_cls: type[AutonomousAuditLoop],
    raw_rounds: list[Any],
    config: AuditLoopConfig,
    weights: dict[str, float],
    valid_severities: set[str],
    errors: list[str],
) -> bool:
    """Replay every round through a verifier; return whether a terminal verdict was seen."""
    verifier = loop_cls(Path("."), config=config)
    terminal_seen = False
    for index, raw_round in enumerate(raw_rounds, start=1):
        terminal_seen = validate_round(
            verifier, errors, index, raw_round, weights, valid_severities, terminal_seen
        )
    return terminal_seen


def _check_final_flags(
    data: dict[Any, Any], raw_rounds: list[Any], terminal_seen: bool, errors: list[str]
) -> None:
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


def _validate_config_section(
    data: dict[Any, Any], errors: list[str]
) -> tuple[AuditLoopConfig | None, dict[str, float], set[str]]:
    """Validate ``config``; a ``None`` config means ``errors`` is already final."""
    raw_config = data.get("config")
    if not isinstance(raw_config, dict):
        errors.append("audit loop config must be a JSON object")
        return None, {}, set()

    config = build_config(raw_config, errors)
    if config is None:
        return None, {}, set()

    valid_severities = {severity.value for severity in Severity}
    weights = check_config_values(config, valid_severities, errors)
    errors.extend(validate_review_config_policy(config))
    return config, weights, valid_severities


def validate_serialized_state(loop_cls: type[AutonomousAuditLoop], data: Any) -> list[str]:
    """Recompute persisted scores and verdicts instead of trusting JSON labels."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["audit loop state must be a JSON object"]
    if data.get("version") != 1:
        errors.append("audit loop version must be 1")

    config, weights, valid_severities = _validate_config_section(data, errors)
    if config is None or errors:
        return errors

    raw_rounds = data.get("rounds")
    if not isinstance(raw_rounds, list):
        return [*errors, "audit loop rounds must be a JSON array"]
    if isinstance(config.max_rounds, int) and len(raw_rounds) > config.max_rounds:
        errors.append(
            f"audit loop contains {len(raw_rounds)} rounds, above max_rounds={config.max_rounds}"
        )

    terminal_seen = _validate_rounds(
        loop_cls, raw_rounds, config, weights, valid_severities, errors
    )
    _check_final_flags(data, raw_rounds, terminal_seen, errors)
    return errors
