"""Phase gate, heartbeat and project-structure tools."""

from pathlib import Path
from typing import Any, Optional

from mcp.server.mcpserver import Context

from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
    PipelineGateValidator,
)

from ..._shared import (
    log_tool_call,
    log_tool_error,
    log_tool_result,
    report_tool_progress,
)
from .._tool_doc import nested_tool_doc
from ._artifacts import _write_pipeline_completed
from ._common import (
    _ALL_PHASES,
    _PHASE_NAMES,
    _require_project_info,
    _sync_to_workspace_state,
    resolve_manuscript_project,
)


def _sync_gate_result(slug: str, phase: int, result: Any) -> None:
    """Auto-sync pipeline state after a gate check (anti-compaction defense)."""
    failure_names = [c.name for c in result.critical_failures]
    next_phase = (
        _ALL_PHASES[min(_ALL_PHASES.index(phase) + 1, len(_ALL_PHASES) - 1)]
        if result.passed
        else phase
    )
    next_act = (
        f"Proceed to Phase {next_phase} ({_PHASE_NAMES.get(next_phase, '')})"
        if result.passed
        else f"Fix {len(failure_names)} failures in Phase {phase}, then re-validate"
    )
    _sync_to_workspace_state(
        slug=slug,
        phase=phase,
        gate_passed=result.passed,
        gate_failures=failure_names,
        gate_details=result.to_dict(compact=True),
        next_action=next_act,
    )


