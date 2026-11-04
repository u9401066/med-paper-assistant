"""``run_quality_checks`` facade handler."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

from mcp.server.mcpserver import Context

from ..._shared import invoke_tool_handler, normalize_facade_action
from ._quality_specs import QUALITY_ALIASES, build_quality_action_specs, list_quality_actions
from ._types import QualityTools


async def run_quality_action(tools: QualityTools, action: str, a: SimpleNamespace) -> str:
    """Resolve ``action`` and invoke the matching review handler."""
    normalized = normalize_facade_action(action, QUALITY_ALIASES)
    action_specs = build_quality_action_specs(tools, a)

    if normalized == "list":
        return list_quality_actions(action_specs)
    if normalized not in action_specs:
        supported = ", ".join(sorted(action_specs))
        return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

    tool_group, handler_name, kwargs = action_specs[normalized]
    handler = tool_group.get(handler_name)
    if handler is None:
        return f"❌ Review facade misconfigured: missing handler '{handler_name}'"

    return await invoke_tool_handler(handler, **kwargs)


class QualityChecksTool:
    """Holds the tool groups behind the ``run_quality_checks`` handler."""

    def __init__(self, tools: QualityTools) -> None:
        self._tools = tools

    async def run_quality_checks(
        self,
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
        - constraint_ledger
        - constraint_add
        - constraint_satisfy
        - constraint_waive
        - constraint_reopen
        """
        return await run_quality_action(self._tools, action, SimpleNamespace(**locals()))
