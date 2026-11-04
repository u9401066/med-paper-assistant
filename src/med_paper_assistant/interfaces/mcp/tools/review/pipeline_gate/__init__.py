"""
Pipeline Gate Tools — Hard enforcement MCP tools.

These tools expose PipelineGateValidator as MCP tools that the agent
MUST call. Unlike SKILL.md (soft constraint), these return FAIL with
specific missing artifacts — the agent cannot bypass them.

Tools:
- validate_phase_gate: Check all required artifacts for a phase
- pipeline_heartbeat: Get full pipeline status across all phases
- start_review_round: Begin a review round (exposes AutonomousAuditLoop)
- submit_review_round: Complete a review round with scores + verdict
- request_section_rewrite: Regress from Phase 7 to Phase 5 for section rewrite
- pause_pipeline: Pause pipeline for user manual editing
- resume_pipeline: Resume pipeline after pause, detecting user edits
- approve_section: Approve or request revision for a written section
- approve_review_completion: Inspect/revoke an externally issued review receipt
"""

from mcp.server import MCPServer

from med_paper_assistant.infrastructure.persistence import ProjectManager

from ..._shared import get_optional_tool_decorator
from ._approvals import (
    approve_concept_review,
    approve_review_completion,
    approve_section,
)
from ._artifacts import (
    _compute_manuscript_hash,
    _count_review_report_issues,
    _validate_review_score_schema,
)
from ._doctor import pipeline_doctor
from ._gates import pipeline_heartbeat, validate_phase_gate, validate_project_structure
from ._pause import pause_pipeline, resume_pipeline
from ._review_start import start_review_round
from ._review_submit import submit_review_round
from ._rewrite import request_section_rewrite, reset_review_loop


def register_pipeline_tools(
    mcp: MCPServer,
    project_manager: ProjectManager,
    *,
    register_public_verbs: bool = True,
):
    """Register pipeline enforcement tools with the MCP server."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    # Registration order is part of the published tool surface.
    registered = {
        fn.__name__: tool()(fn)
        for fn in (
            validate_phase_gate,
            pipeline_heartbeat,
            start_review_round,
            submit_review_round,
            validate_project_structure,
            request_section_rewrite,
            pause_pipeline,
            resume_pipeline,
            approve_section,
            approve_concept_review,
            reset_review_loop,
            pipeline_doctor,
        )
    }

    return {
        "validate_phase_gate": registered["validate_phase_gate"],
        "pipeline_doctor": registered["pipeline_doctor"],
        "pipeline_heartbeat": registered["pipeline_heartbeat"],
        "start_review_round": registered["start_review_round"],
        "submit_review_round": registered["submit_review_round"],
        "validate_project_structure": registered["validate_project_structure"],
        "request_section_rewrite": registered["request_section_rewrite"],
        "pause_pipeline": registered["pause_pipeline"],
        "resume_pipeline": registered["resume_pipeline"],
        "approve_section": registered["approve_section"],
        "approve_concept_review": registered["approve_concept_review"],
        "approve_review_completion": approve_review_completion,
        "reset_review_loop": registered["reset_review_loop"],
    }


__all__ = [
    "_compute_manuscript_hash",
    "_count_review_report_issues",
    "_validate_review_score_schema",
    "register_pipeline_tools",
]
