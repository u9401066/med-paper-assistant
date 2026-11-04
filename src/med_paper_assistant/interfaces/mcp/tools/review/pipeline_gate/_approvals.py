"""approve_section, approve_concept_review and approve_review_completion tools."""

from pathlib import Path
from typing import Optional

from med_paper_assistant.infrastructure.persistence.checkpoint_manager import (
    CheckpointManager,
)
from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
    PipelineGateValidator,
)

from ..._shared import log_tool_call, log_tool_error, log_tool_result
from .._tool_doc import nested_tool_doc
from ._common import _require_project_info, resolve_manuscript_project

_CONCEPT_APPROVAL_REFUSAL = "\n".join(
    [
        "# 🚫 Human Approval Cannot Be Minted by MCP",
        "",
        "The autonomous Agent and this MCP share the same authority; ",
        "`approved_by='human'` is therefore not acceptance evidence.",
        "A trusted host/UI must create `concept-review-override.yaml` ",
        "with schema `mdpaper.concept_review_override.v3`, the current ",
        "concept artifact/review hashes, and an Ed25519 signature. ",
        "Trusted public keys come only from ",
        "`MDPAPER_APPROVAL_ED25519_PUBLIC_KEYS`.",
    ]
)


_REVIEW_APPROVAL_REFUSAL = "\n".join(
    [
        "# 🚫 Human Approval Cannot Be Minted by MCP",
        "",
        "The autonomous Agent and this MCP share the same authority; ",
        "`approved_by='human'` is therefore not acceptance evidence.",
        "A trusted host/UI must create `review-completion-override.yaml` ",
        "with schema `mdpaper.review_completion_override.v3`, the current ",
        "manuscript/loop hashes, and an Ed25519 signature. ",
        "Trusted public keys come only from ",
        "`MDPAPER_APPROVAL_ED25519_PUBLIC_KEYS`.",
    ]
)


def _section_missing_error(project_dir: Path, section: str) -> str | None:
    """Error message when the section is absent from the manuscript."""
    # Verify section exists in manuscript
    manuscript = project_dir / "drafts" / "manuscript.md"
    if manuscript.is_file():
        content = manuscript.read_text(encoding="utf-8")
        if f"## {section}" not in content and f"# {section}" not in content:
            return f"❌ Section '{section}' not found in manuscript."
    return None


def _save_section_decision(
    ckpt: CheckpointManager, section: str, action: str, feedback: str
) -> list[str]:
    """Persist the approval decision and return the opening report lines."""
    if action == "approve":
        ckpt.save_section_progress(
            section=section,
            approval_status="approved",
        )
        lines = [
            f"# ✅ Section Approved: {section}",
            "",
            "The section has been marked as approved.",
            "You can proceed to the next section in the writing order.",
            "",
            "## Current Approval Status",
            "",
        ]
    else:
        ckpt.save_section_progress(
            section=section,
            approval_status="revision_requested",
            user_feedback=feedback,
        )
        lines = [
            f"# ✏️ Revision Requested: {section}",
            "",
            f"**Feedback**: {feedback}",
            "",
            "## Next Steps",
            "",
            f"1. Apply the feedback to the {section} section using `patch_draft()` or `write_draft()`",
            "2. Re-run `run_writing_hooks()` on the modified section",
            f"3. Call `approve_section(section='{section}', action='approve')` when satisfied",
            "",
            "## Current Approval Status",
            "",
        ]
    return lines


def _append_section_statuses(lines: list[str], ckpt: CheckpointManager) -> None:
    """Append the approval status of every section."""
    # Show all section statuses
    statuses = ckpt.get_section_approval_status()
    for sec_name, sec_status in statuses.items():
        icon = {"approved": "✅", "revision_requested": "✏️", "pending": "⏳"}.get(sec_status, "❓")
        lines.append(f"- {icon} {sec_name}: {sec_status}")


def _approve_section_impl(section: str, action: str, feedback: str, project: Optional[str]) -> str:
    """Validate the request, persist the section decision and render the status report."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error
    project_info = _require_project_info(project_info)
    project_dir = Path(project_info["project_path"])
    audit_dir = project_dir / ".audit"

    if action not in ("approve", "revise"):
        return "❌ Action must be 'approve' or 'revise'."

    if action == "revise" and not feedback.strip():
        return "❌ Feedback is required when requesting revision. What should be changed?"

    missing_error = _section_missing_error(project_dir, section)
    if missing_error:
        return missing_error

    ckpt = CheckpointManager(audit_dir, project_dir=project_dir)

    lines = _save_section_decision(ckpt, section, action, feedback)
    _append_section_statuses(lines, ckpt)

    report = "\n".join(lines)
    log_tool_result("approve_section", f"{section}: {action}")
    return report


def _concept_review_impl(action: str, project: Optional[str]) -> str:
    """Inspect or revoke the concept-review override receipt."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error
    project_info = _require_project_info(project_info)

    if action not in ("approve", "status", "revoke"):
        return "❌ Action must be 'status' or 'revoke'."

    project_dir = Path(project_info["project_path"])
    audit_dir = project_dir / ".audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    concept_review_path = audit_dir / "concept-review.yaml"
    override_path = audit_dir / "concept-review-override.yaml"

    if not concept_review_path.is_file():
        return (
            "❌ concept-review.yaml not found. Run `validate_concept()` first so the concept "
            "is normalized before any manual approval is recorded."
        )

    if action == "revoke":
        if override_path.is_file():
            override_path.unlink()
        log_tool_result("approve_concept_review", "override revoked")
        return (
            "# ↩️ Concept Review Override Revoked\n\n"
            "Manual bypass has been removed. Phase 3/4 now require `readiness=ready` again."
        )

    if action == "approve":
        return _CONCEPT_APPROVAL_REFUSAL

    actionable, details = PipelineGateValidator(project_dir)._concept_review_is_actionable()
    status = "PASS" if actionable else "BLOCKED"
    log_tool_result("approve_concept_review", f"override status={status}")
    return "\n".join(
        [
            f"# Concept Review Status: {status}",
            "",
            f"- Receipt: {'present' if override_path.is_file() else 'missing'}",
            f"- Gate: {details}",
        ]
    )


