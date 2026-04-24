"""Regression test: bundled Python mirror must stay byte-identical to source."""

from __future__ import annotations

import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src" / "med_paper_assistant"
BUNDLED_ROOT = ROOT / "vscode-extension" / "bundled" / "tool" / "med_paper_assistant"


def _python_relative_paths(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def test_bundled_python_mirror_matches_source_tree() -> None:
    src_paths = _python_relative_paths(SRC_ROOT)
    bundled_paths = _python_relative_paths(BUNDLED_ROOT)

    assert bundled_paths == src_paths

    mismatches: list[str] = []
    for relative_path in src_paths:
        source_text = (SRC_ROOT / relative_path).read_text(encoding="utf-8")
        bundled_text = (BUNDLED_ROOT / relative_path).read_text(encoding="utf-8")
        if source_text == bundled_text:
            continue

        mismatches.append(
            "".join(
                difflib.unified_diff(
                    source_text.splitlines(keepends=True),
                    bundled_text.splitlines(keepends=True),
                    fromfile=f"src/{relative_path}",
                    tofile=f"bundled/{relative_path}",
                    n=2,
                )
            )
        )

    assert not mismatches, "\n\n".join(mismatches[:3])
