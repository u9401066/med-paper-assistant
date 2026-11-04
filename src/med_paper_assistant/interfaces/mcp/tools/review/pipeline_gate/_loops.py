"""Review-loop cache and persistence helpers for the pipeline gate tools."""

import json
from pathlib import Path

from med_paper_assistant.infrastructure.persistence.autonomous_audit_loop import (
    AuditLoopConfig,
    AutonomousAuditLoop,
    validate_review_config_policy,
)

# Module-level cache: project path → AutonomousAuditLoop instance
_active_loops: dict[str, AutonomousAuditLoop] = {}


def _loop_cache_key(project_path: Path) -> str:
    return str(Path(project_path).resolve())


def _validated_config(config: dict | None) -> AuditLoopConfig:
    """Build the requested review config and enforce the review policy."""
    # Validate caller-supplied policy before consulting the cache.  Otherwise a
    # low-threshold request could appear to succeed merely because an older loop
    # happened to be cached.
    requested_config = AuditLoopConfig(
        max_rounds=config.get("max_rounds", 3) if config else 3,
        min_rounds=config.get("min_rounds", 2) if config else 2,
        quality_threshold=config.get("quality_threshold", 7.0) if config else 7.0,
        stagnation_rounds=config.get("stagnation_rounds", 2) if config else 2,
        stagnation_delta=config.get("stagnation_delta", 0.3) if config else 0.3,
        context="review",
    )
    policy_errors = validate_review_config_policy(requested_config)
    if policy_errors:
        raise ValueError("; ".join(policy_errors))
    return requested_config


def _persisted_config(loop_file: Path) -> AuditLoopConfig:
    """Load the configuration that produced the persisted review state."""
    try:
        persisted = json.loads(loop_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Persisted review state is unreadable or corrupt") from exc
    state_errors = AutonomousAuditLoop.validate_serialized_state(persisted)
    if state_errors:
        raise ValueError(
            "Persisted review state failed integrity checks: " + "; ".join(state_errors[:3])
        )
    return AuditLoopConfig(**persisted["config"])


def _get_or_create_loop(project_dir: str | Path, config: dict | None = None) -> AutonomousAuditLoop:
    """Get existing loop or create/restore from checkpoint."""

    project_path = Path(project_dir).resolve()
    cache_key = _loop_cache_key(project_path)

    audit_dir = project_path / ".audit"
    loop_file = audit_dir / "audit-loop-review.json"

    requested_config = _validated_config(config)

    # If cached loop is completed and checkpoint file is gone, evict stale cache
    if cache_key in _active_loops:
        cached = _active_loops[cache_key]
        if cached.is_completed and not loop_file.is_file():
            del _active_loops[cache_key]
        else:
            return cached

    # A restored loop must use the persisted configuration that produced its
    # earlier verdicts.  Loading rounds into a fresh default configuration can
    # silently change the state machine after a process restart.
    loop_config = requested_config
    if loop_file.is_file():
        loop_config = _persisted_config(loop_file)

    loop = AutonomousAuditLoop(str(audit_dir), config=loop_config)

    # Try to load from checkpoint
    if loop_file.is_file():
        loop.load()

    _active_loops[cache_key] = loop
    return loop


def _request_loop_rewrite(project_dir: Path, section_list: list[str], reason: str) -> None:
    """Mark the review loop as needing rewrite and evict it from the cache."""
    # Mark the review loop as needing rewrite
    loop = _get_or_create_loop(project_dir)
    if not loop.is_completed:
        loop.request_rewrite(section_list, reason)
    # Evict cached loop so next review starts fresh
    cache_key = _loop_cache_key(project_dir)
    if cache_key in _active_loops:
        del _active_loops[cache_key]


def _reset_loop_state(project_dir: Path) -> None:
    """Reset a cached review loop, or delete the persisted state file."""
    cache_key = _loop_cache_key(project_dir)

    # Reset the loop object if it exists in cache
    if cache_key in _active_loops:
        _active_loops[cache_key].reset()
        del _active_loops[cache_key]
    else:
        # Force-delete the persisted state file
        state_file = Path(project_dir) / ".audit" / "audit-loop-review.json"
        if state_file.is_file():
            state_file.unlink()
