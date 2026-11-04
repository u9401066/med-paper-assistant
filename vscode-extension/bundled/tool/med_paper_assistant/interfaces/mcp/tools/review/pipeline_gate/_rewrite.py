"""request_section_rewrite and reset_review_loop tools."""

from pathlib import Path
from typing import Any, Optional

from med_paper_assistant.infrastructure.persistence.autonomous_audit_loop import (
    RoundVerdict,
)
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
from ._loops import _request_loop_rewrite, _reset_loop_state


def _missing_sections_error(project_dir: Path, section_list: list[str]) -> str | None:
    """Error message when requested sections are absent from the manuscript."""
    # Verify sections exist in manuscript
    manuscript = project_dir / "drafts" / "manuscript.md"
    if manuscript.is_file():
        content = manuscript.read_text(encoding="utf-8")
        missing = [s for s in section_list if f"## {s}" not in content and f"# {s}" not in content]
        if missing:
            return f"❌ Sections not found in manuscript: {', '.join(missing)}"
    return None


def _regression_error(state: dict[str, Any], regression_count: int) -> str | None:
    """Error message when a regression is not allowed right now."""
    if regression_count >= 2:
        return (
            "❌ Maximum regression count (2) reached. "
            "Further regressions require user approval. "
            "Ask the user whether to continue or accept current quality."
        )

    # Check we're in Phase 7
    current_phase = state.get("current_phase", state.get("last_completed_phase", -1))
    if current_phase != 7 and current_phase < 6:
        return (
            f"❌ Regression only allowed from Phase 7. "
            f"Current phase: {current_phase}. "
            f"Use patch_draft() for in-phase fixes."
        )
    return None


def _sync_regression(slug: str, section_list: list[str]) -> None:
    """Auto-sync workspace state after a regression to Phase 5."""
    _sync_to_workspace_state(
        slug=slug,
        phase=5,
        gate_passed=False,
        next_action=f"Rewrite sections: {', '.join(section_list)}. Then re-audit (Phase 6) and re-review (Phase 7).",
        review_verdict=RoundVerdict.REWRITE_NEEDED.value,
    )


def _regression_report(
    reason: str, section_list: list[str], regression_count: int, continuity: dict[str, Any]
) -> str:
    """Markdown confirmation of a pipeline regression."""
    continuity_line = (
        "**Continuity**: ✅ Autonomous — rewrite the sections and continue without asking"
        if continuity.get("auto_resume")
        else "**Continuity**: ⚠️ Human checkpoint required (regression threshold reached)"
    )

    lines = [
        "# 🔁 Pipeline Regression: Phase 7 → Phase 5",
        "",
        f"**Reason**: {reason}",
        f"**Sections to rewrite**: {', '.join(section_list)}",
        f"**Regression count**: {regression_count + 1}/2",
        continuity_line,
        "",
        "## Next Steps",
        "",
        "1. Rewrite the specified sections using `draft_section()` + `write_draft()`",
        "2. Run Hook A/B cascading audit on each rewritten section",
        "3. Call `approve_section(section, action='approve')` for each section",
        "4. Validate Phase 5 gate: `validate_phase_gate(5)`",
        "5. Proceed through Phase 6 (cross-section audit)",
        "6. Phase 7 review will restart with a fresh review loop",
        "",
        "**Other sections are preserved** — only rewrite the specified sections.",
    ]
    return "\n".join(lines)


