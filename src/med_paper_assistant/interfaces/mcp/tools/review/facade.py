"""Consolidated review/pipeline facade tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from mcp.server.fastmcp import Context, FastMCP

from .._shared import invoke_tool_handler, normalize_facade_action

ToolMap = Mapping[str, Callable[..., Any]]


def register_review_facade_tools(
    mcp: FastMCP,
    audit_tools: ToolMap,
    pipeline_tools: ToolMap,
):
    """Register stable facade verbs for review quality and pipeline control."""

    @mcp.tool()
    async def run_quality_checks(
        action: str,
        scores: str = "",
        hooks: str = "all",
        prefer_language: str = "american",
        round_num: int = 0,
        issues_fixed: int = 0,
        project: Optional[str] = None,
        ctx: Context | None = None,
    ) -> str:
        """
        Run consolidated review/audit quality actions through one stable entrypoint.

        Actions:
        - quality_audit
        - meta_learning
        - data_artifacts
        - writing_hooks
        - review_hooks
        """
        aliases = {
            "audit": "quality_audit",
            "quality": "quality_audit",
            "meta": "meta_learning",
            "artifacts": "data_artifacts",
            "data": "data_artifacts",
            "writing": "writing_hooks",
            "review": "review_hooks",
        }
        normalized = normalize_facade_action(action, aliases)
        action_specs: dict[str, tuple[str, dict[str, Any]]] = {
            "quality_audit": (
                "run_quality_audit",
                {"scores": scores, "project": project, "ctx": ctx},
            ),
            "meta_learning": (
                "run_meta_learning",
                {"project": project, "ctx": ctx},
            ),
            "data_artifacts": (
                "validate_data_artifacts",
                {"project": project, "ctx": ctx},
            ),
            "writing_hooks": (
                "run_writing_hooks",
                {
                    "hooks": hooks,
                    "prefer_language": prefer_language,
                    "project": project,
                    "ctx": ctx,
                },
            ),
            "review_hooks": (
                "run_review_hooks",
                {
                    "round_num": round_num,
                    "hooks": hooks,
                    "issues_fixed": issues_fixed,
                    "project": project,
                    "ctx": ctx,
                },
            ),
        }

        if normalized not in action_specs:
            supported = ", ".join(sorted(action_specs))
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        handler_name, kwargs = action_specs[normalized]
        handler = audit_tools.get(handler_name)
        if handler is None:
            return f"❌ Review facade misconfigured: missing handler '{handler_name}'"

        return await invoke_tool_handler(handler, **kwargs)

    @mcp.tool()
    async def pipeline_action(
        action: str,
        phase: int = 0,
        project: Optional[str] = None,
        max_rounds: int = 3,
        min_rounds: int = 2,
        quality_threshold: float = 7.0,
        scores: str = "",
        issues_found: int = 0,
        issues_fixed: int = 0,
        sections: str = "",
        reason: str = "user_requested",
        section: str = "",
        decision: str = "approve",
        feedback: str = "",
        rationale: str = "",
        accepted_risks: str = "",
        approved_by: str = "human",
        ctx: Context | None = None,
    ) -> str:
        """
        Run consolidated pipeline state-machine actions through one stable entrypoint.

        Actions:
        - validate_phase
        - heartbeat
        - start_review
        - submit_review
        - validate_structure
        - rewrite_section
        - pause
        - resume
        - approve_section
        - approve_concept_review
        - reset_review_loop
        """
        aliases = {
            "gate": "validate_phase",
            "status": "heartbeat",
            "start": "start_review",
            "submit": "submit_review",
            "structure": "validate_structure",
            "rewrite": "rewrite_section",
            "concept_review": "approve_concept_review",
            "reset": "reset_review_loop",
        }
        normalized = normalize_facade_action(action, aliases)
        action_specs: dict[str, tuple[str, dict[str, Any]]] = {
            "validate_phase": (
                "validate_phase_gate",
                {"phase": phase, "project": project, "ctx": ctx},
            ),
            "heartbeat": (
                "pipeline_heartbeat",
                {"project": project, "ctx": ctx},
            ),
            "start_review": (
                "start_review_round",
                {
                    "project": project,
                    "max_rounds": max_rounds,
                    "min_rounds": min_rounds,
                    "quality_threshold": quality_threshold,
                    "ctx": ctx,
                },
            ),
            "submit_review": (
                "submit_review_round",
                {
                    "scores": scores,
                    "issues_found": issues_found,
                    "issues_fixed": issues_fixed,
                    "project": project,
                    "ctx": ctx,
                },
            ),
            "validate_structure": (
                "validate_project_structure",
                {"project": project, "ctx": ctx},
            ),
            "rewrite_section": (
                "request_section_rewrite",
                {"sections": sections, "reason": reason, "project": project},
            ),
            "pause": (
                "pause_pipeline",
                {"reason": reason, "project": project},
            ),
            "resume": (
                "resume_pipeline",
                {"project": project},
            ),
            "approve_section": (
                "approve_section",
                {
                    "section": section,
                    "action": decision,
                    "feedback": feedback,
                    "project": project,
                },
            ),
            "approve_concept_review": (
                "approve_concept_review",
                {
                    "action": decision,
                    "rationale": rationale,
                    "accepted_risks": accepted_risks,
                    "project": project,
                    "approved_by": approved_by,
                },
            ),
            "reset_review_loop": (
                "reset_review_loop",
                {"project": project},
            ),
        }

        if normalized not in action_specs:
            supported = ", ".join(sorted(action_specs))
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        handler_name, kwargs = action_specs[normalized]
        handler = pipeline_tools.get(handler_name)
        if handler is None:
            return f"❌ Pipeline facade misconfigured: missing handler '{handler_name}'"

        return await invoke_tool_handler(handler, **kwargs)

    return {
        "run_quality_checks": run_quality_checks,
        "pipeline_action": pipeline_action,
    }