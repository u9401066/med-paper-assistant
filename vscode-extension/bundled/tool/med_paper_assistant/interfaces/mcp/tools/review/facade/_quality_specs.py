"""Action tables for the ``run_quality_checks`` facade."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from ..._shared import facade_schema_json
from ._types import QualityTools, ToolMap

QualitySpecs = dict[str, tuple[ToolMap, str, dict[str, Any]]]

QUALITY_ALIASES: dict[str, str] = {
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
    "ledger": "constraint_ledger",
    "constraint_status": "constraint_ledger",
    "retrospective": "pipeline_retrospective",
    "actions": "list",
    "help": "list",
    "list": "list",
    "supported": "list",
}


def _audit_specs(audit_tools: ToolMap, a: SimpleNamespace) -> QualitySpecs:
    return {
        "quality_audit": (
            audit_tools,
            "run_quality_audit",
            {"scores": a.scores, "project": a.project, "ctx": a.ctx},
        ),
        "meta_learning": (
            audit_tools,
            "run_meta_learning",
            {"project": a.project, "ctx": a.ctx},
        ),
        "pipeline_retrospective": (
            audit_tools,
            "write_pipeline_retrospective",
            {
                "summary": a.summary or a.content,
                "d7_retrospective": a.d7_retrospective,
                "d8_retrospective": a.d8_retrospective,
                "project": a.project,
                "ctx": a.ctx,
            },
        ),
        "data_artifacts": (
            audit_tools,
            "validate_data_artifacts",
            {"project": a.project, "ctx": a.ctx},
        ),
    }


def _hook_specs(audit_tools: ToolMap, a: SimpleNamespace) -> QualitySpecs:
    return {
        "writing_hooks": (
            audit_tools,
            "run_writing_hooks",
            {
                "hooks": a.hooks,
                "prefer_language": a.prefer_language,
                "project": a.project,
                "ctx": a.ctx,
            },
        ),
        "review_hooks": (
            audit_tools,
            "run_review_hooks",
            {
                "round_num": a.round_num,
                "hooks": a.hooks,
                "issues_fixed": a.issues_fixed,
                "project": a.project,
                "ctx": a.ctx,
            },
        ),
    }


def _formatting_specs(formatting_tools: ToolMap, a: SimpleNamespace) -> QualitySpecs:
    return {
        "formatting": (
            formatting_tools,
            "check_formatting",
            {
                "draft_filename": a.draft_filename,
                "journal": a.journal,
                "check_submission": a.check_submission,
                "has_cover_letter": a.has_cover_letter,
                "has_ethics": a.has_ethics,
                "has_consent": a.has_consent,
                "has_coi": a.has_coi,
                "has_author_contributions": a.has_author_contributions,
                "has_data_availability": a.has_data_availability,
                "has_keywords": a.has_keywords,
                "has_highlights": a.has_highlights,
                "project": a.project,
            },
        ),
    }


def _evolution_specs(audit_tools: ToolMap, a: SimpleNamespace) -> QualitySpecs:
    return {
        "record_hook_event": (
            audit_tools,
            "record_hook_event",
            {"hook_id": a.hook_id, "event_type": a.event_type, "project": a.project},
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
                "content": a.content,
                "section": a.section,
                "paper_type": a.paper_type,
                "project": a.project,
            },
        ),
        "evolve_constraint": (
            audit_tools,
            "evolve_constraint",
            {
                "constraint_id": a.constraint_id,
                "rule": a.rule,
                "category": a.category,
                "description": a.description,
                "severity": a.severity,
                "reason": a.reason,
                "source_hook": a.source_hook,
                "project": a.project,
            },
        ),
        "pending_evolutions": (
            audit_tools,
            "apply_pending_evolutions",
            {"action": a.reason or "preview", "item_ids": a.item_ids},
        ),
    }


def _health_specs(health_tools: ToolMap, a: SimpleNamespace) -> QualitySpecs:
    return {
        "tool_health": (
            health_tools,
            "diagnose_tool_health",
            {"project": a.project},
        ),
    }


def _constraint_specs(constraint_tools: ToolMap, a: SimpleNamespace) -> QualitySpecs:
    return {
        "constraint_ledger": (
            constraint_tools,
            "constraint_action",
            {"action": "status", "project": a.project},
        ),
        "constraint_add": (
            constraint_tools,
            "constraint_action",
            {
                "action": "add",
                "source": a.source_hook,
                "description": a.description,
                "severity": a.severity,
                "section": a.section,
                "project": a.project,
            },
        ),
    }


def _constraint_decision_specs(constraint_tools: ToolMap, a: SimpleNamespace) -> QualitySpecs:
    return {
        "constraint_satisfy": (
            constraint_tools,
            "constraint_action",
            {
                "action": "satisfy",
                "key": a.constraint_id,
                "reason": a.reason,
                "project": a.project,
            },
        ),
        "constraint_waive": (
            constraint_tools,
            "constraint_action",
            {
                "action": "waive",
                "key": a.constraint_id,
                "reason": a.reason,
                "project": a.project,
            },
        ),
        "constraint_reopen": (
            constraint_tools,
            "constraint_action",
            {
                "action": "reopen",
                "key": a.constraint_id,
                "reason": a.reason,
                "project": a.project,
            },
        ),
    }


def build_quality_action_specs(tools: QualityTools, a: SimpleNamespace) -> QualitySpecs:
    """Map each action to (tool group, handler name, kwargs) for the given arguments."""
    return {
        **_audit_specs(tools.audit_tools, a),
        **_hook_specs(tools.audit_tools, a),
        **_formatting_specs(tools.formatting_tools, a),
        **_evolution_specs(tools.audit_tools, a),
        **_health_specs(tools.health_tools, a),
        **_constraint_specs(tools.constraint_tools, a),
        **_constraint_decision_specs(tools.constraint_tools, a),
    }


def list_quality_actions(action_specs: QualitySpecs) -> str:
    """Machine-readable schema of the supported actions."""
    return facade_schema_json(
        tool="run_quality_checks",
        actions={
            name: {"handler": spec[1], "params": sorted(k for k in spec[2] if k != "ctx")}
            for name, spec in sorted(action_specs.items())
        },
        aliases=QUALITY_ALIASES,
        notes=[
            "Use action='meta_learning' for D1-D9 analysis.",
            "Use action='pipeline_retrospective' to write .audit/pipeline-run-*.md with required D7/D8 headings.",
            "Use response_format='json' where downstream tools support structured output.",
        ],
    )
