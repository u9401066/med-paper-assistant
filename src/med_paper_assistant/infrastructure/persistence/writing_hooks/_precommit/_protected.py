"""Writing Hooks — P5 protected-content check."""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from .._models import HookIssue, HookResult

logger = structlog.get_logger()

_LOCK_MARK = "\U0001f512"  # 🔒


def _protected_blocks(concept_text: str) -> list[tuple[str, str]]:
    """Return (heading, content) for every 🔒-marked heading block."""
    blocks: list[tuple[str, str]] = []
    current_heading: str | None = None
    current_content: list[str] = []

    for line in concept_text.split("\n"):
        heading_match = re.match(r"^#{1,3}\s+(.+)", line)
        if heading_match:
            if current_heading is not None:
                blocks.append((current_heading, "\n".join(current_content).strip()))
            heading_text = heading_match.group(1).strip()
            current_heading = heading_text if _LOCK_MARK in heading_text else None
            current_content = []
        elif current_heading is not None:
            current_content.append(line)

    # Don't forget last block
    if current_heading is not None:
        blocks.append((current_heading, "\n".join(current_content).strip()))
    return blocks


def _is_placeholder_only(block_content: str) -> bool:
    stripped = re.sub(r"\[.*?\]", "", block_content).strip()
    stripped = re.sub(r">\s*\[.*?\]", "", stripped).strip()
    stripped = re.sub(r"^[-*]\s*$", "", stripped, flags=re.MULTILINE).strip()
    return not stripped


def _empty_block_issue(heading: str) -> HookIssue:
    return HookIssue(
        hook_id="P5",
        severity="CRITICAL",
        section="concept.md",
        message=f"Protected block '{heading}' is empty or only has placeholder text",
        suggestion=f"Fill in the content for '{heading}' before proceeding",
    )


class ProtectedContentHooksMixin:
    """P5: 🔒-marked concept.md sections must not be empty."""

    _project_dir: Path

    def check_protected_content(
        self,
        concept_path: Path | None = None,
    ) -> HookResult:
        """
        Hook P5: Verify 🔒-marked sections in concept.md are not empty.

        Scans concept.md for headings containing 🔒, extracts the content
        block under each, strips placeholder text, and flags empty blocks.
        """
        issues: list[HookIssue] = []

        if concept_path is None:
            concept_path = self._project_dir / "concept.md"

        if not concept_path.is_file():
            return HookResult(
                hook_id="P5",
                passed=True,
                stats={"note": "No concept.md found"},
            )

        try:
            concept_text = concept_path.read_text(encoding="utf-8")
        except Exception:
            return HookResult(
                hook_id="P5",
                passed=True,
                stats={"note": "Failed to read concept.md"},
            )

        protected_blocks = _protected_blocks(concept_text)

        empty_blocks: list[str] = []
        for heading, block_content in protected_blocks:
            if _is_placeholder_only(block_content):
                empty_blocks.append(heading)
                issues.append(_empty_block_issue(heading))

        passed = len(empty_blocks) == 0
        stats = {
            "protected_blocks_found": len(protected_blocks),
            "non_empty_count": len(protected_blocks) - len(empty_blocks),
            "empty_blocks": empty_blocks,
        }

        logger.info(
            "Hook P5 complete", passed=passed, blocks=len(protected_blocks), empty=len(empty_blocks)
        )
        return HookResult(hook_id="P5", passed=passed, issues=issues, stats=stats)
