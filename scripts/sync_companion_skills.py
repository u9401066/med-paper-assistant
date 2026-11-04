#!/usr/bin/env python3
"""Sync vendored companion-MCP skills from their pinned submodules.

Some research skills in ``.claude/skills/`` are owned by companion MCP
projects. They are copied verbatim from the Agent Plugin that each pinned
submodule ships, so the tool names in the skills always match the MCP surface
locked in ``mcp-integration-lock.json``. Downstream mirrors (the agent plugin
and the VS Code extension) are regenerated from ``.claude/skills/`` by their
own build scripts.

Usage:
    python scripts/sync_companion_skills.py          # copy from submodules
    python scripts/sync_companion_skills.py --check  # fail if vendored copies drift
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / ".claude" / "skills"


@dataclass(frozen=True)
class CompanionSkills:
    companion: str
    source: Path
    skills: tuple[str, ...]


COMPANION_SKILLS: tuple[CompanionSkills, ...] = (
    CompanionSkills(
        companion="pubmed-search",
        source=ROOT / "integrations" / "pubmed-search-mcp" / "plugins" / "pubmed-search" / "skills",
        skills=(
            "pipeline-persistence",
            "pubmed-export-citations",
            "pubmed-fulltext-access",
            "pubmed-gene-drug-research",
            "pubmed-mcp-tools-reference",
            "pubmed-multi-source-search",
            "pubmed-paper-exploration",
            "pubmed-pico-search",
            "pubmed-quick-search",
            "pubmed-systematic-search",
        ),
    ),
)


def _normalize(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _read_tree(root: Path) -> dict[Path, bytes]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root): _normalize(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _missing_sources() -> list[str]:
    return [
        f"{spec.companion}: {spec.source.relative_to(ROOT).as_posix()}"
        for spec in COMPANION_SKILLS
        if not spec.source.is_dir()
    ]


def find_drift() -> list[str]:
    """Return vendored skill files that differ from the pinned upstream copies."""
    drift: list[str] = []
    for spec in COMPANION_SKILLS:
        for name in spec.skills:
            expected = _read_tree(spec.source / name)
            if not expected:
                drift.append(f"{spec.companion}: upstream skill missing: {name}")
                continue
            actual = _read_tree(SKILLS_DIR / name)
            for rel in sorted(expected.keys() | actual.keys()):
                if expected.get(rel) != actual.get(rel):
                    drift.append(f".claude/skills/{name}/{rel.as_posix()}")
    return drift


def sync() -> list[Path]:
    """Replace each vendored skill directory with its pinned upstream copy."""
    written: list[Path] = []
    for spec in COMPANION_SKILLS:
        for name in spec.skills:
            files = _read_tree(spec.source / name)
            if not files:
                raise SystemExit(f"ERROR: {spec.companion} does not ship skill {name!r}")
            target = SKILLS_DIR / name
            shutil.rmtree(target, ignore_errors=True)
            for rel, data in files.items():
                dest = target / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                written.append(dest.relative_to(ROOT))
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify vendored skills are current")
    args = parser.parse_args(argv)

    missing = _missing_sources()
    if missing:
        print(
            "ERROR: companion submodules are not initialised; "
            "run git submodule update --init --recursive",
            file=sys.stderr,
        )
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return 2

    if args.check:
        drift = find_drift()
        if drift:
            print(
                "ERROR: vendored companion skills are out of date; "
                "run python scripts/sync_companion_skills.py",
                file=sys.stderr,
            )
            for item in drift:
                print(f"  - {item}", file=sys.stderr)
            return 1
        total = sum(len(spec.skills) for spec in COMPANION_SKILLS)
        print(f"OK: {total} vendored companion skills match their pinned upstream")
        return 0

    written = sync()
    print(f"OK: synced {len(written)} files from companion submodules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
