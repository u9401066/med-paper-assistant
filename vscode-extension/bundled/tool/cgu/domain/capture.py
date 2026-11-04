"""Capture policy shared by the MCP tool, the CLI and the hook. Standard library only."""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

CHANNELS = ("agent", "hook", "import", "manual")
MAX_PROJECT_CHARS = 100
MAX_BATCH = 200
FAMILY_JACCARD = 0.8
SETTING_ENABLED = "enabled"
SETTING_CONSENT = "consent"
SETTING_EXCLUDED = "excluded_projects"
SETTING_THEMES_MIN_SIZE = "themes_min_size"
DEFAULT_THEME_MIN_SIZE = 3
REASON_NOT_ASKED = "consent_not_asked"
REASON_DISABLED = "disabled"
REASON_EXCLUDED = "excluded_project"
_SEPARATORS = re.compile(r"[\\/]+")
_DRIVE = re.compile(r"[A-Za-z]:")


def capture_gate(
    enabled: bool | None, excluded_projects: Sequence[str], project: str | None
) -> str | None:
    """Why a question must not be recorded, or None when recording is allowed."""
    if enabled is None:
        return REASON_NOT_ASKED
    if not enabled:
        return REASON_DISABLED
    if project is not None and project.casefold() in {p.casefold() for p in excluded_projects}:
        return REASON_EXCLUDED
    return None


def clean_project(value: str | None) -> str | None:
    """The last path segment only: a full path is never stored."""
    if not value:
        return None
    parts = [part for part in _SEPARATORS.split(value.strip()) if part]
    if not parts or _DRIVE.fullmatch(parts[-1]):
        return None
    return parts[-1][:MAX_PROJECT_CHARS]


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def parse_time(value: str) -> datetime:
    """An ISO-8601 time as UTC; a naive time is taken to be UTC. Raises ValueError."""
    parsed = datetime.fromisoformat(value.strip())
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def to_iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def iso_from_epoch_ms(milliseconds: float) -> str:
    return to_iso(datetime.fromtimestamp(milliseconds / 1000.0, tz=UTC))


def utc_now_iso() -> str:
    return to_iso(datetime.now(UTC))
