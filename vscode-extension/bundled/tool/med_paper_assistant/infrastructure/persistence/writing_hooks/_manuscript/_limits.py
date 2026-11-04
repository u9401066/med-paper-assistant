"""Writing Hooks — C6 total word count and C7a figure/table count limits."""

from __future__ import annotations

import re

import structlog

from .._asset_manifest import manifest_numbers
from .._models import HookIssue, HookResult

logger = structlog.get_logger()


def _word_count_severity(deviation_pct: float) -> str | None:
    if deviation_pct > 20:
        return "CRITICAL"
    if deviation_pct > 10:
        return "WARNING"
    return None


def _limit_issue(kind: str, count: int, limit: int) -> HookIssue:
    return HookIssue(
        hook_id="C7a",
        severity="WARNING",
        section="manuscript",
        message=f"{kind} count ({count}) exceeds limit ({limit})",
        suggestion=f"Move excess {kind.lower()}s to supplementary materials",
    )


class CountLimitHooksMixin:
    """C6 / C7a: manuscript size limits."""

    # ── Hook C6: Total Word Count ──────────────────────────────────

    def check_total_word_count(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook C6: Check total manuscript word count against journal limit.

        Per academic convention (ICMJE), counts only body sections.
        """
        issues: list[HookIssue] = []

        limit = self._get_total_word_limit()
        if limit is None:
            return HookResult(
                hook_id="C6",
                passed=True,
                stats={"note": "No total word limit configured"},
            )

        body_info = self._extract_body_word_count(content)
        total_words = body_info["body_words"]

        deviation_pct = ((total_words - limit) / limit) * 100 if limit > 0 else 0

        severity = _word_count_severity(deviation_pct)
        if severity:
            issues.append(
                HookIssue(
                    hook_id="C6",
                    severity=severity,
                    section="manuscript",
                    message=f"Total word count {total_words} exceeds limit {limit} by {deviation_pct:.0f}%",
                    suggestion="Trim the longest section(s) to meet the word limit",
                )
            )

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "body_words": total_words,
            "limit": limit,
            "deviation_pct": round(deviation_pct, 1),
            "body_sections": body_info["breakdown"],
            "excluded_sections": body_info["excluded_sections"],
            "counting_method": "body_only (ICMJE convention)",
        }

        logger.info("Hook C6 complete", passed=passed, body_words=total_words, limit=limit)
        return HookResult(hook_id="C6", passed=passed, issues=issues, stats=stats)

    # ── Hook C7a: Figure/Table Count Limits ────────────────────────

    def _count_figures_tables(self, content: str, issues: list[HookIssue]) -> tuple[int, int]:
        fig_refs = set(re.findall(r"Figure\s+(\d+)", content, re.IGNORECASE))
        tbl_refs = set(re.findall(r"Table\s+(\d+)", content, re.IGNORECASE))

        manifest_entries, manifest_error = self._load_manifest_entries_checked()
        if manifest_error:
            issues.append(self._parse_error_issue("C7a", "results/manifest.json", manifest_error))
        if not manifest_entries:
            return len(fig_refs), len(tbl_refs)

        manifest_figs = manifest_numbers(manifest_entries, "figure")
        manifest_tbls = manifest_numbers(manifest_entries, "table")
        return (
            max(len(fig_refs), len({n for n in manifest_figs if n})),
            max(len(tbl_refs), len({n for n in manifest_tbls if n})),
        )

    def check_figure_table_counts(
        self,
        content: str,
    ) -> HookResult:
        """Hook C7a: Check figure and table counts against journal limits."""
        issues: list[HookIssue] = []

        fig_limit, tbl_limit = self._get_figure_table_limits()
        if fig_limit is None and tbl_limit is None:
            return HookResult(
                hook_id="C7a",
                passed=True,
                stats={"note": "No figure/table limits configured"},
            )

        fig_count, tbl_count = self._count_figures_tables(content, issues)

        if fig_limit is not None and fig_count > fig_limit:
            issues.append(_limit_issue("Figure", fig_count, fig_limit))
        if tbl_limit is not None and tbl_count > tbl_limit:
            issues.append(_limit_issue("Table", tbl_count, tbl_limit))

        passed = len(issues) == 0
        stats = {
            "figure_count": fig_count,
            "table_count": tbl_count,
            "figure_limit": fig_limit,
            "table_limit": tbl_limit,
        }

        logger.info("Hook C7a complete", passed=passed, figs=fig_count, tbls=tbl_count)
        return HookResult(hook_id="C7a", passed=passed, issues=issues, stats=stats)
