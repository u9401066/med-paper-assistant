"""pause_pipeline and resume_pipeline tools."""

from pathlib import Path
from typing import Any, Optional

from med_paper_assistant.infrastructure.persistence.checkpoint_manager import (
    CheckpointManager,
)

from ..._shared import log_tool_call, log_tool_error, log_tool_result
from .._tool_doc import nested_tool_doc
from ._common import (
    _require_project_info,
    _sync_to_workspace_state,
    resolve_manuscript_project,
)


def _pause_report(current_phase: Any, reason: str) -> str:
    """Markdown confirmation that the pipeline is paused."""
    lines = [
        "# ⏸️ Pipeline Paused",
        "",
        f"**Phase at pause**: {current_phase}",
        f"**Reason**: {reason}",
        "",
        "## What You Can Do",
        "",
        "- Edit any draft files in `drafts/`",
        "- Modify `concept.md` or `manuscript-plan.yaml`",
        "- Add or update references",
        "- Take notes in `.memory/`",
        "",
        "## When Ready to Resume",
        "",
        "Call `resume_pipeline()` — the system will:",
        "1. Detect which files changed during the pause",
        "2. Recommend which audits to re-run",
        "3. Continue from the current phase",
    ]
    return "\n".join(lines)


def _append_changes(lines: list[str], changed_files: list[str], phase_at_pause: int) -> None:
    """List the files edited during the pause and the audits worth re-running."""
    lines.extend(
        [
            "",
            "## Modified Files",
            "",
        ]
    )
    for f in changed_files:
        lines.append(f"- `{f}`")
    lines.extend(
        [
            "",
            "## Recommended Actions",
            "",
        ]
    )
    if phase_at_pause >= 5:
        lines.append("1. Re-run `run_writing_hooks()` on modified sections (Hook A/B)")
    if phase_at_pause >= 6:
        lines.append("2. Re-run Phase 6 cross-section audit (Hook C)")
    if phase_at_pause >= 7:
        lines.append("3. Consider restarting Phase 7 review loop")
    lines.append("")
    lines.append("These are recommendations — proceed based on the scope of changes.")


def _resume_report(
    changed: bool, changed_files: list[str], phase_at_pause: int, auto_resume: bool
) -> str:
    """Markdown report for a resumed pipeline."""
    lines = [
        "# ▶️ Pipeline Resumed",
        "",
        f"**Phase**: {phase_at_pause}",
        f"**Drafts modified during pause**: {'Yes' if changed else 'No'}",
        f"**Auto-resume**: {'✅ Safe — continue autonomously' if auto_resume else '⚠️ Review changes first'}",
    ]

    if changed:
        _append_changes(lines, changed_files, phase_at_pause)
    else:
        lines.extend(
            [
                "",
                "No changes detected. **Auto-resume is safe** — continue from where we "
                "left off without manual intervention.",
            ]
        )
    return "\n".join(lines)


def _save_pause(project_dir: Path, reason: str) -> Any:
    """Record the pause and return the phase at which the pipeline was paused."""
    ckpt = CheckpointManager(project_dir / ".audit", project_dir=project_dir)
    ckpt.save_pause(reason=reason)

    state = ckpt.load() or {}
    return state.get("pause_state", {}).get("phase_at_pause", "N/A")


def _resume_state(project_dir: Path) -> tuple[bool, list[str], int, bool]:
    """Resume from the pause: (changed, changed_files, phase_at_pause, auto_resume)."""
    ckpt = CheckpointManager(project_dir / ".audit", project_dir=project_dir)
    resume_result = ckpt.resume_from_pause()

    changed = resume_result["changed"]
    changed_files = resume_result["changed_files"]
    phase_at_pause = resume_result["phase_at_pause"]
    auto_resume = resume_result.get("auto_resume", not changed)
    return changed, changed_files, phase_at_pause, auto_resume


@nested_tool_doc
def pause_pipeline(
    reason: str = "user_requested",
    project: Optional[str] = None,
) -> str:
    """
    ⏸️ Pause the pipeline for manual editing.

    Call this when the user wants to pause the auto-paper pipeline to
    manually edit drafts, review content, or take a break. The system
    records current draft hashes so it can detect changes when resumed.

    After pausing:
    - User can freely edit any draft files
    - User can edit concept.md, manuscript-plan.yaml, etc.
    - When ready, call resume_pipeline() to continue

    Args:
        reason: Why the pipeline is being paused (e.g., "user wants to edit Methods")
        project: Project slug (optional, uses current project)

    Returns:
        Pause confirmation with resume instructions
    """
    log_tool_call("pause_pipeline", {"reason": reason})
    try:
        project_info, workflow_error = resolve_manuscript_project(project)
        if workflow_error:
            return workflow_error
        project_info = _require_project_info(project_info)
        slug = project_info["slug"]
        project_dir = Path(project_info["project_path"])

        current_phase = _save_pause(project_dir, reason)

        _sync_to_workspace_state(
            slug=slug,
            phase=current_phase if isinstance(current_phase, int) else 0,
            gate_passed=False,
            next_action="Pipeline paused. User editing. Call resume_pipeline() when ready.",
        )

        report = _pause_report(current_phase, reason)
        log_tool_result("pause_pipeline", f"paused at phase {current_phase}")
        return report

    except Exception as e:
        log_tool_error("pause_pipeline", e)
        return f"❌ Error pausing pipeline: {e}"


@nested_tool_doc
def resume_pipeline(
    project: Optional[str] = None,
) -> str:
    """
    ▶️ Resume the pipeline after a pause.

    Detects which draft files were modified during the pause and
    recommends appropriate re-validation steps.

    Args:
        project: Project slug (optional, uses current project)

    Returns:
        Resume report with detected changes and recommended actions
    """
    log_tool_call("resume_pipeline", {"project": project})
    try:
        project_info, workflow_error = resolve_manuscript_project(project)
        if workflow_error:
            return workflow_error
        project_info = _require_project_info(project_info)
        slug = project_info["slug"]
        project_dir = Path(project_info["project_path"])

        changed, changed_files, phase_at_pause, auto_resume = _resume_state(project_dir)

        _sync_to_workspace_state(
            slug=slug,
            phase=phase_at_pause if phase_at_pause >= 0 else 0,
            gate_passed=False,
            next_action=(
                f"Re-run audits for changed files: {', '.join(changed_files)}"
                if changed
                else f"Auto-resume safe — continue from Phase {phase_at_pause}"
            ),
        )

        report = _resume_report(changed, changed_files, phase_at_pause, auto_resume)
        log_tool_result("resume_pipeline", f"resumed, changed={changed}")
        return report

    except Exception as e:
        log_tool_error("resume_pipeline", e)
        return f"❌ Error resuming pipeline: {e}"
