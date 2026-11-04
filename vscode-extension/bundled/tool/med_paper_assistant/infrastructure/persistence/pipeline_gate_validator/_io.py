"""Gate helpers for reading project files with fixed failure semantics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

import yaml

UNREADABLE: Final = object()


def read_json_value(path: Path) -> Any:
    """Parse a JSON file; return ``UNREADABLE`` when it cannot be read or decoded.

    The parsed value is returned unvalidated, so callers decide how to treat
    non-object JSON.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return UNREADABLE


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML mapping; a missing, unreadable, invalid or non-mapping file yields ``{}``."""
    if not path.is_file():
        return {}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def read_text_or_empty(path: Path) -> str:
    """Read UTF-8 text, returning an empty string when the file is unreadable."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""
