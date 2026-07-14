"""Helpers for locating bundled MedPaper templates.

Templates may live in three supported layouts:
- repository checkout: ``<repo>/templates``
- VSIX bundle: ``<extension>/templates``
- installed wheel: ``med_paper_assistant/templates`` package data
"""

from __future__ import annotations

import os
from pathlib import Path


def _looks_like_templates_dir(path: Path) -> bool:
    """Return True when a directory contains the expected template catalog."""
    return path.is_dir() and (
        (path / "journal-profile.template.yaml").is_file()
        or (path / "csl" / "vancouver.csl").is_file()
        or any(path.glob("*.docx"))
    )


def get_templates_dir() -> Path:
    """Locate MedPaper's built-in templates directory across install surfaces."""
    env_dir = os.getenv("MEDPAPER_TEMPLATES_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "templates"
        if _looks_like_templates_dir(candidate):
            return candidate

    # Last-resort fallback keeps error messages deterministic for sparse installs.
    return current.parents[1] / "templates"


__all__ = ["get_templates_dir"]