async def _validate_gate(
    phase: int,
    project: Optional[str],
    response_format: str,
    compact: bool,
    ctx: Context | None,
) -> str:
    """Validate a phase's artifacts, sync the gate result and render the report."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error

    await report_tool_progress(ctx, 0, 3, f"Resolving project context for Phase {phase}", end=95)
    project_info = _require_project_info(project_info)
    slug = project_info["slug"]
    project_dir = Path(project_info["project_path"])

    await report_tool_progress(ctx, 1, 3, f"Validating Phase {phase} artifacts", end=95)
    validator = PipelineGateValidator(project_dir)
    result = validator.validate_phase(phase)

    # Write pipeline-completed marker when Phase 11 passes
    if phase == 11 and result.passed:
        _write_pipeline_completed(project_dir, slug)

    _sync_gate_result(slug, phase, result)

    report = (
        result.to_json(compact=compact)
        if response_format.strip().lower() == "json"
        else result.to_markdown(compact=compact)
    )
    await report_tool_progress(ctx, 3, 3, f"Phase {phase} validation complete")
    log_tool_result(
        "validate_phase_gate", f"Phase {phase}: {'PASSED' if result.passed else 'FAILED'}"
    )
    return report


@nested_tool_doc
async def validate_phase_gate(
    phase: int,
    project: Optional[str] = None,
    response_format: str = "markdown",
    compact: bool = False,
    ctx: Context | None = None,
) -> str:
    """
    DEPRECATED public verb. Prefer `pipeline_action(action="validate_phase", phase=...)`.

    🚧 HARD GATE: Validate all required artifacts for a pipeline phase.

    Call this AFTER completing a phase, BEFORE proceeding to the next.
    Returns PASS only if ALL critical artifacts exist.
    Returns FAIL with specific missing items if incomplete.

    The agent MUST receive PASS before moving to the next phase.
    This is CODE-ENFORCED — cannot be bypassed.

    Phase numbers:
    - 0: Configuration (journal-profile.yaml)
    - 1: Setup (directory structure)
    - 2: Literature (≥10 refs)
    - 3: Concept (concept.md with 🔒 sections)
    - 4: Planning (manuscript plan)
    - 5: Writing (manuscript with all sections)
    - 6: Audit (scorecard + hook effectiveness)
    - 65: Evolution Gate (baseline + evolution log)
    - 7: Autonomous Review (review reports + responses per round)
    - 8: Reference Sync (references section)
    - 9: Export (docx/pdf)
    - 10: Retrospective (D1-D9 analysis)
    - 11: Final Delivery (exports plus optional Git provenance)

    Args:
        phase: Phase number to validate (0-11, use 21 for Phase 2.1 and 65 for Phase 6.5)
        project: Project slug (optional, uses current project)
        response_format: "markdown" or "json"
        compact: If true, return only failing checks

    Returns:
        Markdown report with PASS/FAIL and specific check results
    """
    log_tool_call("validate_phase_gate", {"phase": phase, "project": project})
    try:
        return await _validate_gate(phase, project, response_format, compact, ctx)
    except Exception as e:
        log_tool_error("validate_phase_gate", e)
        return f"❌ Error validating phase gate: {e}"


def _heartbeat_report(status: dict[str, Any]) -> str:
    """Render the pipeline status as a markdown heartbeat report."""
    lines = [
        "# 💓 Pipeline Heartbeat",
        f"**Completion**: {status['completion_pct']}% ({status['phases_passed']}/{status['phases_total']} phases)",
        f"**Critical Failures Remaining**: {status['total_critical_failures']}",
        f"**Timestamp**: {status['timestamp']}",
        "",
        "| Phase | Name | Status | Critical | Warnings |",
        "|-------|------|--------|----------|----------|",
    ]

    for p in status["phases"]:
        status_icon = "✅" if p["passed"] else "❌"
        lines.append(
            f"| {p['phase']} | {p['name']} | {status_icon} | {p['critical_failures']} | {p['warnings']} |"
        )

    # Add details for failing phases
    failing = [p for p in status["phases"] if not p["passed"]]
    if failing:
        lines.extend(["", "## ❌ Failing Phases — Remaining Work", ""])
        for p in failing:
            if p["details"]:
                lines.append(f"### Phase {p['phase']}: {p['name']}")
                for d in p["details"]:
                    lines.append(f"- **{d['check']}**: {d['details']}")
                lines.append("")

    return "\n".join(lines)


def _sync_heartbeat(slug: str, status: dict[str, Any]) -> None:
    """Auto-sync pipeline state from heartbeat (anti-compaction)."""
    failing = [p for p in status["phases"] if not p["passed"]]
    current_phase = failing[0]["phase"] if failing else 11
    _sync_to_workspace_state(
        slug=slug,
        phase=current_phase,
        gate_passed=not failing,
        gate_failures=[f"Phase {p['phase']}" for p in failing[:5]],
        gate_details={
            "schema": "mdpaper.heartbeat.v1",
            "completion_pct": status["completion_pct"],
            "failing_phases": failing[:5],
        },
        next_action=(
            f"Complete Phase {current_phase} ({_PHASE_NAMES.get(current_phase, '')})"
            if failing
            else "Pipeline complete! Run validate_phase_gate(11) for final check."
        ),
    )


@nested_tool_doc
async def pipeline_heartbeat(
    project: Optional[str] = None,
    ctx: Context | None = None,
) -> str:
    """
    DEPRECATED public verb. Prefer `pipeline_action(action="heartbeat")`.

    💓 Pipeline heartbeat — get full status across ALL phases.

    Returns:
    - Overall completion percentage
    - Per-phase pass/fail status
    - Specific missing artifacts for each failing phase
    - Total critical failures remaining

    Call this periodically during pipeline execution to stay on track.
    The result shows EXACTLY what remains to be done — no guessing.

    Args:
        project: Project slug (optional, uses current project)

    Returns:
        Detailed pipeline status report in markdown
    """
    log_tool_call("pipeline_heartbeat", {"project": project})
    try:
        project_info, workflow_error = resolve_manuscript_project(project)
        if workflow_error:
            return workflow_error

        await report_tool_progress(ctx, 0, 3, "Resolving project context", end=95)
        project_info = _require_project_info(project_info)
        slug = project_info["slug"]
        project_dir = Path(project_info["project_path"])

        await report_tool_progress(ctx, 1, 3, "Collecting pipeline status", end=95)
        validator = PipelineGateValidator(project_dir)
        status = validator.get_pipeline_status()

        report = _heartbeat_report(status)
        _sync_heartbeat(slug, status)
        log_tool_result("pipeline_heartbeat", f"{status['completion_pct']}% complete")
        await report_tool_progress(ctx, 3, 3, "Pipeline heartbeat complete")
        return report

    except Exception as e:
        log_tool_error("pipeline_heartbeat", e)
        return f"❌ Error getting pipeline heartbeat: {e}"


@nested_tool_doc
async def validate_project_structure(
    project: Optional[str] = None,
    ctx: Context | None = None,
) -> str:
    """
    🏗️ Validate project file structure integrity.

    Checks required directories, config files, and memory files.
    Works for both new and existing projects.
    Call this after create_project or when resuming work on an existing project.

    Args:
        project: Project slug (optional, uses current project)

    Returns:
        Markdown report of structural checks
    """
    log_tool_call("validate_project_structure", {"project": project})
    try:
        project_info, workflow_error = resolve_manuscript_project(project)
        if workflow_error:
            return workflow_error

        await report_tool_progress(ctx, 0, 2, "Resolving project context", end=95)
        project_info = _require_project_info(project_info)
        project_dir = Path(project_info["project_path"])

        await report_tool_progress(ctx, 1, 2, "Validating project structure", end=95)
        validator = PipelineGateValidator(project_dir)
        result = validator.validate_project_structure()

        report = result.to_markdown()
        await report_tool_progress(ctx, 2, 2, "Project structure validation complete")
        log_tool_result("validate_project_structure", f"{'PASSED' if result.passed else 'FAILED'}")
        return report

    except Exception as e:
        log_tool_error("validate_project_structure", e)
        return f"❌ Error validating project structure: {e}"
