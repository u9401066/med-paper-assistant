"""Shared primitives for durable JSON/YAML state files.

- ``atomic_write_text`` writes via a same-directory temp file + ``os.replace`` so a
  crash mid-write never leaves truncated state behind.
- ``quarantine_corrupt_file`` moves an unreadable state file aside (instead of
  letting callers silently overwrite it with empty state) and logs a warning.
- ``load_json_object`` reads a JSON object, treating missing/invalid content
  as ``None`` without raising.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


def atomic_write_text(path: str | Path, text: str) -> None:
    """Atomically replace ``path`` with ``text`` (UTF-8)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def quarantine_corrupt_file(path: str | Path, reason: object = "") -> Path | None:
    """Rename a corrupt state file to ``<name>.corrupt-<timestamp>``.

    Returns the quarantine path, or ``None`` if the file could not be moved.
    """
    source = Path(path)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    quarantined = source.with_name(f"{source.name}.corrupt-{stamp}")
    try:
        os.replace(source, quarantined)
    except OSError as exc:
        logger.warning("state_quarantine_failed", path=str(source), error=str(exc))
        return None
    logger.warning(
        "state_file_corrupt_quarantined",
        path=str(source),
        quarantined=str(quarantined),
        reason=str(reason),
    )
    return quarantined


def load_json_state(path: str | Path) -> dict[str, Any] | None:
    """Load a JSON-object state file; quarantine it if corrupt, never reset it silently.

    Returns ``None`` when the file is missing, unreadable, or was quarantined.
    """
    source = Path(path)
    if not source.is_file():
        return None
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        logger.warning("state_file_unreadable", path=str(source), error=str(exc))
        return None
    except ValueError as exc:
        quarantine_corrupt_file(source, exc)
        return None
    if not isinstance(data, dict):
        quarantine_corrupt_file(source, "root is not a JSON object")
        return None
    return data


def load_json_object(path: str | Path) -> dict[str, Any] | None:
    """Return the JSON object stored at ``path``, or ``None`` if unavailable/malformed."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None
