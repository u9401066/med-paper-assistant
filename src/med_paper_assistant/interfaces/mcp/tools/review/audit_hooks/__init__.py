"""
Audit Hook Tools — Hard enforcement MCP tools for quality audit and meta-learning.

These tools wrap the QualityScorecard, HookEffectivenessTracker, MetaLearningEngine,
and DataArtifactTracker as MCP tools that the agent MUST call. The agent cannot bypass
them — the Phase 5, 6, and 10 gate validators check for actual data produced by these tools.
Tool responses use TOON (Token-Oriented Object Notation) format for ~40% token savings.
See: https://github.com/toon-format/toon
Tools:
- record_hook_event: Record a hook evaluation outcome (trigger/pass/fix/false_positive)
- run_quality_audit: Set quality scores for all dimensions and generate audit report
- run_meta_learning: Run D1-D9 meta-learning analysis and write audit trail
- validate_data_artifacts: Cross-validate data artifacts, manifest, and draft references
"""

from mcp.server import MCPServer

from ..._shared import get_optional_tool_decorator
from ._constraints import check_domain_constraints, evolve_constraint
from ._data_artifacts import validate_data_artifacts
from ._evolution import apply_pending_evolutions, verify_evolution
from ._hook_events import record_hook_event
from ._meta_learning import run_meta_learning
from ._quality_audit import run_quality_audit
from ._retrospective import (
    _write_pipeline_retrospective_artifact,
    write_pipeline_retrospective,
)
from ._review_hooks import run_review_hooks
from ._writing_hooks import run_writing_hooks


def register_audit_hook_tools(
    mcp: MCPServer,
    *,
    register_public_verbs: bool = True,
):
    """Register audit hook enforcement tools with the MCP server."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    # Registration order is part of the published tool surface.
    registered = {
        fn.__name__: tool()(fn)
        for fn in (
            record_hook_event,
            run_quality_audit,
            run_meta_learning,
            validate_data_artifacts,
            run_writing_hooks,
            verify_evolution,
            check_domain_constraints,
            evolve_constraint,
            apply_pending_evolutions,
            write_pipeline_retrospective,
            run_review_hooks,
        )
    }

    return {
        "record_hook_event": registered["record_hook_event"],
        "run_quality_audit": registered["run_quality_audit"],
        "run_meta_learning": registered["run_meta_learning"],
        "write_pipeline_retrospective": registered["write_pipeline_retrospective"],
        "validate_data_artifacts": registered["validate_data_artifacts"],
        "run_writing_hooks": registered["run_writing_hooks"],
        "run_review_hooks": registered["run_review_hooks"],
        "verify_evolution": registered["verify_evolution"],
        "check_domain_constraints": registered["check_domain_constraints"],
        "evolve_constraint": registered["evolve_constraint"],
        "apply_pending_evolutions": registered["apply_pending_evolutions"],
    }


__all__ = ["_write_pipeline_retrospective_artifact", "register_audit_hook_tools"]
