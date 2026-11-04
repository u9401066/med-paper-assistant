"""Config-section checks for ``AutonomousAuditLoop.validate_serialized_state``."""

from __future__ import annotations

import math
from dataclasses import fields
from typing import Any

from ._models import AuditLoopConfig


def build_config(raw_config: dict[str, Any], errors: list[str]) -> AuditLoopConfig | None:
    """Build the config, appending field-set errors; ``None`` means it is unusable."""
    config_fields = {item.name for item in fields(AuditLoopConfig)}
    missing_config = sorted(config_fields - raw_config.keys())
    unknown_config = sorted(raw_config.keys() - config_fields)
    if missing_config:
        errors.append(f"audit loop config missing fields: {', '.join(missing_config)}")
    if unknown_config:
        errors.append(f"audit loop config has unknown fields: {', '.join(unknown_config)}")

    try:
        return AuditLoopConfig(
            **{name: raw_config[name] for name in config_fields if name in raw_config}
        )
    except (TypeError, ValueError) as exc:
        errors.append(f"audit loop config is invalid: {exc}")
        return None


def _check_round_limits(config: AuditLoopConfig, errors: list[str]) -> None:
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


def _check_thresholds(config: AuditLoopConfig, errors: list[str]) -> None:
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


def _check_severities_and_context(
    config: AuditLoopConfig, valid_severities: set[str], errors: list[str]
) -> None:
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


def _has_positive_numeric_weights(weights: Any) -> bool:
    if not (isinstance(weights, dict) and bool(weights)):
        return False
    for name, weight in weights.items():
        if (
            not isinstance(name, str)
            or not name
            or isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(float(weight))
            or float(weight) <= 0
        ):
            return False
    return True


def _check_dimension_weights(config: AuditLoopConfig, errors: list[str]) -> dict[str, float]:
    weights = config.dimension_weights
    if not _has_positive_numeric_weights(weights):
        errors.append("config.dimension_weights must contain positive numeric weights")
        return {}
    if abs(sum(float(weight) for weight in weights.values()) - 1.0) > 1e-6:
        errors.append("config.dimension_weights must sum to 1.0")
    return weights


def check_config_values(
    config: AuditLoopConfig, valid_severities: set[str], errors: list[str]
) -> dict[str, float]:
    """Validate each config field in order; return the usable dimension weights."""
    _check_round_limits(config, errors)
    _check_thresholds(config, errors)
    _check_severities_and_context(config, valid_severities, errors)
    return _check_dimension_weights(config, errors)
