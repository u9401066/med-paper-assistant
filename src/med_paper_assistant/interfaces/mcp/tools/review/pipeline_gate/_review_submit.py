"""submit_review_round tool (Phase 7 state machine)."""

import json
from pathlib import Path
from typing import Any, Optional

from mcp.server.mcpserver import Context

from med_paper_assistant.infrastructure.persistence.autonomous_audit_loop import (
    AutonomousAuditLoop,
    RoundVerdict,
    Severity,
)

from ..._shared import (
    log_tool_call,
    log_tool_error,
    log_tool_result,
    report_tool_progress,
)
from .._tool_doc import nested_tool_doc
from ._artifacts import _log_review_round_to_evolution, _validate_review_score_schema
from ._common import (
    _require_project_info,
    _sync_to_workspace_state,
    resolve_manuscript_project,
)
from ._loops import _get_or_create_loop
from ._review_enforce import (
    collect_artifact_failures,
    collect_hook_findings,
    rejection_report,
)

_VERDICT_ACTIONS = {
    "continue": "🔄 **CONTINUE** — Start next round with `start_review_round()`",
    "quality_met": "🎉 **QUALITY_MET** — Quality threshold reached! Proceed to Phase 8.",
    "max_rounds": "⚠️ **MAX_ROUNDS** — Quality target was not met. Human decision is required.",
    "stagnated": "⚠️ **STAGNATED** — No improvement detected. Human decision is required.",
    "user_needed": "🛑 **USER_NEEDED** — Critical unresolved issues. Escalate to user.",
    "rewrite_needed": "🔁 **REWRITE_NEEDED** — Section(s) need major rewrite. Call `request_section_rewrite()` to regress to Phase 5.",
}


def _record_round(
    loop: AutonomousAuditLoop,
    project_dir: Path,
    score_dict: dict[str, Any],
    issues_found: int,
    issues_fixed: int,
    current_hash: str,
) -> RoundVerdict:
    """Record issues and fixes, complete the round, persist state and log it."""
    # Record issues and fixes
    for i in range(issues_found):
        loop.record_issue(
            hook_id="review_round",
            severity=Severity.MAJOR,
            description=f"Issue {i + 1} from review round",
            suggested_fix="See author response for details",
        )
    for i in range(min(issues_fixed, issues_found)):
        loop.record_fix(
            issue_index=i,
            strategy="author_revision",
            success=True,
        )

    # Complete the round with manuscript hash
    verdict = loop.complete_round(score_dict, artifact_hash=current_hash)

    # Save state
    loop.save()

    # Log to evolution log
    _log_review_round_to_evolution(project_dir, loop, score_dict, verdict.value)
    return verdict


def _sync_round_state(slug: str, verdict_value: str, status: dict[str, Any]) -> None:
    """Auto-sync pipeline state from the round verdict (anti-compaction)."""
    is_quality_met = verdict_value == "quality_met"
    needs_human_decision = verdict_value in (
        "max_rounds",
        "stagnated",
        "user_needed",
    )
    if verdict_value == "rewrite_needed":
        next_act = "Call request_section_rewrite() to regress to Phase 5 before continuing."
    elif is_quality_met:
        next_act = "Phase 7 complete. Run validate_phase_gate(7), then proceed to Phase 8."
    elif needs_human_decision:
        next_act = (
            "Quality is below the configured target. Escalate to the user; either revise "
            "or have a trusted host/UI record an external confirmation receipt."
        )
    else:
        next_act = f"Start review round {status['current_round'] + 1} with start_review_round()"
    _sync_to_workspace_state(
        slug=slug,
        phase=7,
        gate_passed=is_quality_met,
        next_action=next_act,
        current_round=status["current_round"],
        review_verdict=verdict_value,
        gate_details={
            "schema": "mdpaper.review_round_result.v1",
            "round": status["current_round"],
            "verdict": verdict_value,
            "weighted_score": status.get("latest_weighted_score"),
        },
    )


def _round_report(
    status: dict[str, Any],
    verdict_value: str,
    mod_label: str,
    score_dict: dict[str, Any],
    r_results: dict[str, Any],
    r_warnings: list[str],
) -> str:
    """Markdown summary of a completed review round."""
    lines = [
        f"# Review Round {status['current_round']} Complete",
        "",
        _VERDICT_ACTIONS.get(verdict_value, f"Unknown verdict: {verdict_value}"),
        "",
        f"**Rounds Completed**: {status['current_round']}/{status['max_rounds']}",
        f"**Weighted Score**: {status.get('latest_weighted_score', 'N/A')}",
        "**Manuscript Modified**: " + mod_label,
        "",
        "## Scores This Round",
        "",
        "| Dimension | Score |",
        "|-----------|-------|",
    ]
    for dim, score in score_dict.items():
        lines.append(f"| {dim} | {score} |")

    # Append R-hook summary
    lines.extend(["", "## Review Hook Results (R-series)", ""])
    for hook_id, result in r_results.items():
        status_icon = "✅" if result.passed else "❌"
        lines.append(f"- {status_icon} **{hook_id}**: {'PASS' if result.passed else 'FAIL'}")

    if r_warnings:
        lines.extend(["", "## Warnings", ""])
        for w in r_warnings:
            lines.append(f"- {w}")

    return "\n".join(lines)