def _rewrite_sections(sections: str, reason: str, project: Optional[str]) -> str:
    """Validate a regression request, record it and render the confirmation."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error
    project_info = _require_project_info(project_info)
    slug = project_info["slug"]
    project_dir = Path(project_info["project_path"])
    audit_dir = project_dir / ".audit"

    section_list = [s.strip() for s in sections.split(",") if s.strip()]
    if not section_list:
        return "❌ Must specify at least one section to rewrite."

    sections_error = _missing_sections_error(project_dir, section_list)
    if sections_error:
        return sections_error

    # Check regression count limit
    ckpt = CheckpointManager(audit_dir, project_dir=project_dir)
    state = ckpt.load() or {}
    regression_ctx = state.get("regression_context", {})
    regression_count = regression_ctx.get("regression_count", 0)
    regression_error = _regression_error(state, regression_count)
    if regression_error:
        return regression_error

    _request_loop_rewrite(project_dir, section_list, reason)

    # Save regression to checkpoint
    ckpt.save_phase_regression(
        from_phase=7,
        to_phase=5,
        reason=reason,
        sections_to_rewrite=section_list,
    )

    # Surface the continuity decision (autonomous rewrite vs escalation)
    continuity = ckpt.get_continuity_plan()

    _sync_regression(slug, section_list)

    report = _regression_report(reason, section_list, regression_count, continuity)
    log_tool_result("request_section_rewrite", f"regression to Phase 5: {section_list}")
    return report


@nested_tool_doc
def request_section_rewrite(
    sections: str,
    reason: str,
    project: Optional[str] = None,
) -> str:
    """
    🔁 Request a pipeline regression from Phase 7 to Phase 5 for section rewrite.

    When review discovers that a section needs a fundamental rewrite (not just
    patching), call this to regress the pipeline back to Phase 5. Only the
    specified sections will be rewritten; other approved sections are preserved.

    ENFORCEMENT:
    - Only callable during Phase 7 (review phase)
    - Maximum 2 regressions per pipeline run (prevent infinite loops)
    - Creates a pre-regression snapshot of all drafts

    After calling this:
    1. Rewrite the specified sections using write_draft/draft_section
    2. Run Hook A/B on rewritten sections
    3. Call approve_section() for each rewritten section
    4. Proceed through Phase 6 → Phase 7 again

    Args:
        sections: Comma-separated section names to rewrite (e.g., "Methods,Results")
        reason: Why these sections need rewriting
        project: Project slug (optional, uses current project)

    Returns:
        Regression confirmation with instructions
    """
    log_tool_call("request_section_rewrite", {"sections": sections, "reason": reason})
    try:
        return _rewrite_sections(sections, reason, project)
    except Exception as e:
        log_tool_error("request_section_rewrite", e)
        return f"❌ Error requesting section rewrite: {e}"


def _reset_report() -> str:
    """Markdown confirmation of a review-loop reset."""
    lines = [
        "# ✅ Review Loop Reset",
        "",
        "The review state machine has been cleared:",
        "- All round history deleted",
        "- `_in_round` flag cleared",
        "- Module cache entry removed",
        "- State file deleted",
        "",
        "## Next Steps",
        "",
        "Call `start_review_round()` to begin a fresh review cycle.",
    ]
    return "\n".join(lines)


@nested_tool_doc
def reset_review_loop(
    project: Optional[str] = None,
    confirm: bool = False,
) -> str:
    """
    🔄 Reset the review loop state machine (emergency recovery).

    Use this when the review round is stuck (e.g., hash mismatch deadlock,
    _in_round=True preventing start_round, or corrupted state).

    This clears ALL review round history and allows starting fresh.
    Requires confirm=True as a safety check.

    Args:
        project: Project slug (optional, uses current project)
        confirm: Must be True to proceed (safety check)

    Returns:
        Confirmation that the loop was reset
    """
    log_tool_call("reset_review_loop", {"project": project, "confirm": confirm})
    try:
        if not confirm:
            return (
                "⚠️ This will DELETE all review round history and reset the state machine.\n"
                "Call again with `confirm=True` to proceed."
            )

        project_info, workflow_error = resolve_manuscript_project(project)
        if workflow_error:
            return workflow_error
        project_info = _require_project_info(project_info)
        project_dir = Path(project_info["project_path"])

        _reset_loop_state(project_dir)

        report = _reset_report()
        log_tool_result("reset_review_loop", "Loop reset successfully")
        return report

    except Exception as e:
        log_tool_error("reset_review_loop", e)
        return f"❌ Error resetting review loop: {e}"
