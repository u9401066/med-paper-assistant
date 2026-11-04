"""run_quality_audit tool."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server.mcpserver import Context

from med_paper_assistant.infrastructure.persistence.hook_effectiveness_tracker import (
    HookEffectivenessTracker,
)
from med_paper_assistant.infrastructure.persistence.quality_scorecard import (
    DIMENSIONS,
    QualityScorecard,
)

from ..._shared import (
    log_tool_call,
    log_tool_error,
    log_tool_result,
    report_tool_progress,
)
from .._tool_doc import nested_tool_doc
from ._common import MIN_SCORED_DIMENSIONS, _coerce_project_info, resolve_manuscript_project


def _score_error(score_dict: Any) -> str | None:
    """Return the validation error for a parsed scores payload, if any."""
    if not isinstance(score_dict, dict) or not score_dict:
        return (
            "❌ Scores must be a non-empty JSON object mapping dimension names to numeric scores."
        )

    # Validate score values
    for dim, score in score_dict.items():
        if not isinstance(score, (int, float)):
            return f"❌ Score for '{dim}' must be a number, got {type(score).__name__}"
        if not 0 <= score <= 10:
            return f"❌ Score for '{dim}' must be 0-10, got {score}"

    # Validate minimum dimensions
    standard_scored = [d for d in DIMENSIONS if d in score_dict]
    if len(standard_scored) < MIN_SCORED_DIMENSIONS:
        return (
            f"❌ At least {MIN_SCORED_DIMENSIONS} of the {len(DIMENSIONS)} standard dimensions must be scored.\n"
            f"Scored: {len(standard_scored)} ({', '.join(standard_scored)})\n"
            f"Missing: {', '.join(d for d in DIMENSIONS if d not in score_dict)}\n\n"
            f"Standard dimensions: {', '.join(DIMENSIONS)}"
        )
    return None


def _set_scores(scorecard: QualityScorecard, score_dict: dict[str, Any]) -> None:
    """Write every submitted dimension score (with optional explanation)."""
    for dim, score in score_dict.items():
        explanation = ""
        if isinstance(score, dict):
            explanation = score.get("explanation", "")
            score = score.get("score", score)
        scorecard.set_score(dim, score, explanation)


def _scorecard_lines(slug: str, scorecard: QualityScorecard, sc_data: dict[str, Any]) -> list[str]:
    """TOON lines for the scorecard summary, threshold verdict and weak dimensions."""
    # Build combined audit report (TOON format)
    lines = [
        "status: ok",
        f"project: {slug}",
        f"timestamp: {datetime.now().isoformat()}",
        f"average_score: {sc_data['average_score']}",
        f"min_score: {sc_data.get('min_score', 'N/A')}",
        f"max_score: {sc_data.get('max_score', 'N/A')}",
        f"scored: {sc_data['scored_count']}/{sc_data['total_dimensions']}",
    ]

    if sc_data.get("missing_dimensions"):
        lines.append(f"missing: {','.join(sc_data['missing_dimensions'])}")

    # Threshold check
    meets_6 = scorecard.meets_threshold(6.0)
    meets_7 = scorecard.meets_threshold(7.0)
    if meets_7:
        lines.append("threshold: PASS (>=7.0, ready for Phase 7)")
    elif meets_6:
        lines.append("threshold: WARN (6-7, consider improvement)")
    else:
        lines.append("threshold: FAIL (<6, significant improvement needed)")

    # Weak dimensions
    weak = scorecard.get_weak_dimensions(min_score=6.0)
    if weak:
        lines.append(f"weak_dimensions[{len(weak)}]{{dimension,score,explanation}}:")
        for w in weak:
            expl = w.get("explanation", "").replace(",", ";")
            lines.append(f"  {w['dimension']},{w['score']},{expl}")
    return lines


def _hook_lines(tracker: HookEffectivenessTracker) -> list[str]:
    """TOON lines for the recorded hook statistics and recommendations."""
    lines: list[str] = []
    all_stats = tracker.get_stats()
    if all_stats:
        sorted_hooks = sorted(all_stats.keys())
        lines.append(f"hooks[{len(sorted_hooks)}]{{hook,triggers,passes,fixes,fp_rate}}:")
        for hid in sorted_hooks:
            s = all_stats[hid]
            lines.append(
                f"  {hid},{s['trigger']},{s['pass']},{s['fix']},{s['false_positive_rate']:.0%}"
            )

        # Recommendations
        recs = tracker.get_recommendations()
        if recs:
            lines.append(f"recommendations[{len(recs)}]{{hook,type,reason}}:")
            for r in recs:
                reason = r["reason"].replace(",", ";")
                lines.append(f"  {r['hook_id']},{r['type']},{reason}")
    return lines


def _parse_scores(scores: str) -> tuple[Any, str | None]:
    """Parse the scores JSON and validate it, returning (parsed scores, error)."""
    # Parse scores
    try:
        score_dict = json.loads(scores)
    except json.JSONDecodeError:
        return None, (
            "❌ Invalid scores JSON. Expected format:\n"
            "```json\n"
            '{"citation_quality": 8, "methodology_reproducibility": 7, ...}\n'
            "```"
        )
    return score_dict, _score_error(score_dict)


async def _quality_audit(scores: str, project: Optional[str], ctx: Context | None) -> str:
    """Score the manuscript dimensions and generate the audit reports."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error
    project_info = _coerce_project_info(project_info)

    await report_tool_progress(ctx, 0, 4, "Parsing quality audit scores", end=95)
    score_dict, score_error = _parse_scores(scores)
    if score_error:
        return score_error

    await report_tool_progress(ctx, 1, 4, "Resolving project context", end=95)
    slug = project_info["slug"]
    project_dir = Path(project_info["project_path"])
    audit_dir = project_dir / ".audit"

    # Set quality scores
    await report_tool_progress(ctx, 2, 4, "Generating quality scorecard", end=95)
    scorecard = QualityScorecard(audit_dir)
    _set_scores(scorecard, score_dict)

    # Generate scorecard report
    scorecard.generate_report()
    sc_data = scorecard.get_scorecard()

    # Generate hook effectiveness report
    await report_tool_progress(ctx, 3, 4, "Generating hook effectiveness report", end=95)
    tracker = HookEffectivenessTracker(audit_dir)
    tracker.generate_report()

    lines = _scorecard_lines(slug, scorecard, sc_data)
    lines.extend(_hook_lines(tracker))
    lines.extend(["", "files: .audit/quality-scorecard.md,.audit/hook-effectiveness.md"])

    result = "\n".join(lines)
    await report_tool_progress(ctx, 4, 4, "Quality audit complete")
    log_tool_result(
        "run_quality_audit",
        f"avg={sc_data['average_score']}, dims={sc_data['scored_count']}",
    )
    return result


