"""Action tables for the ``pipeline_action`` facade."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from ..._shared import facade_schema_json

PipelineSpecs = dict[str, tuple[str, dict[str, Any]]]

PIPELINE_ALIASES: dict[str, str] = {
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

PIPELINE_ACTION_SCHEMAS: dict[str, dict[str, Any]] = {
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
        "params": ["decision", "project"],
        "decision_values": ["status", "revoke"],
        "external_receipt_schema": "mdpaper.concept_review_override.v3",
        "external_receipt_signature": {
            "algorithm": "Ed25519",
            "encoding": "base64url",
            "fields": ["key_id", "value"],
            "trusted_keys_env": "MDPAPER_APPROVAL_ED25519_PUBLIC_KEYS",
        },
        "required_binding": ["concept_artifact_sha256", "concept_review_sha256"],
    },
    "approve_review_completion": {
        "handler": "approve_review_completion",
        "params": ["decision", "project"],
        "decision_values": ["status", "revoke"],
        "external_receipt_schema": "mdpaper.review_completion_override.v3",
        "external_receipt_signature": {
            "algorithm": "Ed25519",
            "encoding": "base64url",
            "fields": ["key_id", "value"],
            "trusted_keys_env": "MDPAPER_APPROVAL_ED25519_PUBLIC_KEYS",
        },
    },
    "reset_review_loop": {
        "handler": "reset_review_loop",
        "params": ["project"],
    },
}

PIPELINE_NOTES: list[str] = [
    "Phase 7 flow: start_review -> create review artifacts -> patch draft -> submit_review -> validate_phase.",
    "Figure/table assets are handled by analysis_action or draft_action, not pipeline_action.",
    "Use response_format='json' and compact=true on validate_phase for agent-friendly gate output.",
    "A sub-threshold review can only be accepted by an external trusted host/UI; pipeline_action can inspect or revoke that receipt, but cannot mint it.",
]

ASSET_ACTIONS = {
    "insert_figure",
    "insert_table",
    "list_assets",
    "review_asset",
    "review_asset_for_insertion",
}


def list_pipeline_actions() -> str:
    """Machine-readable schema of the supported actions."""
    return facade_schema_json(
        tool="pipeline_action",
        actions=PIPELINE_ACTION_SCHEMAS,
        aliases=PIPELINE_ALIASES,
        notes=PIPELINE_NOTES,
    )


def asset_action_error(action: str) -> str:
    """Redirect figure/table asset actions to the tools that own them."""
    return (
        f"❌ Unsupported pipeline action '{action}'. "
        "Use asset tools for figures/tables:\n"
        '• `draft_action(action="insert_figure", filename=..., caption=..., ... )`\n'
        '• `analysis_action(action="insert_figure", filename=..., caption=..., ... )`\n'
        '• `draft_action(action="insert_table", filename=..., caption=..., table_content=..., ... )`\n'
        '• `analysis_action(action="insert_table", filename=..., caption=..., ... )`\n'
        '• `draft_action(action="list_assets")`\n'
        '• `analysis_action(action="list_assets")`\n'
        'For asset review use `analysis_action(action="review_asset_for_insertion" or "review_asset")`.'
    )


def _core_specs(a: SimpleNamespace) -> PipelineSpecs:
    return {
        "validate_phase": (
            "validate_phase_gate",
            {
                "phase": a.phase,
                "project": a.project,
                "response_format": a.response_format,
                "compact": a.compact,
                "ctx": a.ctx,
            },
        ),
        "heartbeat": (
            "pipeline_heartbeat",
            {"project": a.project, "ctx": a.ctx},
        ),
        "doctor": (
            "pipeline_doctor",
            {"project": a.project},
        ),
        "start_review": (
            "start_review_round",
            {
                "project": a.project,
                "max_rounds": a.max_rounds,
                "min_rounds": a.min_rounds,
                "quality_threshold": a.quality_threshold,
                "ctx": a.ctx,
            },
        ),
        "submit_review": (
            "submit_review_round",
            {
                "scores": a.scores,
                "issues_found": a.issues_found,
                "issues_fixed": a.issues_fixed,
                "project": a.project,
                "ctx": a.ctx,
            },
        ),
        "validate_structure": (
            "validate_project_structure",
            {"project": a.project, "ctx": a.ctx},
        ),
    }


def _control_specs(a: SimpleNamespace) -> PipelineSpecs:
    return {
        "rewrite_section": (
            "request_section_rewrite",
            {"sections": a.sections, "reason": a.reason, "project": a.project},
        ),
        "pause": (
            "pause_pipeline",
            {"reason": a.reason, "project": a.project},
        ),
        "resume": (
            "resume_pipeline",
            {"project": a.project},
        ),
        "approve_section": (
            "approve_section",
            {
                "section": a.section,
                "action": a.decision,
                "feedback": a.feedback,
                "project": a.project,
            },
        ),
    }


def _approval_specs(a: SimpleNamespace) -> PipelineSpecs:
    return {
        "approve_concept_review": (
            "approve_concept_review",
            {
                "action": a.decision,
                "rationale": a.rationale,
                "accepted_risks": a.accepted_risks,
                "project": a.project,
                "approved_by": a.approved_by,
            },
        ),
        "approve_review_completion": (
            "approve_review_completion",
            {
                "action": a.decision,
                "rationale": a.rationale,
                "accepted_risks": a.accepted_risks,
                "project": a.project,
                "approved_by": a.approved_by,
            },
        ),
        "reset_review_loop": (
            "reset_review_loop",
            {"project": a.project},
        ),
    }


def build_pipeline_action_specs(a: SimpleNamespace) -> PipelineSpecs:
    """Map each action to (handler name, kwargs) for the given arguments."""
    return {**_core_specs(a), **_control_specs(a), **_approval_specs(a)}
