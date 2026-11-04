"""SubagentStart hook: give a subagent the project, mode and role guidance."""

from __future__ import annotations

from .common import HookContext, HookResult, Payload, build_output, first_alt
from .workspace import (
    mode_or_normal,
    read_state,
    resolve_active_project,
    workflow_mode,
    writing_section,
)

EVENT = "SubagentStart"
READ_ONLY_REVIEW = (
    "Read-only mode: Do NOT modify any draft files. Produce a structured review report only."
)
AGENT_GUIDANCE = {
    "literature-searcher": (
        "Use save_reference_mcp(pmid) for saving. Never use save_reference() directly."
    ),
    "paper-reviewer": READ_ONLY_REVIEW,
    "domain-reviewer": READ_ONLY_REVIEW,
    "methodology-reviewer": READ_ONLY_REVIEW,
    "statistics-reviewer": READ_ONLY_REVIEW,
    "reference-analyzer": (
        "Focus on extracting structured data from full text. Do not modify project files."
    ),
    "concept-challenger": "Be critical and constructive. Challenge novelty claims with evidence.",
}
LIBRARY_WIKI_NOTE = (
    "WORKFLOW NOTE: active project is library-wiki. Prioritize ingestion, organization, "
    "synthesis, and evidence traversal unless the user explicitly requests a manuscript "
    "transition."
)


def agent_name(payload: Payload) -> str:
    """Subagent name across host payload variants; ``unknown`` when absent."""
    return (
        first_alt(
            payload.get("agentName"),
            payload.get("agent_name"),
            payload.get("agent_type"),
            payload.get("agentType"),
        )
        or "unknown"
    )


def _header(agent: str, mode: str, project: str, workflow: str, section: str) -> str:
    header = f"[SUBAGENT CONTEXT] Agent: {agent} | Mode: {mode}"
    for label, value in (("Project", project), ("Workflow", workflow), ("Writing", section)):
        if value:
            header += f" | {label}: {value}"
    return header


def build_context(agent: str, mode: str, project: str, workflow: str, section: str) -> str:
    lines = [_header(agent, mode, project, workflow, section)]
    guidance = AGENT_GUIDANCE.get(agent)
    if guidance:
        lines.append(guidance)
    if workflow == "library-wiki":
        lines.append(LIBRARY_WIKI_NOTE)
    if mode in ("normal", "research"):
        lines.append(
            f"MODE RESTRICTION: {mode} mode — .claude/, .github/, src/, tests/ are read-only."
        )
    return "\n".join(lines)


def run(payload: Payload, ctx: HookContext) -> HookResult:
    root = ctx.workspace_root
    state = read_state(root)
    project = resolve_active_project(root, state, prefer_current_file=False)
    workflow = workflow_mode(root, project, on_error="manuscript")
    context = build_context(
        agent_name(payload),
        mode_or_normal(root),
        project,
        workflow,
        writing_section(state),
    )
    return build_output(EVENT, context)
