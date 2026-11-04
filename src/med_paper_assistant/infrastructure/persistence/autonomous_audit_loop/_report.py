"""Markdown report generation for the audit loop."""

from __future__ import annotations

from typing import Any

from ._base import LoopState
from ._models import AuditLoopConfig, RoundRecord


def _header_lines(config: AuditLoopConfig, rounds: list[RoundRecord]) -> list[str]:
    ctx = config.context
    lines = [
        f"# Autonomous Audit Loop Report: {ctx}",
        "",
        f"- **Context**: {ctx}",
        f"- **Max Rounds**: {config.max_rounds}",
        f"- **Quality Threshold**: {config.quality_threshold}",
        f"- **Rounds Completed**: {len(rounds)}",
    ]
    if rounds:
        final = rounds[-1]
        lines.append(f"- **Final Score**: {final.weighted_avg}")
        lines.append(f"- **Final Verdict**: {final.verdict}")
    lines.append("")
    return lines


def _score_trend_lines(rounds: list[RoundRecord]) -> list[str]:
    lines = ["## Score Trend", ""]

    # Collect all dimension names
    all_dims: set[str] = set()
    for r in rounds:
        all_dims.update(r.scores.keys())
    dims_sorted = sorted(all_dims)

    header = "| Round | " + " | ".join(dims_sorted) + " | Avg | Verdict |"
    sep = "|-------|" + "|".join(["-------"] * len(dims_sorted)) + "|-----|---------|"
    lines.append(header)
    lines.append(sep)

    for r in rounds:
        scores_str = " | ".join(f"{r.scores.get(d, '-')}" for d in dims_sorted)
        lines.append(f"| {r.round_number} | {scores_str} | {r.weighted_avg} | {r.verdict} |")
    lines.append("")
    return lines


def _issue_table_lines(issues: list[dict[str, Any]]) -> list[str]:
    lines = ["### Issues Found", ""]
    lines.append("| # | Hook | Severity | Section | Description | Fixed |")
    lines.append("|---|------|----------|---------|-------------|-------|")
    for i, issue in enumerate(issues):
        fixed = "✅" if issue.get("fixed") else "❌"
        sec = issue.get("section") or "—"
        lines.append(
            f"| {i} | {issue['hook_id']} | {issue['severity']} "
            f"| {sec} | {issue['description']} | {fixed} |"
        )
    lines.append("")
    return lines


def _fix_table_lines(fixes: list[dict[str, Any]]) -> list[str]:
    lines = ["### Fixes Applied", ""]
    lines.append("| Issue # | Strategy | Success | Details |")
    lines.append("|---------|----------|---------|---------|")
    for fix in fixes:
        ok = "✅" if fix.get("success") else "❌"
        lines.append(
            f"| {fix['issue_index']} | {fix['strategy']} | {ok} | {fix.get('details', '')} |"
        )
    lines.append("")
    return lines


def _round_detail_lines(record: RoundRecord) -> list[str]:
    lines = [f"## Round {record.round_number}", ""]
    if record.issues:
        lines.extend(_issue_table_lines(record.issues))
    if record.fixes:
        lines.extend(_fix_table_lines(record.fixes))
    return lines


class ReportMixin(LoopState):
    """Markdown audit report rendering and persistence."""

    # ── Report Generation ──────────────────────────────────────────

    def generate_report(self) -> str:
        """Generate a Markdown audit report."""
        lines = _header_lines(self._config, self._rounds)

        # Score trend table
        if self._rounds:
            lines.extend(_score_trend_lines(self._rounds))

        # Per-round details
        for r in self._rounds:
            lines.extend(_round_detail_lines(r))

        report = "\n".join(lines)

        # Save report to disk
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._report_path.write_text(report, encoding="utf-8")

        return report
