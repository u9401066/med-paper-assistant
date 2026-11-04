"""``pipeline_action`` facade handler."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

from mcp.server.mcpserver import Context

from ..._shared import invoke_tool_handler, normalize_facade_action
from ._pipeline_specs import (
    ASSET_ACTIONS,
    PIPELINE_ALIASES,
    asset_action_error,
    build_pipeline_action_specs,
    list_pipeline_actions,
)
from ._types import ToolMap


async def run_pipeline_action(pipeline_tools: ToolMap, action: str, a: SimpleNamespace) -> str:
    """Resolve ``action`` and invoke the matching pipeline handler."""
    normalized = normalize_facade_action(action, PIPELINE_ALIASES)
    if normalized == "list":
        return list_pipeline_actions()
    if normalized in ASSET_ACTIONS:
        return asset_action_error(action)
    action_specs = build_pipeline_action_specs(a)
    if normalized not in action_specs:
        supported = ", ".join(sorted([*action_specs, "list"]))
        return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

    handler_name, kwargs = action_specs[normalized]
    handler = pipeline_tools.get(handler_name)
    if handler is None:
        return f"❌ Pipeline facade misconfigured: missing handler '{handler_name}'"

    return await invoke_tool_handler(handler, **kwargs)


class PipelineActionTool:
    """Holds the pipeline tool group behind the ``pipeline_action`` handler."""

    def __init__(self, pipeline_tools: ToolMap) -> None:
        self._pipeline_tools = pipeline_tools

    async def pipeline_action(
        self,
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
        - approve_review_completion
        - reset_review_loop
        - list
        """
        return await run_pipeline_action(self._pipeline_tools, action, SimpleNamespace(**locals()))