def _review_completion_impl(action: str, project: Optional[str]) -> str:
    """Inspect or revoke the review-completion override receipt."""
    project_info, workflow_error = resolve_manuscript_project(project)
    if workflow_error:
        return workflow_error
    project_info = _require_project_info(project_info)
    if action not in ("approve", "status", "revoke"):
        return "❌ Action must be 'status' or 'revoke'."

    project_dir = Path(project_info["project_path"])
    audit_dir = project_dir / ".audit"
    override_path = audit_dir / "review-completion-override.yaml"
    if action == "revoke":
        if override_path.is_file():
            override_path.unlink()
        log_tool_result("approve_review_completion", "override revoked")
        return "# ↩️ Review Completion Override Revoked\n\nPhase 7 again requires quality_met."

    if action == "approve":
        return _REVIEW_APPROVAL_REFUSAL

    passed, details = PipelineGateValidator(project_dir)._check_review_completed()
    status = "PASS" if passed else "BLOCKED"
    log_tool_result("approve_review_completion", f"override status={status}")
    return "\n".join(
        [
            f"# Review Completion Status: {status}",
            "",
            f"- Receipt: {'present' if override_path.is_file() else 'missing'}",
            f"- Gate: {details}",
        ]
    )


@nested_tool_doc
def approve_section(
    section: str,
    action: str = "approve",
    feedback: str = "",
    project: Optional[str] = None,
) -> str:
    """
    ✅ Approve or request revision for a written section.

    During Phase 5, call this after each section is written and audited.
    The Phase 5 gate REQUIRES all sections to be approved before proceeding.

    **Autopilot mode (default)**: Agent self-reviews the section using Hook A/B
    results, then calls this with action="approve" to auto-approve and continue.
    No user confirmation needed unless the user explicitly requests review.

    **Manual mode**: User reviews each section and provides approve/revise.

    Actions:
    - "approve": Mark section as approved. Pipeline can continue to next section.
    - "revise": Mark section as needing revision. Agent must apply the feedback
                using patch_draft/write_draft, re-run hooks, then call this again.

    Args:
        section: Section name (e.g., "Methods", "Results", "Introduction")
        action: "approve" or "revise"
        feedback: User feedback for revision (required when action="revise")
        project: Project slug (optional, uses current project)

    Returns:
        Confirmation with next steps
    """
    log_tool_call("approve_section", {"section": section, "action": action})
    try:
        return _approve_section_impl(section, action, feedback, project)
    except Exception as e:
        log_tool_error("approve_section", e)
        return f"❌ Error processing section approval: {e}"


@nested_tool_doc
def approve_concept_review(
    action: str = "status",
    rationale: str = "",
    accepted_risks: str = "",
    project: Optional[str] = None,
    approved_by: str = "",
) -> str:
    """
    Inspect or revoke external Concept Review acceptance.

    The MCP and autonomous Agent share one authority and therefore cannot
    mint human evidence. A trusted host/UI must issue the v2 receipt.

    Actions:
    - "status": Inspect whether the current review/receipt is actionable.
    - "revoke": Remove the previous manual approval and restore normal hard gate behavior.

    Args:
        action: "status" or "revoke" ("approve" returns a refusal for compatibility)
        project: Project slug (optional, uses current project)
        approved_by: Deprecated compatibility field; never establishes authority

    Returns:
        Confirmation plus current gating implication
    """
    log_tool_call(
        "approve_concept_review",
        {"action": action, "project": project, "approved_by": approved_by},
    )
    try:
        return _concept_review_impl(action, project)
    except Exception as e:
        log_tool_error("approve_concept_review", e)
        return f"❌ Error processing concept review approval: {e}"


@nested_tool_doc
def approve_review_completion(
    action: str = "status",
    rationale: str = "",
    accepted_risks: str = "",
    project: Optional[str] = None,
    approved_by: str = "",
) -> str:
    """Inspect or revoke external human acceptance of a sub-threshold review.

    This MCP shares the autonomous Agent's authority, so it deliberately
    cannot mint a human-approval receipt. A trusted host/UI must create the
    v3 Ed25519-signed external-user-confirmation receipt. This helper can
    inspect or revoke that receipt without impersonating a reviewer. Trusted
    public keys come only from ``MDPAPER_APPROVAL_ED25519_PUBLIC_KEYS``.
    """
    log_tool_call(
        "approve_review_completion",
        {"action": action, "project": project, "approved_by": approved_by},
    )
    try:
        return _review_completion_impl(action, project)
    except Exception as e:
        log_tool_error("approve_review_completion", e)
        return f"❌ Error processing review completion approval: {e}"
