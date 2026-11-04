"""Vendored companion skills must match the pinned companion MCP surface."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sync_companion_skills  # noqa: E402


def test_vendored_companion_skills_match_pinned_upstream() -> None:
    drift = sync_companion_skills.find_drift()

    assert drift == [], "run python scripts/sync_companion_skills.py:\n" + "\n".join(drift)


def test_vendored_skills_are_distinct_and_exist_upstream() -> None:
    names = [name for spec in sync_companion_skills.COMPANION_SKILLS for name in spec.skills]

    assert len(names) == len(set(names))
    for spec in sync_companion_skills.COMPANION_SKILLS:
        for name in spec.skills:
            assert (spec.source / name / "SKILL.md").is_file(), name
