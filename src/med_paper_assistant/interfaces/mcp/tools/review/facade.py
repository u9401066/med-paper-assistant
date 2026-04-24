"""Consolidated review/pipeline facade tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Optional

from mcp.server.fastmcp import Context, FastMCP

from .._shared import facade_schema_json, invoke_tool_handler, normalize_facade_action

ToolMap = Mapping[str, Callable[..., Any]]


def register_review_facade_tools(
    mcp: FastMCP,
    audit_tools: ToolMap,
    pipeline_tools: ToolMap,
    formatting_tools: ToolMap | None = None,
    health_tools: ToolMap | None = None,
):
    """Register stable facade verbs for review quality and pipeline control."""

    formatting_tools = formatting_tools or {}
    health_tools = health_tools or {}

    @mcp.tool()
    async def run_quality_checks(
        action: str,
        scores: str = "",
        hooks: str = "all",
        prefer_language: str = "american",
        round_num: int = 0,
        issues_fixed: int = 0,
        draft_filename: str = "",
        journal: str = "generic",
        check_submission: bool = False,
        has_cover_letter: bool = False,
        has_ethics: bool = False,
        has_consent: bool = False,
        has_coi: bool = False,
        has_author_contributions: bool = False,
        has_data_availability: bool = False,
        has_keywords: bool = False,
        has_highlights: bool = False,
        hook_id: str = "",
        event_type: str = "",
        response_format: str = "markdown",
        compact: bool = False,
        summary: str = "",
        d7_retrospective: str = "",
        d8_retrospective: str = "",
        content: str = "",
        section: str = "manuscript",
        paper_type: str = "",
        constraint_id: str = "",
        rule: str = "",
        category: str = "",
        description: str = "",
        severity: str = "WARNING",
        reason: str = "",
        source_hook: str = "",
        item_ids: str = "",
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
        - formatting
        - record_hook_event
        - verify_evolution
        - domain_constraints
        - evolve_constraint
        - pending_evolutions
        - tool_health
        """
        aliases = {
            "audit": "quality_audit",
            "quality": "quality_audit",
            "meta": "meta_learning",
            "artifacts": "data_artifacts",
            "data": "data_artifacts",
            "writing": "writing_hooks",
            "review": "review_hooks",
            "format": "formatting",
            "record_hook": "record_hook_event",
            "constraints": "domain_constraints",
            "pending": "pending_evolutions",
            "health": "tool_health",
            "retrospective": "pipeline_retrospective",
            "actions": "list",
            "help": "list",
            "list": "list",
            "supported": "list",
        }
        normalized = normalize_facade_action(action, aliases)
        action_specs: dict[str, tuple[ToolMap, str, dict[str, Any]]] = {
            "quality_audit": (
                audit_tools,
                "run_quality_audit",
                {"scores": scores, "project": project, "ctx": ctx},
            ),
            "meta_learning": (
                audit_tools,
                "run_meta_learning",
                {"project": project, "ctx": ctx},
            ),
            "pipeline_retrospective": (
                audit_tools,
                "write_pipeline_retrospective",
                {
                    "summary": summary or content,
                    "d7_retrospective": d7_retrospective,
                    "d8_retrospective": d8_retrospective,
                    "project": project,
                    "ctx": ctx,
                },
            ),
            "data_artifacts": (
                audit_tools,
                "validate_data_artifacts",
                {"project": project, "ctx": ctx},
            ),
            "writing_hooks": (
                audit_tools,
                "run_writing_hooks",
                {
                    "hooks": hooks,
                    "prefer_language": prefer_language,
                    "project": project,
                    "ctx": ctx,
                },
            ),
            "review_hooks": (
                audit_tools,
                "run_review_hooks",
                {
                    "round_num": round_num,
                    "hooks": hooks,
                    "issues_fixed": issues_fixed,
                    "project": project,
                    "ctx": ctx,
                },
            ),
            "formatting": (
                formatting_tools,
                "check_formatting",
                {
                    "draft_filename": draft_filename,
                    "journal": journal,
                    "check_submission": check_submission,
                    "has_cover_letter": has_cover_letter,
                    "has_ethics": has_ethics,
                    "has_consent": has_consent,
                    "has_coi": has_coi,
                    "has_author_contributions": has_author_contributions,
                    "has_data_availability": has_data_availability,
                    "has_keywords": has_keywords,
                    "has_highlights": has_highlights,
                    "project": project,
                },
            ),
            "record_hook_event": (
                audit_tools,
                "record_hook_event",
                {"hook_id": hook_id, "event_type": event_type, "project": project},
            ),
            "verify_evolution": (
                audit_tools,
                "verify_evolution",
                {},
            ),
            "domain_constraints": (
                audit_tools,
                "check_domain_constraints",
                {
                    "content": content,
                    "section": section,
                    "paper_type": paper_type,
                    "project": project,
                },
            ),
            "evolve_constraint": (
                audit_tools,
                "evolve_constraint",
                {
                    "constraint_id": constraint_id,
                    "rule": rule,
                    "category": category,
                    "description": description,
                    "severity": severity,
                    "reason": reason,
                    "source_hook": source_hook,
                    "project": project,
                },
            ),
            "pending_evolutions": (
                audit_tools,
                "apply_pending_evolutions",
                {"action": reason or "preview", "item_ids": item_ids},
            ),
            "tool_health": (
                health_tools,
                "diagnose_tool_health",
                {"project": project},
            ),
        }

        if normalized == "list":
            return facade_schema_json(
                tool="run_quality_checks",
                actions={
                    name: {"handler": spec[1], "params": sorted(k for k in spec[2] if k != "ctx")}
                    for name, spec in sorted(action_specs.items())
                },
                aliases=aliases,
                notes=[
                    "Use action='meta_learning' for D1-D6 analysis.",
                    "Use action='pipeline_retrospective' to write .audit/pipeline-run-*.md with required D7/D8 headings.",
                    "Use response_format='json' where downstream tools support structured output.",
                ],
            )

        if normalized not in action_specs:
            supported = ", ".join(sorted(action_specs))
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        tool_group, handler_name, kwargs = action_specs[normalized]
        handler = tool_group.get(handler_name)
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
        response_format: str = "markdown",
        compact: bool = False,
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
        - list
        """
        aliases = {
            "actions": "list",
            "doctor": "doctor",
            "gate": "validate_phase",
            "help": "list",
            "status": "heartbeat",
            "start": "start_review",
            "submit": "submit_review",
            "supported": "list",
            "structure": "validate_structure",
            "rewrite": "rewrite_section",
            "concept_review": "approve_concept_review",
            "reset": "reset_review_loop",
        }
        normalized = normalize_facade_action(action, aliases)
        if normalized == "list":
            return facade_schema_json(
                tool="pipeline_action",
                actions={
                    "validate_phase": {
                        "handler": "validate_phase_gate",
                        "params": ["phase", "project", "response_format", "compact"],
                        "phase_values": [0, 1, 2, 21, 3, 4, 5, 6, 65, 7, 8, 9, 10, 11],
                    },
                    "heartbeat": {
                        "handler": "pipeline_heartbeat",
                        "params": ["project"],
                    },
                    "doctor": {
                        "handler": "pipeline_doctor",
                        "params": ["project"],
                    },
                    "validate_structure": {
                        "handler": "validate_project_structure",
                        "params": ["project"],
                    },
                    "start_review": {
                        "handler": "start_review_round",
                        "params": ["project", "max_rounds", "min_rounds", "quality_threshold"],
                    },
                    "submit_review": {
                        "handler": "submit_review_round",
                        "params": ["scores", "issues_found", "issues_fixed", "project"],
                        "score_schema": {
                            "required_dimensions": [
                                "citation_quality",
                                "methodology_reproducibility",
                                "text_quality",
                                "concept_consistency",
                                "format_compliance",
                                "figure_table_quality",
                            ],
                            "score_range": [0, 10],
                        },
                    },
                    "rewrite_section": {
                        "handler": "request_section_rewrite",
                        "params": ["sections", "reason", "project"],
                    },
                    "pause": {"handler": "pause_pipeline", "params": ["reason", "project"]},
                    "resume": {"handler": "resume_pipeline", "params": ["project"]},
                    "approve_section": {
                        "handler": "approve_section",
                        "params": [
                            "section",
                            "decision",
                            "feedback",
                            "rationale",
                            "accepted_risks",
                            "approved_by",
                            "project",
                        ],
                    },
                    "approve_concept_review": {
                        "handler": "approve_concept_review",
                        "params": ["decision", "feedback", "rationale", "accepted_risks", "project"],
                    },
                    "reset_review_loop": {
                        "handler": "reset_review_loop",
                        "params": ["project"],
                    },
                },
                aliases=aliases,
                notes=[
                    "Phase 7 flow: start_review -> create review artifacts -> patch draft -> submit_review -> validate_phase.",
                    "Figure/table assets are handled by analysis_action or draft_action, not pipeline_action.",
                    "Use response_format='json' and compact=true on validate_phase for agent-friendly gate output.",
                ],
            )
        if normalized in {
            "insert_figure",
            "insert_table",
            "list_assets",
            "review_asset",
            "review_asset_for_insertion",
        }:
            return (
                f"❌ Unsupported pipeline action '{action}'. "
                "Use asset tools for figures/tables:\n"
                "• `draft_action(action=\"insert_figure\", filename=..., caption=..., ... )`\n"
                "• `analysis_action(action=\"insert_figure\", filename=..., caption=..., ... )`\n"
                "• `draft_action(action=\"insert_table\", filename=..., caption=..., table_content=..., ... )`\n"
                "• `analysis_action(action=\"insert_table\", filename=..., caption=..., ... )`\n"
                "• `draft_action(action=\"list_assets\")`\n"
                "• `analysis_action(action=\"list_assets\")`\n"
                "For asset review use `analysis_action(action=\"review_asset_for_insertion\" or \"review_asset\")`."
            )
        action_specs: dict[str, tuple[str, dict[str, Any]]] = {
            "validate_phase": (
                "validate_phase_gate",
                {
                    "phase": phase,
                    "project": project,
                    "response_format": response_format,
                    "compact": compact,
                    "ctx": ctx,
                },
            ),
            "heartbeat": (
                "pipeline_heartbeat",
                {"project": project, "ctx": ctx},
            ),
            "doctor": (
                "pipeline_doctor",
                {"project": project},
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
            supported = ", ".join(sorted([*action_specs, "list"]))
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
