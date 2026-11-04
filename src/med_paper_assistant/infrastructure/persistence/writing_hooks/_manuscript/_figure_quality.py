"""Writing Hooks — C13 figure/table quality, ordering and caption completeness."""

from __future__ import annotations

import re
from typing import Any

import structlog

from .._models import HookIssue, HookResult

logger = structlog.get_logger()

_DATA_PATTERN = r"\b(?:p\s*[<>=]\s*0\.\d|mean|median|OR|HR|RR|CI|SD|IQR|\d+\.\d+%|\d+/\d+)\b"


def _first_mention_order(numbers: list[int]) -> list[int]:
    seen: list[int] = []
    for n in numbers:
        if n not in seen:
            seen.append(n)
    return seen


def _find_captions(content: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    fig_captions = re.findall(
        r"(?:Figure|Fig\.?)\s+(\d+)\.\s*(.+?)(?:\n\n|\n#|\Z)",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    tbl_captions = re.findall(
        r"Table\s+(\d+)\.\s*(.+?)(?:\n\n|\n#|\Z)",
        content,
        re.IGNORECASE | re.DOTALL,
    )
    return fig_captions, tbl_captions


def _quality_stats(
    seen_figs: list[int],
    seen_tbls: list[int],
    captioned_figs: set[int],
    captioned_tbls: set[int],
) -> dict[str, Any]:
    return {
        "figures_referenced": sorted(set(seen_figs)),
        "tables_referenced": sorted(set(seen_tbls)),
        "figures_with_captions": sorted(captioned_figs),
        "tables_with_captions": sorted(captioned_tbls),
        "fig_order_correct": seen_figs == sorted(set(seen_figs), key=seen_figs.index),
        "tbl_order_correct": seen_tbls == sorted(set(seen_tbls), key=seen_tbls.index),
    }


def _ordering_issues(label: str, seen: list[int]) -> list[HookIssue]:
    issues: list[HookIssue] = []
    for i in range(1, len(seen)):
        if seen[i] < seen[i - 1]:
            issues.append(
                HookIssue(
                    hook_id="C13",
                    severity="WARNING",
                    section="manuscript",
                    message=f"{label} {seen[i]} appears before {label} {seen[i - 1]} in text — should be sequential",
                    suggestion=f"Renumber {label.lower()}s so they appear in the order they are first mentioned",
                )
            )
    return issues


def _figure_caption_issues(
    seen_figs: list[int], fig_captions: list[tuple[str, str]], captioned_figs: set[int]
) -> list[HookIssue]:
    issues: list[HookIssue] = []
    for n in set(seen_figs):
        if n not in captioned_figs:
            issues.append(
                HookIssue(
                    hook_id="C13",
                    severity="WARNING",
                    section="manuscript",
                    message=f"Figure {n} referenced in text but no caption found (expected 'Figure {n}. <description>')",
                    suggestion=f"Add a descriptive caption: 'Figure {n}. <Brief description of what the figure shows>'",
                )
            )
            continue
        for num, cap_text in fig_captions:
            if int(num) == n:
                cap_words = len(cap_text.split())
                if cap_words < 10:
                    issues.append(
                        HookIssue(
                            hook_id="C13",
                            severity="WARNING",
                            section="manuscript",
                            message=f"Figure {n} caption too short ({cap_words} words) — should be descriptive (≥10 words)",
                            suggestion="Expand caption to describe axes, key findings, statistical significance, and abbreviations",
                        )
                    )
                break
    return issues


def _table_caption_issues(seen_tbls: list[int], captioned_tbls: set[int]) -> list[HookIssue]:
    return [
        HookIssue(
            hook_id="C13",
            severity="WARNING",
            section="manuscript",
            message=f"Table {n} referenced in text but no caption found (expected 'Table {n}. <description>')",
            suggestion=f"Add a descriptive caption: 'Table {n}. <Brief description of table content>'",
        )
        for n in set(seen_tbls)
        if n not in captioned_tbls
    ]


def _results_visual_issues(sections: dict[str, str]) -> list[HookIssue]:
    results_text = ""
    for name, text in sections.items():
        if name.lower().startswith("result"):
            results_text = text
            break
    if not results_text:
        return []

    has_data = bool(re.search(_DATA_PATTERN, results_text, re.IGNORECASE))
    has_fig_ref = bool(re.search(r"(?:Figure|Fig\.?|Table)\s+\d+", results_text, re.IGNORECASE))
    if not (has_data and not has_fig_ref):
        return []
    return [
        HookIssue(
            hook_id="C13",
            severity="WARNING",
            section="Results",
            message="Results contains statistical data but no figure/table references — consider visual presentation",
            suggestion="Present key data in tables (demographics, outcomes) and figures (trends, comparisons). Add: 'as shown in Table 1' or 'Figure 1 illustrates...'",
        )
    ]


class FigureQualityHooksMixin:
    """C13: figure/table ordering and caption quality."""

    def check_figure_table_quality(
        self,
        content: str,
    ) -> HookResult:
        """
        C13: Verify figure/table quality, ordering, and caption completeness.
        """
        issues: list[HookIssue] = []

        sections = self._parse_sections(content)

        # Check 1: Sequential ordering
        fig_order = [
            int(n) for n in re.findall(r"(?:Figure|Fig\.?)\s+(\d+)", content, re.IGNORECASE)
        ]
        tbl_order = [int(n) for n in re.findall(r"Table\s+(\d+)", content, re.IGNORECASE)]

        seen_figs = _first_mention_order(fig_order)
        issues.extend(_ordering_issues("Figure", seen_figs))
        seen_tbls = _first_mention_order(tbl_order)
        issues.extend(_ordering_issues("Table", seen_tbls))

        # Check 2: Caption presence and quality
        fig_captions, tbl_captions = _find_captions(content)

        captioned_figs = {int(n) for n, _ in fig_captions}
        captioned_tbls = {int(n) for n, _ in tbl_captions}

        issues.extend(_figure_caption_issues(seen_figs, fig_captions, captioned_figs))
        issues.extend(_table_caption_issues(seen_tbls, captioned_tbls))

        # Check 3: Results section should reference figures/tables if it has data claims
        issues.extend(_results_visual_issues(sections))

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = _quality_stats(seen_figs, seen_tbls, captioned_figs, captioned_tbls)

        logger.info(
            "Hook C13 (Figure/Table Quality) complete",
            passed=passed,
            figs=len(set(seen_figs)),
            tbls=len(set(seen_tbls)),
        )
        return HookResult(hook_id="C13", passed=passed, issues=issues, stats=stats)
