"""Markdown report rendering for the formatting check."""

from typing import Any

from ..medrxiv_screening import ScreeningReport


def count_severities(issues: list[dict[str, str]]) -> tuple[int, int, int]:
    """Return (errors, warnings, info) counts."""
    error_count = sum(1 for i in issues if i["severity"] == "error")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")
    info_count = sum(1 for i in issues if i["severity"] == "info")
    return error_count, warning_count, info_count


def _render_header(journal_name: str, journal_key: str, filenames: list[str]) -> str:
    output = f"# 📐 Manuscript Check: {journal_name}\n\n"
    output += f"**Files:** {', '.join(filenames)}\n"
    output += f"**Journal:** {journal_name} (`{journal_key}`)\n\n"
    return output


def _render_summary(
    passes: list[str], error_count: int, warning_count: int, info_count: int
) -> str:
    output = ""
    output += "## Summary\n\n"
    output += f"- ✅ Passed: {len(passes)}\n"
    output += f"- ❌ Errors: {error_count}\n"
    output += f"- ⚠️ Warnings: {warning_count}\n"
    output += f"- ℹ️ Info: {info_count}\n\n"

    if passes:
        output += "## ✅ Passed\n\n"
        for p in passes:
            output += f"- {p}\n"
        output += "\n"
    return output


def _render_issues(issues: list[dict[str, str]]) -> str:
    output = ""
    if issues:
        output += "## Issues\n\n"
        output += "| Severity | Item | Detail |\n"
        output += "|----------|------|--------|\n"

        icons = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}
        for issue in sorted(
            issues, key=lambda x: {"error": 0, "warning": 1, "info": 2}[x["severity"]]
        ):
            icon = icons[issue["severity"]]
            output += f"| {icon} | {issue['item']} | {issue['detail']} |\n"

        output += "\n"
    return output


def _render_submission(submission_items: list[dict[str, str]]) -> str:
    output = ""
    if submission_items:
        output += "## 📋 Submission Checklist\n\n"
        sub_icons = {
            "pass": "✅",  # nosec B105 - presentation status mapping
            "fail": "❌",
            "warning": "⚠️",
        }
        for item in submission_items:
            icon = sub_icons.get(item["status"], "❓")
            detail = f" — {item['detail']}" if item["detail"] else ""
            output += f"- {icon} {item['item']}{detail}\n"
        output += "\n"
    return output


def _render_medrxiv(medrxiv_report: ScreeningReport | None) -> str:
    output = ""
    if medrxiv_report is not None:
        output += "## 🏥 medRxiv Pre-Submission Screening\n\n"
        output += (
            "Automated checks mirroring medRxiv's two-stage screening process "
            "(in-house + affiliate review).\n\n"
        )
        screening_errors = medrxiv_report.error_count
        screening_warnings = medrxiv_report.warning_count
        screening_total = len(medrxiv_report.issues)
        if screening_total == 0:
            output += "✅ **All medRxiv screening checks passed.**\n\n"
        else:
            output += (
                f"- ❌ Errors: {screening_errors}\n"
                f"- ⚠️ Warnings: {screening_warnings}\n"
                f"- ℹ️ Info: {screening_total - screening_errors - screening_warnings}\n\n"
            )
            if screening_errors > 0:
                output += (
                    "⚠️ **Fix errors before submitting to medRxiv — "
                    "these will likely cause rejection during screening.**\n\n"
                )
    return output


def _render_requirements(reqs: dict[str, Any], error_count: int) -> str:
    output = ""
    output += "## Journal Requirements Overview\n\n"
    output += "| Requirement | Value |\n"
    output += "|-------------|-------|\n"
    output += f"| Word limit (original) | {reqs['word_limit'].get('original', 'N/A')} |\n"
    output += f"| Abstract limit | {reqs.get('abstract_limit', 'N/A')} |\n"
    output += f"| Max references | {reqs.get('references_limit', 'N/A')} |\n"
    output += f"| Max figures | {reqs.get('figures_limit', 'N/A')} |\n"
    output += f"| Max tables | {reqs.get('tables_limit', 'N/A')} |\n"
    output += f"| Keywords | {reqs.get('keywords', 'N/A')} |\n"
    output += f"| Cover letter | {'Required' if reqs.get('cover_letter') else 'Optional'} |\n"
    output += f"| Highlights | {'Required' if reqs.get('highlights') else 'Not required'} |\n"
    output += f"| ORCID | {reqs.get('orcid', 'N/A')} |\n\n"

    if error_count == 0:
        output += "🟢 **No critical formatting errors detected.**\n"
    else:
        output += "🔴 **Fix errors before submission.**\n"
    return output


def render_report(
    journal_key: str,
    filenames: list[str],
    reqs: dict[str, Any],
    passes: list[str],
    issues: list[dict[str, str]],
    submission_items: list[dict[str, str]],
    medrxiv_report: ScreeningReport | None,
    counts: tuple[int, int, int],
) -> str:
    """Render the full markdown report in its fixed section order."""
    error_count, warning_count, info_count = counts
    return (
        _render_header(str(reqs["name"]), journal_key, filenames)
        + _render_summary(passes, error_count, warning_count, info_count)
        + _render_issues(issues)
        + _render_submission(submission_items)
        + _render_medrxiv(medrxiv_report)
        + _render_requirements(reqs, error_count)
    )
