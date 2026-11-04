"""Issue collection for the formatting check (formatting, consistency, medRxiv)."""

from typing import Any

from med_paper_assistant.infrastructure.persistence import ReferenceManager

from ..consistency import (
    ConsistencyReport,
    _check_abbreviations,
    _check_citations,
    _check_figure_table_archive,
    _check_numbers,
    _check_pvalue_format,
    _check_statistical_reporting,
    _check_table_figure_refs,
)
from ..medrxiv_screening import ScreeningReport, run_medrxiv_screening
from ._checks import (
    check_keywords_and_headings,
    check_reference_table_figure_counts,
    check_sections_and_characters,
    check_word_count_and_abstract,
)


def _add_consistency_issues(
    all_content: str, ref_manager: ReferenceManager, issues: list[dict[str, str]]
) -> None:
    consistency_report = ConsistencyReport()
    _check_citations(all_content, ref_manager, consistency_report)
    _check_numbers(all_content, consistency_report)
    _check_abbreviations(all_content, consistency_report)
    _check_table_figure_refs(all_content, consistency_report)
    _check_pvalue_format(all_content, consistency_report)
    _check_statistical_reporting(all_content, consistency_report)

    # Figure/table archive cross-validation
    from med_paper_assistant.infrastructure.persistence import get_project_manager

    pm = get_project_manager()
    project_info = pm.get_project_info()
    project_path = str(project_info["project_path"]) if project_info.get("project_path") else None
    _check_figure_table_archive(all_content, project_path, consistency_report)

    # Convert consistency issues to formatting issues format
    for ci in consistency_report.issues:
        issues.append(
            {
                "severity": ci.severity,
                "item": f"[Consistency] {ci.category}",
                "detail": ci.description + (f" — {ci.suggestion}" if ci.suggestion else ""),
            }
        )


def _add_medrxiv_issues(
    all_content: str, journal_key: str, issues: list[dict[str, str]]
) -> ScreeningReport | None:
    medrxiv_report = None
    if journal_key == "medrxiv":
        medrxiv_report = run_medrxiv_screening(all_content)
        for si in medrxiv_report.issues:
            issues.append(
                {
                    "severity": si.severity,
                    "item": f"[medRxiv] {si.category}",
                    "detail": si.description + (f" — {si.suggestion}" if si.suggestion else ""),
                }
            )
    return medrxiv_report


def analyze_manuscript(
    all_content: str,
    reqs: dict[str, Any],
    journal_key: str,
    ref_manager: ReferenceManager,
) -> tuple[list[dict[str, str]], list[str], ScreeningReport | None]:
    """Run every check and return (issues, passes, medRxiv report)."""
    issues: list[dict[str, str]] = []
    passes: list[str] = []
    check_word_count_and_abstract(all_content, reqs, issues, passes)
    check_reference_table_figure_counts(all_content, reqs, issues, passes)
    check_keywords_and_headings(all_content, reqs, issues, passes)
    check_sections_and_characters(all_content, issues)
    _add_consistency_issues(all_content, ref_manager, issues)
    medrxiv_report = _add_medrxiv_issues(all_content, journal_key, issues)
    return issues, passes, medrxiv_report
