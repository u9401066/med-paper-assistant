"""Helpers for reading manuscript text during review tools."""

from __future__ import annotations

from pathlib import Path


def read_review_manuscript_content(project_dir: str | Path) -> str:
    """Read manuscript text for review hooks, including section-only drafts."""
    drafts_dir = Path(project_dir) / "drafts"
    if not drafts_dir.is_dir():
        return ""

    manuscript_path = drafts_dir / "manuscript.md"
    if manuscript_path.is_file():
        try:
            return manuscript_path.read_text(encoding="utf-8")
        except OSError:
            return ""

    parts: list[str] = []
    for md_file in sorted(drafts_dir.glob("*.md")):
        if md_file.name.startswith("."):
            continue
        try:
            content = md_file.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if content:
            parts.append(f"<!-- source: {md_file.name} -->\n{content}")

    return "\n\n".join(parts)
