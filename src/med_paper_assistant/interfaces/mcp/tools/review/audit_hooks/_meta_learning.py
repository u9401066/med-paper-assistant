"""run_meta_learning tool and its pending-evolution persistence helpers."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from mcp.server.mcpserver import Context

from med_paper_assistant.infrastructure.persistence.hook_effectiveness_tracker import (
    HookEffectivenessTracker,
)
from med_paper_assistant.infrastructure.persistence.meta_learning_engine import (
    MetaLearningEngine,
)
from med_paper_assistant.infrastructure.persistence.pending_evolution_store import (
    EvolutionItem,
    PendingEvolutionStore,
)
from med_paper_assistant.infrastructure.persistence.quality_scorecard import QualityScorecard
from med_paper_assistant.infrastructure.persistence.workspace_state_manager import (
    get_workspace_state_manager,
)

from ..._shared import (
    log_tool_call,
    log_tool_error,
    log_tool_result,
    report_tool_progress,
)
from ..._shared.guidance import build_guidance_hint
from .._tool_doc import nested_tool_doc
from ._common import _coerce_project_info, resolve_manuscript_project


def _summarize_pending_evolutions(
    workspace_root: Path,
    slug: str,
) -> dict:
    """Build a compact project-facing summary of pending evolution items."""
    store = PendingEvolutionStore(workspace_root)
    pending = [item for item in store.get_pending() if item.project in {None, slug}]
    return {
        "schema": "mdpaper.meta_learning_feedback.v1",
        "project": slug,
        "pending_count": len(pending),
        "auto_apply_count": sum(1 for item in pending if item.auto_apply),
        "requires_confirmation_count": sum(1 for item in pending if not item.auto_apply),
        "items": [
            {
                "id": item.id,
                "type": item.type,
                "source": item.source,
                "auto_apply": item.auto_apply,
                "project": item.project or "workspace",
                "summary": str(
                    item.payload.get("lesson") or item.payload.get("reason") or item.payload
                )[:240],
            }
            for item in pending[:50]
        ],
    }


def _write_meta_learning_feedback(
    *,
    project_dir: Path,
    workspace_root: Path,
    slug: str,
) -> dict:
    """Persist meta-learning feedback where the next agent turn will see it."""
    feedback = _summarize_pending_evolutions(workspace_root, slug)
    feedback_path = project_dir / ".audit" / "meta-learning-feedback.yaml"
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    feedback_path.write_text(
        yaml.dump(feedback, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    try:
        wsm = get_workspace_state_manager()
        wsm.record_activity(
            tool_name="run_meta_learning",
            doing=f"Meta-learning complete for {slug}",
            next_action=(
                "Review .audit/meta-learning-feedback.yaml and apply safe pending evolutions"
                if feedback["pending_count"]
                else "Proceed with next pipeline gate"
            ),
            context=[
                f"pending_evolutions={feedback['pending_count']}",
                f"auto_apply={feedback['auto_apply_count']}",
                f"requires_confirmation={feedback['requires_confirmation_count']}",
            ],
        )
    except Exception:  # nosec B110
        pass
    return feedback


def _queue_adjustments(
    store: PendingEvolutionStore, analysis_result: dict, project_slug: str
) -> None:
    """Queue D3 threshold adjustments as pending evolution items."""
    for adj in analysis_result.get("adjustments", []):
        store.add(
            EvolutionItem(
                item_type="threshold_adjustment",
                source="meta_learning_D3",
                project=project_slug,
                auto_apply=bool(adj.get("auto_apply", False)),
                payload={
                    "hook_id": adj.get("hook_id", ""),
                    "parameter": adj.get("parameter", ""),
                    "current_value": adj.get("current_value"),
                    "suggested_value": adj.get("suggested_value"),
                    "reason": adj.get("reason", ""),
                },
            )
        )


def _queue_suggestions(
    store: PendingEvolutionStore, analysis_result: dict, project_slug: str
) -> None:
    """Queue D4-D5 suggestions as pending evolution items."""
    for sug in analysis_result.get("suggestions", []):
        store.add(
            EvolutionItem(
                item_type="suggestion",
                source=f"meta_learning_D4D5_{sug.get('type', '')}",
                project=project_slug,
                auto_apply=not sug.get("requires_confirmation", True),
                payload={
                    "target": sug.get("target", ""),
                    "type": sug.get("type", ""),
                    "reason": sug.get("reason", ""),
                },
            )
        )


def _queue_coverage_gaps(
    store: PendingEvolutionStore, analysis_result: dict, project_slug: str
) -> None:
    """Queue hook/process coverage-gap lessons as pending evolution items."""
    # Coverage gaps: extract from lessons with category "hook_coverage_gap" or "process_gap"
    coverage_categories = {"hook_coverage_gap", "process_gap"}
    for lesson in analysis_result.get("lessons", []):
        if lesson.get("category") in coverage_categories:
            store.add(
                EvolutionItem(
                    item_type="coverage_gap",
                    source=lesson.get("source", "meta_learning_D1"),
                    project=project_slug,
                    auto_apply=False,
                    payload={
                        "category": lesson.get("category", ""),
                        "lesson": lesson.get("lesson", ""),
                        "severity": lesson.get("severity", "info"),
                    },
                )
            )


def _flush_meta_learning_evolutions(
    workspace_root: Path,
    project_slug: str,
    analysis_result: dict,
) -> None:
    """Persist meta-learning results as pending evolution items for cross-conversation pickup."""
    try:
        store = PendingEvolutionStore(workspace_root)
        _queue_adjustments(store, analysis_result, project_slug)
        _queue_suggestions(store, analysis_result, project_slug)
        _queue_coverage_gaps(store, analysis_result, project_slug)
    except Exception:
        # Never let evolution persistence break the main tool
        import structlog

        structlog.get_logger().warning(
            "flush_meta_learning_evolutions.failed",
            project=project_slug,
            exc_info=True,
        )


def _append_evolution_log(audit_dir: Path, result: dict) -> None:
    """Append the meta_learning event to evolution-log.jsonl."""
    elog = audit_dir / "evolution-log.jsonl"
    entry = {
        "schema": "mdpaper.meta_learning_event.v1",
        "event": "meta_learning",
        "timestamp": datetime.now().isoformat(),
        "source_tool": "run_meta_learning",
        "audit_timestamp": result.get("audit_trail", {}).get("timestamp"),
        "run_number": result.get("audit_trail", {}).get("run_number"),
        "adjustments_count": len(result.get("adjustments", [])),
        "lessons_count": len(result.get("lessons", [])),
        "suggestions_count": len(result.get("suggestions", [])),
        "auto_adjustments": sum(
            1 for a in result.get("adjustments", []) if a.get("auto_apply", False)
        ),
    }
    with open(elog, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _adjustment_lines(adjustments: list[dict]) -> list[str]:
    """TOON lines for D1+D3 threshold adjustments."""
    lines: list[str] = []
    if adjustments:
        auto = [a for a in adjustments if a.get("auto_apply")]
        manual = [a for a in adjustments if not a.get("auto_apply")]

        if auto:
            lines.append(
                f"auto_adjustments[{len(auto)}]{{hook,parameter,current,suggested,change_pct,reason}}:"
            )
            for a in auto:
                reason = a["reason"].replace(",", ";")
                lines.append(
                    f"  {a['hook_id']},{a['parameter']},{a['current_value']},{a['suggested_value']},{a.get('change_pct', 'N/A')},{reason}"
                )

        if manual:
            lines.append(f"manual_adjustments[{len(manual)}]{{hook,parameter,reason}}:")
            for a in manual:
                reason = a["reason"].replace(",", ";")
                lines.append(f"  {a['hook_id']},{a['parameter']},{reason}")
    return lines


def _lesson_lines(lessons: list[dict]) -> list[str]:
    """TOON lines for D2 lessons."""
    lines: list[str] = []
    if lessons:
        lines.append(f"lessons[{len(lessons)}]{{severity,category,lesson}}:")
        for lesson in lessons:
            lesson_text = lesson["lesson"].replace(",", ";")
            lines.append(f"  {lesson.get('severity', 'info')},{lesson['category']},{lesson_text}")
    return lines


def _suggestion_lines(suggestions: list[dict]) -> list[str]:
    """TOON lines for D4-D5 suggestions."""
    lines: list[str] = []
    if suggestions:
        lines.append(f"suggestions[{len(suggestions)}]{{target,type,reason}}:")
        for s in suggestions:
            reason = s["reason"].replace(",", ";")
            lines.append(f"  {s['target']},{s['type']},{reason}")
    return lines


def _report_lines(slug: str, result: dict, feedback: dict) -> list[str]:
    """TOON report lines for the meta-learning analysis."""
    lines = [
        "status: ok",
        f"project: {slug}",
        f"timestamp: {datetime.now().isoformat()}",
    ]

    # Adjustments (D1+D3)
    lines.extend(_adjustment_lines(result.get("adjustments", [])))
    # Lessons (D2)
    lines.extend(_lesson_lines(result.get("lessons", [])))
    # Suggestions (D4-D5)
    lines.extend(_suggestion_lines(result.get("suggestions", [])))

    # Audit trail reference
    lines.append(
        "files: .audit/meta-learning-audit.yaml,.audit/evolution-log.jsonl,.audit/meta-learning-feedback.yaml"
    )
    lines.append(
        f"pending_evolutions: {feedback['pending_count']} "
        f"(auto_apply={feedback['auto_apply_count']}, "
        f"requires_confirmation={feedback['requires_confirmation_count']})"
    )
    return lines


def _guided_report(report: str, result: dict) -> str:
    """Log the analysis outcome and append next-step guidance to the report."""
    adjustments = result.get("adjustments", [])
    lessons = result.get("lessons", [])
    suggestions = result.get("suggestions", [])
    log_tool_result(
        "run_meta_learning",
        f"adjustments={len(adjustments)}, lessons={len(lessons)}, suggestions={len(suggestions)}",
    )
    # Proactive guidance: point agent to next steps
    _hints: list[str] = []
    n_confirm = sum(1 for s in suggestions if s.get("requires_confirmation"))
    if n_confirm > 0:
        _hints.append(f"{n_confirm} suggestion(s) require confirmation")
    report = build_guidance_hint(report, next_tool="evolve_constraint", warnings=_hints or None)
    return report


async def _meta_learning(project: Optional[str], ctx: Context | None) -> str:
    """Run the D1-D9 analysis and persist its audit trail and feedback."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error
    project_info = _coerce_project_info(project_info)

    await report_tool_progress(ctx, 0, 4, "Resolving project context", end=95)
    slug = project_info["slug"]
    project_dir = Path(project_info["project_path"])
    audit_dir = project_dir / ".audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    # Initialize infrastructure
    await report_tool_progress(ctx, 1, 4, "Initializing meta-learning engine", end=95)
    tracker = HookEffectivenessTracker(audit_dir)
    scorecard = QualityScorecard(audit_dir)
    # project_dir = projects/<slug>, so .parent.parent = workspace root
    workspace_root = project_dir.parent.parent
    engine = MetaLearningEngine(audit_dir, tracker, scorecard, workspace_root=workspace_root)

    # Run analysis (D1 through D9)
    await report_tool_progress(ctx, 2, 4, "Running D1-D9 meta-learning analysis", end=95)
    result = engine.analyze()

    # Write meta_learning event to evolution-log.jsonl
    _append_evolution_log(audit_dir, result)

    # Flush evolution items to PendingEvolutionStore for cross-conversation persistence
    _flush_meta_learning_evolutions(workspace_root, slug, result)
    feedback = _write_meta_learning_feedback(
        project_dir=project_dir,
        workspace_root=workspace_root,
        slug=slug,
    )

    # Build response (TOON format)
    await report_tool_progress(ctx, 3, 4, "Building meta-learning report", end=95)
    report = "\n".join(_report_lines(slug, result, feedback))
    report = _guided_report(report, result)
    await report_tool_progress(ctx, 4, 4, "Meta-learning complete")
    return report


@nested_tool_doc
async def run_meta_learning(
    project: Optional[str] = None,
    ctx: Context | None = None,
) -> str:
    """
    🧠 HARD GATE: Run D1-D9 meta-learning analysis.

    Call this during Phase 10 (Retrospective).
    Executes the full MetaLearningEngine analysis:
    - D1: Hook effectiveness statistics
    - D2: Quality scorecard analysis
    - D3: Threshold adjustments (auto-apply within ±20%)
    - D4-D5: SKILL.md improvement suggestions
    - D6: Audit trail generation
    - D7: Review loop retrospective
    - D8: EQUATOR/reporting checklist retrospective
    - D9: Tool telemetry and description suggestions

    Also writes a meta_learning event to evolution-log.jsonl.

    The agent MUST call this before validate_phase_gate(10) will PASS.
    Phase 10 gate validates actual meta-learning analysis data exists.

    Args:
        project: Project slug (optional, uses current project)

    Returns:
        Meta-learning analysis summary with adjustments, lessons, and suggestions
    """
    log_tool_call("run_meta_learning", {"project": project})
    try:
        return await _meta_learning(project, ctx)
    except Exception as e:
        log_tool_error("run_meta_learning", e)
        return f"❌ Error running meta-learning analysis: {e}"