def _parse_round_scores(scores: str, loop: AutonomousAuditLoop) -> tuple[dict[str, Any], str]:
    """Parse and schema-check the submitted scores; return (scores, rejection message)."""
    try:
        score_dict = json.loads(scores)
    except json.JSONDecodeError:
        return {}, '❌ Invalid scores JSON. Expected format: {"citation_quality": 8, ...}'

    expected_dimensions = list(loop._config.dimension_weights)
    scores_ok, score_error = _validate_review_score_schema(
        score_dict,
        expected_dimensions,
    )
    if not scores_ok:
        log_tool_result("submit_review_round", "REJECTED: score schema mismatch")
        return {}, "❌ Review score schema mismatch\n\n```json\n" + score_error + "\n```"
    return score_dict, ""


def _check_round(
    loop: AutonomousAuditLoop, project_dir: Path, issues_found: int, issues_fixed: int
) -> tuple[str, dict[str, Any], list[str], str, str]:
    """Run enforcement; return (rejection report, R-hook results, warnings, label, hash)."""
    round_num = loop.current_round_number
    enforcement_failures, start_hash, current_hash = collect_artifact_failures(
        loop, project_dir, round_num, issues_found
    )
    r_results, hook_failures, r_warnings, mod_label = collect_hook_findings(
        project_dir, round_num, issues_fixed, start_hash, current_hash
    )
    enforcement_failures.extend(hook_failures)

    # If enforcement failures, REJECT the submission
    failure_report = ""
    if enforcement_failures:
        failure_report = rejection_report(round_num, enforcement_failures, r_warnings)
        log_tool_result("submit_review_round", "REJECTED: enforcement failures")
    return failure_report, r_results, r_warnings, mod_label, current_hash


async def _submit_round(
    scores: str,
    issues_found: int,
    issues_fixed: int,
    project: Optional[str],
    ctx: Context | None,
) -> str:
    """Verify the round's artifacts, record its scores and report the verdict."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error

    await report_tool_progress(ctx, 0, 5, "Resolving project context", end=95)
    project_info = _require_project_info(project_info)
    slug = project_info["slug"]
    project_dir = Path(project_info["project_path"])

    loop = _get_or_create_loop(project_dir)

    # ── Enforcement: Artifact verification ──
    await report_tool_progress(
        ctx, 1, 5, "Checking review artifacts and manuscript changes", end=95
    )
    failure_report, r_results, r_warnings, mod_label, current_hash = _check_round(
        loop, project_dir, issues_found, issues_fixed
    )
    if failure_report:
        return failure_report

    # ── Enforcement passed — proceed with normal submission ──
    await report_tool_progress(ctx, 2, 5, "Recording fixes and scoring review round", end=95)
    score_dict, score_error = _parse_round_scores(scores, loop)
    if score_error:
        return score_error

    verdict = _record_round(loop, project_dir, score_dict, issues_found, issues_fixed, current_hash)
    status = loop.get_status()

    # Auto-sync pipeline state (anti-compaction)
    await report_tool_progress(ctx, 3, 5, "Evaluating verdict and syncing state", end=95)
    _sync_round_state(slug, verdict.value, status)

    report = _round_report(status, verdict.value, mod_label, score_dict, r_results, r_warnings)
    await report_tool_progress(
        ctx, 5, 5, f"Review round {status['current_round']} submission complete"
    )
    log_tool_result("submit_review_round", f"verdict={verdict.value}")
    return report


@nested_tool_doc
async def submit_review_round(
    scores: str,
    issues_found: int = 0,
    issues_fixed: int = 0,
    project: Optional[str] = None,
    ctx: Context | None = None,
) -> str:
    """
    DEPRECATED public verb. Prefer `pipeline_action(action="submit_review", ...)`.

    ✅ Submit a completed review round with quality scores.

    Call this AFTER writing review-report and author-response files,
    AND after applying fixes to the manuscript.

    ENFORCEMENT:
    - review-report-{N}.md MUST exist
    - author-response-{N}.md MUST exist
    - Manuscript MUST have been modified (hash comparison)
    - issues_found MUST be > 0 (a real review always finds something)

    Args:
        scores: JSON string of dimension scores, e.g.:
                '{"citation_quality": 8, "methodology_reproducibility": 7,
                  "text_quality": 8, "concept_consistency": 9,
                  "format_compliance": 8, "figure_table_quality": 7}'
        issues_found: Number of issues found this round
        issues_fixed: Number of issues fixed this round
        project: Project slug (optional, uses current project)

    Returns:
        Verdict and next steps
    """
    log_tool_call("submit_review_round", {"scores": scores, "issues_found": issues_found})
    try:
        return await _submit_round(scores, issues_found, issues_fixed, project, ctx)
    except Exception as e:
        log_tool_error("submit_review_round", e)
        return f"❌ Error submitting review round: {e}"
