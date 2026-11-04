"""start_review_round tool (Phase 7 state machine)."""

from pathlib import Path
from typing import Any, Optional

from mcp.server.mcpserver import Context

from ..._shared import (
    log_tool_call,
    log_tool_error,
    log_tool_result,
    report_tool_progress,
)
from .._tool_doc import nested_tool_doc
from ._artifacts import _compute_manuscript_hash
from ._common import (
    _require_project_info,
    _sync_to_workspace_state,
    resolve_manuscript_project,
)
from ._loops import _get_or_create_loop


def _sync_round_started(slug: str, round_num: int) -> None:
    """Auto-sync pipeline state when a review round starts (anti-compaction)."""
    # Auto-sync pipeline state (anti-compaction)
    _sync_to_workspace_state(
        slug=slug,
        phase=7,
        gate_passed=False,  # Round started = not yet passed
        next_action=f"Complete review round {round_num}: write review-report-{round_num}.md, author-response-{round_num}.md, then call submit_review_round()",
        current_round=round_num,
        gate_details={
            "schema": "mdpaper.review_round_started.v1",
            "round": round_num,
            "required_artifacts": [
                f".audit/review-report-{round_num}.md",
                f".audit/author-response-{round_num}.md",
                f".audit/equator-compliance-{round_num}.md",
            ],
        },
    )


def _round_task_lines(
    round_num: int, min_rounds: int, max_rounds: int, quality_threshold: float
) -> list[str]:
    """Header and task checklist for a freshly started review round."""
    return [
        f"# 🔄 Review Round {round_num} Started",
        "",
        f"**Min Rounds**: {min_rounds} (mandatory before QUALITY_MET)",
        f"**Max Rounds**: {max_rounds}",
        f"**Quality Threshold**: {quality_threshold}",
        "",
        "## Your Tasks This Round",
        "",
        "1. Read the manuscript carefully",
        "2. Review from 4 perspectives: methodology, domain, statistics, editor",
        f"3. Write `.audit/review-report-{round_num}.md` with YAML front matter",
        f"4. Write `.audit/author-response-{round_num}.md` (ACCEPT/DECLINE each issue)",
        f"5. Write `.audit/equator-compliance-{round_num}.md` (or equator-na-{round_num}.md)",
        "6. **MANDATORY**: Apply fixes to the manuscript using `patch_draft()`",
        "   - Even if no structural issues, MUST strengthen narrative (tighten prose, improve transitions)",
        "   - Manuscript MUST be modified — hash is checked at submit time",
        "7. Call `submit_review_round()` with updated quality scores",
        "",
    ]


def _append_previous_issues(lines: list[str], context: dict[str, Any]) -> None:
    """List unresolved issues carried over from earlier rounds."""
    if context.get("previous_issues"):
        lines.extend(
            [
                "## Unresolved Issues from Previous Rounds",
                "",
            ]
        )
        for issue in context.get("previous_issues", []):
            lines.append(f"- [{issue.get('severity', 'MEDIUM')}] {issue.get('description', 'N/A')}")
        lines.append("")


def _append_score_trend(lines: list[str], context: dict[str, Any]) -> None:
    """Show the previous score per dimension."""
    if context.get("score_trend"):
        lines.extend(
            [
                "## Score Trend",
                "",
                "| Dimension | Previous |",
                "|-----------|----------|",
            ]
        )
        for dim, scores in context.get("score_trend", {}).items():
            prev = scores[-1] if scores else "N/A"
            lines.append(f"| {dim} | {prev} |")


async def _start_round(
    project: Optional[str],
    max_rounds: int,
    min_rounds: int,
    quality_threshold: float,
    ctx: Context | None,
) -> str:
    """Create or resume the review loop, start a round and build its task report."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error

    await report_tool_progress(ctx, 0, 4, "Resolving project context", end=95)
    project_info = _require_project_info(project_info)
    slug = project_info["slug"]
    project_dir = Path(project_info["project_path"])

    await report_tool_progress(ctx, 1, 4, "Initializing review loop", end=95)
    loop = _get_or_create_loop(
        project_dir,
        config={
            "max_rounds": max_rounds,
            "min_rounds": min_rounds,
            "quality_threshold": quality_threshold,
        },
    )

    # Compute manuscript hash BEFORE the round starts
    await report_tool_progress(ctx, 2, 4, "Snapshotting manuscript state", end=95)
    ms_hash = _compute_manuscript_hash(project_dir)

    context = loop.start_round(artifact_hash=ms_hash)
    round_num = context.get("round", 1)

    # Save state immediately
    loop.save()

    _sync_round_started(slug, round_num)

    lines = _round_task_lines(round_num, min_rounds, max_rounds, quality_threshold)
    _append_previous_issues(lines, context)
    _append_score_trend(lines, context)

    report = "\n".join(lines)
    await report_tool_progress(ctx, 4, 4, f"Review round {round_num} ready")
    log_tool_result("start_review_round", f"Round {round_num} started")
    return report


@nested_tool_doc
async def start_review_round(
    project: Optional[str] = None,
    max_rounds: int = 3,
    min_rounds: int = 2,
    quality_threshold: float = 7.0,
    ctx: Context | None = None,
) -> str:
    """
    DEPRECATED public verb. Prefer `pipeline_action(action="start_review", ...)`.

    🔄 Start a new review round (Phase 7 state machine).

    This exposes the AutonomousAuditLoop as an MCP tool.
    The agent MUST call this to begin each review round.
    Cannot skip rounds or fake completion.

    Workflow for Phase 7:
    1. Call start_review_round() → get round context
    2. Perform the actual review (read manuscript, check issues)
    3. Write review-report-{N}.md and author-response-{N}.md
    4. Call submit_review_round() with scores → get verdict
    5. If verdict is CONTINUE → go to step 1
    6. If verdict is QUALITY_MET/MAX_ROUNDS/STAGNATED → Phase 7 done

    Args:
        project: Project slug (optional, uses current project)
        max_rounds: Maximum review rounds (default: 3)
        min_rounds: Minimum review rounds before QUALITY_MET allowed (default: 2)
        quality_threshold: Minimum quality score to pass (default: 7.0)

    Returns:
        Round context with round number, previous issues, and score trends
    """
    log_tool_call(
        "start_review_round",
        {"project": project, "max_rounds": max_rounds, "min_rounds": min_rounds},
    )
    try:
        return await _start_round(project, max_rounds, min_rounds, quality_threshold, ctx)
    except Exception as e:
        log_tool_error("start_review_round", e)
        return f"❌ Error starting review round: {e}"