@nested_tool_doc
async def run_quality_audit(
    scores: str,
    project: Optional[str] = None,
    ctx: Context | None = None,
) -> str:
    """
    DEPRECATED public verb. Prefer `run_quality_checks(action="quality_audit", ...)`.

    🔍 HARD GATE: Run quality audit — set scores and generate reports.

    Call this AFTER Phase 6 (Hook C post-manuscript audit).
    Sets quality scores for manuscript dimensions and generates:
    - quality-scorecard.yaml + quality-scorecard.md
    - hook-effectiveness.md (from recorded hook events)

    The agent MUST call this before validate_phase_gate(6) will PASS.
    Phase 6 gate validates actual score data exists (not just files).

    Args:
        scores: JSON string of dimension scores (0-10), e.g.:
                '{"citation_quality": 8, "methodology_reproducibility": 7,
                  "text_quality": 8.5, "concept_consistency": 9,
                  "format_compliance": 8, "figure_table_quality": 7}'

                Standard dimensions:
                - citation_quality
                - methodology_reproducibility
                - text_quality
                - concept_consistency
                - format_compliance
                - figure_table_quality
        project: Project slug (optional, uses current project)

    Returns:
        Combined audit report with scorecard and hook effectiveness
    """
    log_tool_call("run_quality_audit", {"project": project})
    try:
        return await _quality_audit(scores, project, ctx)
    except Exception as e:
        log_tool_error("run_quality_audit", e)
        return f"❌ Error running quality audit: {e}"
