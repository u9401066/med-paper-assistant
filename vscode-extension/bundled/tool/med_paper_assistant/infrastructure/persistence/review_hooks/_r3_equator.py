"""R3 — EQUATOR Compliance Gate."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..writing_hooks._models import HookIssue, HookResult
from ._constants import MIN_EQUATOR_ITEMS


class EquatorComplianceMixin:
    """R3: EQUATOR compliance (or N/A justification) file exists and is substantive."""

    _audit_dir: Path

    # Patterns for counting checklist items across diverse agent-produced formats.
    # Each regex is tried against every line; we take the union (de-dup by line)
    # to avoid double-counting when a line matches multiple patterns.
    _ITEM_PATTERNS: list[re.Pattern[str]] = [
        # Markdown checkbox:  - [x] Item  /  * [ ] Item
        re.compile(r"^\s*[-*]\s*\[[ xX✓✗]\]"),
        # Numbered list:  1. Item  /  3) Item
        re.compile(r"^\s*\d+[a-z]?[\.\)]\s"),
        # Markdown pipe table data row (skip header-separator rows like |---|)
        # Matches rows with ≥3 columns that contain real content
        re.compile(r"^\s*\|(?!\s*[-:]+\s*\|)\s*\S.*\|.*\|.*\|"),
        # Emoji status lines:  ✅ Item  /  ❌ Item  /  ⚠️ Item
        re.compile(r"^\s*[✅❌⚠️🔲☑☐✓✗⬜🟢🔴🟡]\s*\S"),
        # Bold numbered:  **1.** Item  /  **2a)** Item
        re.compile(r"^\s*\*\*\d+[a-z]?[\.\)]\*\*\s"),
        # Plain dash/bullet with content (last resort — only if nothing else matched)
        re.compile(r"^\s*[-*]\s+\S"),
    ]

    def _count_equator_items(self, content: str) -> int:
        """Count checklist items in an EQUATOR compliance file.

        Supports multiple formats agents may produce:
        - Markdown checkboxes:  ``- [x] Title``
        - Numbered lists:  ``1. Title``
        - Pipe tables:  ``| 1 | Title | Methods | ✅ |``
        - Emoji status:  ``✅ Title and abstract``
        - Bold numbered:  ``**1.** Title``
        - Plain bullets:  ``- Title: Reported``

        The method tries rich patterns first (checkbox, numbered, table, emoji,
        bold) and only falls back to plain bullets if none of the rich patterns
        matched anything. This prevents over-counting headings/prose as items.

        Args:
            content: Full text of the EQUATOR compliance file.

        Returns:
            Number of checklist items detected.
        """
        lines = content.splitlines()
        matched_lines = self._match_rich_item_lines(lines)

        # If no rich pattern matched anything, try the plain-bullet fallback.
        if not matched_lines:
            matched_lines = self._match_fallback_item_lines(lines)

        # For pipe tables: subtract the header row (first table row).
        # We keep it simple — if table rows are the dominant pattern,
        # remove the first table-matched line (likely the header row).
        table_pat = self._ITEM_PATTERNS[3 - 1]  # index 2 = pipe table pattern
        table_lines = sorted(idx for idx in matched_lines if table_pat.search(lines[idx]))
        if table_lines and len(table_lines) == len(matched_lines):
            # All matches are table rows — first one is the header
            matched_lines.discard(table_lines[0])

        return len(matched_lines)

    def _match_rich_item_lines(self, lines: list[str]) -> set[int]:
        """Indices of lines matching any rich pattern (all but the plain-bullet fallback)."""
        rich_patterns = self._ITEM_PATTERNS[:-1]
        matched_lines: set[int] = set()
        for idx, line in enumerate(lines):
            for pat in rich_patterns:
                if pat.search(line):
                    matched_lines.add(idx)
                    break  # one match per line is enough
        return matched_lines

    def _match_fallback_item_lines(self, lines: list[str]) -> set[int]:
        """Plain-bullet fallback; excludes obvious non-item lines (headings, separators, blank)."""
        fallback_pattern = self._ITEM_PATTERNS[-1]
        heading_re = re.compile(r"^\s*#{1,6}\s")
        matched_lines: set[int] = set()
        for idx, line in enumerate(lines):
            if heading_re.match(line):
                continue
            if fallback_pattern.search(line):
                matched_lines.add(idx)
        return matched_lines

    def check_equator_compliance(self, round_num: int) -> HookResult:
        """
        R3: Verify EQUATOR reporting guideline compliance file exists and is substantive.

        Checks:
        - equator-compliance-{N}.md OR equator-na-{N}.md exists
        - If compliance file: ≥ MIN_EQUATOR_ITEMS checklist items
        - If N/A file: must contain justification
        """
        compliance_path = self._audit_dir / f"equator-compliance-{round_num}.md"
        na_path = self._audit_dir / f"equator-na-{round_num}.md"

        if compliance_path.is_file():
            issues, stats = self._r3_compliance_file(compliance_path)
        elif na_path.is_file():
            issues, stats = self._r3_not_applicable_file(na_path)
        else:
            issues, stats = self._r3_missing_files(round_num)

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="R3", passed=passed, issues=issues, stats=stats)

    def _r3_compliance_file(self, compliance_path: Path) -> tuple[list[HookIssue], dict[str, Any]]:
        issues: list[HookIssue] = []
        content = compliance_path.read_text(encoding="utf-8")
        checklist_items = self._count_equator_items(content)

        if checklist_items < MIN_EQUATOR_ITEMS:
            issues.append(
                HookIssue(
                    hook_id="R3",
                    severity="CRITICAL",
                    section="review",
                    message=f"EQUATOR checklist has only {checklist_items} items (minimum {MIN_EQUATOR_ITEMS})",
                    suggestion="Complete the EQUATOR reporting guideline checklist (CONSORT/STROBE/PRISMA/CARE etc.)",
                )
            )

        return issues, {"type": "compliance", "checklist_items": checklist_items}

    @staticmethod
    def _r3_not_applicable_file(na_path: Path) -> tuple[list[HookIssue], dict[str, Any]]:
        issues: list[HookIssue] = []
        content = na_path.read_text(encoding="utf-8")
        words = len(content.split())
        if words < 30:
            issues.append(
                HookIssue(
                    hook_id="R3",
                    severity="WARNING",
                    section="review",
                    message=f"EQUATOR N/A justification too brief ({words} words) — explain why no reporting guideline applies",
                    suggestion="Provide clear justification (≥30 words) for why no EQUATOR reporting guideline is applicable",
                )
            )
        return issues, {"type": "not_applicable", "justification_words": words}

    @staticmethod
    def _r3_missing_files(round_num: int) -> tuple[list[HookIssue], dict[str, Any]]:
        issue = HookIssue(
            hook_id="R3",
            severity="CRITICAL",
            section="review",
            message=f"Neither equator-compliance-{round_num}.md nor equator-na-{round_num}.md found",
            suggestion="Create equator-compliance-{N}.md with reporting guideline checklist, or equator-na-{N}.md with justification",
        )
        return [issue], {"type": "missing"}
