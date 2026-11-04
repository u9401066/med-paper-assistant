"""Enforcement checks that gate a review round submission."""

from pathlib import Path
from typing import Any

from med_paper_assistant.infrastructure.persistence.autonomous_audit_loop import (
    AutonomousAuditLoop,
)

from .._manuscript import read_review_manuscript_content
from ._artifacts import _compute_manuscript_hash, _count_review_report_issues


def _missing_file_failures(audit_dir: Path, round_num: int) -> list[str]:
    """Review report and author response must exist before submitting."""
    enforcement_failures: list[str] = []

    # Check review-report exists
    review_report = audit_dir / f"review-report-{round_num}.md"
    if not review_report.is_file():
        enforcement_failures.append(
            f"❌ Missing `.audit/review-report-{round_num}.md` — "
            "write the review report before submitting"
        )

    # Check author-response exists
    author_response = audit_dir / f"author-response-{round_num}.md"
    if not author_response.is_file():
        enforcement_failures.append(
            f"❌ Missing `.audit/author-response-{round_num}.md` — "
            "write the author response before submitting"
        )
    return enforcement_failures


def _manuscript_hashes(loop: AutonomousAuditLoop, project_dir: Path) -> tuple[str, str]:
    """Return (hash at round start, current hash) of the review target."""
    current_hash = _compute_manuscript_hash(project_dir)
    start_hash = getattr(loop, "_artifact_hash_start", "")
    # Also check round records for start hash
    if not start_hash and loop._rounds:
        # Fallback: recover from last completed round's end hash
        last_round = loop._rounds[-1]
        if last_round.artifact_hash_end:
            start_hash = last_round.artifact_hash_end
    return start_hash, current_hash


def _unchanged_manuscript_failure(
    project_dir: Path, start_hash: str, current_hash: str
) -> list[str]:
    """A review must produce an actual manuscript change."""
    failures: list[str] = []
    if start_hash and current_hash and start_hash == current_hash:
        # List which files were hashed for debugging
        drafts_dir = project_dir / "drafts"
        hashed_files = (
            sorted(f.name for f in drafts_dir.glob("*.md")) if drafts_dir.is_dir() else []
        )
        failures.append(
            "❌ Manuscript NOT modified — hash unchanged since round start. "
            "A review MUST produce actual changes (use `patch_draft()` to apply fixes). "
            "Even if no structural issues exist, strengthen narrative, tighten prose, "
            "or improve transitions.\n"
            f"   Files hashed: {', '.join(hashed_files) or '(none)'}.\n"
            f"   Start hash: {start_hash[:12]}…  Current hash: {current_hash[:12]}…\n"
            "   If stuck, call `reset_review_loop(confirm=True)` to reset the state machine."
        )
    return failures


def _issues_found_failures(audit_dir: Path, round_num: int, issues_found: int) -> list[str]:
    """issues_found must be realistic and consistent with the review report."""
    failures: list[str] = []
    review_report = audit_dir / f"review-report-{round_num}.md"
    # Check issues_found is realistic
    if issues_found == 0:
        # Cross-check with review-report if it exists
        if review_report.is_file():
            report_counts = _count_review_report_issues(audit_dir, round_num)
            total_in_report = sum(report_counts.values())
            if total_in_report > 0:
                failures.append(
                    f"❌ issues_found=0 but review-report-{round_num}.md contains "
                    f"{total_in_report} issues ({report_counts}). "
                    f"Set issues_found={total_in_report} and fix the accepted ones."
                )
        else:
            failures.append(
                "⚠️ issues_found=0 is suspicious — a thorough review almost always "
                "finds at least narrative improvements. Ensure you reviewed carefully."
            )
    return failures


def collect_artifact_failures(
    loop: AutonomousAuditLoop, project_dir: Path, round_num: int, issues_found: int
) -> tuple[list[str], str, str]:
    """Artifact verification: returns (failures, start hash, current hash)."""
    audit_dir = project_dir / ".audit"
    failures = _missing_file_failures(audit_dir, round_num)
    start_hash, current_hash = _manuscript_hashes(loop, project_dir)
    failures.extend(_unchanged_manuscript_failure(project_dir, start_hash, current_hash))
    failures.extend(_issues_found_failures(audit_dir, round_num, issues_found))
    return failures, start_hash, current_hash


def _modification_status(start_hash: str, current_hash: str) -> tuple[bool, str]:
    """Whether the manuscript changed this round, plus a report label."""
    if start_hash and current_hash:
        manuscript_modified = start_hash != current_hash
        mod_label = "✅ (hash changed)" if manuscript_modified else "❌ (hash unchanged)"
    else:
        manuscript_modified = True  # assume modified if hashes unavailable
        mod_label = "⚠️ (hash unavailable — assumed modified)"
    return manuscript_modified, mod_label


def _run_review_hooks(
    project_dir: Path, round_num: int, issues_fixed: int, manuscript_modified: bool
) -> dict[str, Any]:
    """Run the R-series review hooks against the manuscript."""
    from med_paper_assistant.infrastructure.persistence.review_hooks import (
        ReviewHooksEngine,
    )

    review_engine = ReviewHooksEngine(project_dir)
    manuscript_content = read_review_manuscript_content(project_dir)

    return review_engine.run_all(
        round_num=round_num,
        issues_fixed=issues_fixed,
        manuscript_changed=manuscript_modified,
        manuscript_content=manuscript_content,
    )


def _classify_hook_issues(r_results: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Split hook issues into blocking failures and warnings."""
    failures: list[str] = []
    r_warnings: list[str] = []
    for hook_id, result in r_results.items():
        if not result.passed:
            for issue in result.issues:
                if issue.severity == "CRITICAL":
                    failures.append(
                        f"❌ [{hook_id}] {issue.message}"
                        + (f" — {issue.suggestion}" if issue.suggestion else "")
                    )
                elif issue.severity == "WARNING":
                    r_warnings.append(
                        f"⚠️ [{hook_id}] {issue.message}"
                        + (f" — {issue.suggestion}" if issue.suggestion else "")
                    )
        else:
            # Even passing hooks may have warnings
            for issue in result.issues:
                if issue.severity == "WARNING":
                    r_warnings.append(
                        f"⚠️ [{hook_id}] {issue.message}"
                        + (f" — {issue.suggestion}" if issue.suggestion else "")
                    )
    return failures, r_warnings


def collect_hook_findings(
    project_dir: Path, round_num: int, issues_fixed: int, start_hash: str, current_hash: str
) -> tuple[dict[str, Any], list[str], list[str], str]:
    """R-series content-quality enforcement: (results, failures, warnings, label)."""
    manuscript_modified, mod_label = _modification_status(start_hash, current_hash)
    r_results = _run_review_hooks(project_dir, round_num, issues_fixed, manuscript_modified)
    hook_failures, r_warnings = _classify_hook_issues(r_results)
    return r_results, hook_failures, r_warnings, mod_label


def rejection_report(round_num: int, enforcement_failures: list[str], r_warnings: list[str]) -> str:
    """Markdown report for a rejected submission."""
    failure_lines = [
        f"# 🚫 Review Round {round_num} Submission REJECTED\n",
        "The following enforcement checks failed:\n",
        *[f"- {f}" for f in enforcement_failures],
    ]
    if r_warnings:
        failure_lines.extend(
            [
                "\n## Warnings (address if possible)\n",
                *[f"- {w}" for w in r_warnings],
            ]
        )
    failure_lines.append("\nFix these issues and call `submit_review_round()` again.")
    return "\n".join(failure_lines)
