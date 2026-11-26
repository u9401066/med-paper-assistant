"""PostToolUse hook: remind the agent which quality hooks to run after a tool call."""

from __future__ import annotations

import re

from .common import (
    CROSS_PLATFORM_RE,
    HookContext,
    HookResult,
    Payload,
    alt,
    append_audit,
    build_output,
    first_alt,
    get_tool_input,
    get_tool_name,
    normalize_slashes,
)
from .workspace import active_workflow_mode

EVENT = "PostToolUse"
LIBRARY_WIKI = "library-wiki"

DRAFT_TOOL_RE = re.compile(r"(?:^|_)(write_draft|patch_draft|draft_section)$", re.IGNORECASE)
DRAFT_ACTION_RE = re.compile(r"(?:^|_)draft_action$", re.IGNORECASE)
DRAFT_WRITE_ACTIONS = frozenset(
    {"write", "patch", "draft_section", "section", "create", "update", "edit"}
)
DRAFT_CITE_ACTIONS = frozenset({"insert_citation", "cite"})
FILE_EDIT_RE = re.compile(
    r"apply_patch|editFiles|replace_string|multi_replace|create_file|edit_file|write_file",
    re.IGNORECASE,
)
APPLY_PATCH_RE = re.compile(r"apply_patch", re.IGNORECASE)
INSERT_CITATION_RE = re.compile(r"(?:^|_)insert_citation$", re.IGNORECASE)
SAVE_REFERENCE_RE = re.compile(r"(?:^|_)save_reference(?:_mcp)?$", re.IGNORECASE)
REFERENCE_ACTION_RE = re.compile(r"(?:^|_)reference_action$", re.IGNORECASE)
REFERENCE_SAVE_ACTIONS = frozenset({"save_agent", "save", "save_reference", "agent_save"})
TERMINAL_RE = re.compile(r"terminal", re.IGNORECASE)
VALIDATE_CONCEPT_RE = re.compile(r"(?:^|_)validate_concept$", re.IGNORECASE)
VALIDATION_ACTION_RE = re.compile(r"(?:^|_)validation_action$", re.IGNORECASE)
VALIDATION_CONCEPT_ACTIONS = frozenset({"concept", "validate_concept", "concept_validation"})


def _action_name(tool_input: Payload) -> str:
    return alt(tool_input.get("action")).strip().lower().replace("-", "_")


def _is_draft_write_call(tool: str, tool_input: Payload) -> bool:
    if DRAFT_TOOL_RE.search(tool):
        return True
    return bool(DRAFT_ACTION_RE.search(tool) and _action_name(tool_input) in DRAFT_WRITE_ACTIONS)


def _is_insert_citation_call(tool: str, tool_input: Payload) -> bool:
    if INSERT_CITATION_RE.search(tool):
        return True
    return bool(DRAFT_ACTION_RE.search(tool) and _action_name(tool_input) in DRAFT_CITE_ACTIONS)


def _is_save_reference_call(tool: str, tool_input: Payload) -> bool:
    if SAVE_REFERENCE_RE.search(tool):
        return True
    return bool(
        REFERENCE_ACTION_RE.search(tool) and _action_name(tool_input) in REFERENCE_SAVE_ACTIONS
    )


def _is_validate_concept_call(tool: str, tool_input: Payload) -> bool:
    if VALIDATE_CONCEPT_RE.search(tool):
        return True
    return bool(
        VALIDATION_ACTION_RE.search(tool) and _action_name(tool_input) in VALIDATION_CONCEPT_ACTIONS
    )


DRAFT_FILE_RE = re.compile(r"projects/.*/drafts/.*\.md$")
CONCEPT_FILE_RE = re.compile(r"projects/.*/concept\.md$")
PROJECT_YAML_RE = re.compile(r"projects/.*/\.project\.yaml$")
STATE_FILE_RE = re.compile(r"\.(copilot-mode|mdpaper-state)\.json$")
GIT_COMMIT_RE = re.compile(r"git\s+commit")
PATCH_FILE_LINE_RE = re.compile(r"^\*\*\* (?:Update|Add|Delete) File: (.*)$")


def _draft_tool_context(tool: str, tool_input: Payload, workflow: str) -> str:
    if not _is_draft_write_call(tool, tool_input):
        return ""
    if workflow == LIBRARY_WIKI:
        return (
            "[LIBRARY-WIKI NOTE] Draft tool used while the active project is library-wiki. "
            "Confirm manuscript transition before requiring writing hooks or "
            "concept-validation gates."
        )
    return (
        f"[WRITING HOOKS REQUIRED] Draft modified via {tool}. You MUST run "
        'run_quality_checks(action="writing_hooks", hooks="post-write") '
        '(or run_quality_checks(action="repair_plan")) to check A1-A6 + A3b before proceeding. '
        "This is Code-Enforced and cannot be skipped."
    )


def _draft_file_context(file_path: str, workflow: str) -> str:
    if workflow == LIBRARY_WIKI:
        return (
            f"[LIBRARY-WIKI NOTE] Draft-area note '{file_path}' was edited while the active "
            "project is library-wiki. Manuscript writing hooks are optional until "
            "workflow_mode switches to manuscript."
        )
    return (
        f"[WRITING HOOKS REQUIRED] Draft file '{file_path}' was edited directly. Run "
        'run_quality_checks(action="writing_hooks", hooks="post-write") to check A1-A6 + A3b.'
    )


def _concept_file_context(workflow: str) -> str:
    if workflow == LIBRARY_WIKI:
        return (
            "[LIBRARY WORKSPACE UPDATED] concept.md is acting as the library workspace seed in "
            "library-wiki mode. Novelty validation is not required unless you switch to "
            "manuscript."
        )
    return (
        '[CONCEPT CHANGED] concept.md was modified. Remember: validation_action(action="concept") '
        "must pass (novelty ≥ 75) before any draft writing."
    )


def _edited_file_context(file_path: str, workflow: str, context: str) -> str:
    """Later matches override earlier ones, except the draft hint which never overrides."""
    normalized = normalize_slashes(file_path)
    if DRAFT_FILE_RE.search(normalized) and not context:
        context = _draft_file_context(file_path, workflow)
    if CONCEPT_FILE_RE.search(normalized):
        context = _concept_file_context(workflow)
    if PROJECT_YAML_RE.search(normalized):
        context = (
            '[PROJECT CONFIG CHANGED] .project.yaml was modified. Run project_action(action="current") '
            "to verify the changes are correct."
        )
    if STATE_FILE_RE.search(normalized):
        context = (
            "[STATE FILE CHANGED] Mode or workspace state was updated. The next SessionStart "
            "hook will pick up these changes."
        )
    if CROSS_PLATFORM_RE.search(normalized):
        context = (
            "[CROSS-PLATFORM SMOKE ADVISED] You changed installation, workflow, extension, or "
            f"path-resolution code at '{file_path}'. Before wrapping up, run the focused smoke "
            "checks or ensure the GitHub Actions cross-platform smoke matrix covers this change."
        )
    return context


def patch_paths(tool_input: Payload) -> list[str]:
    """File paths named by an ``apply_patch`` payload (``*** Update/Add/Delete File:``)."""
    paths: list[str] = []
    for line in alt(tool_input.get("input")).splitlines():
        found = PATCH_FILE_LINE_RE.match(line)
        if found and found.group(1):
            paths.append(found.group(1).split(" ")[0])
    return paths


def _patch_context(tool: str, tool_input: Payload, context: str) -> str:
    if not APPLY_PATCH_RE.search(tool):
        return context
    if any(CROSS_PLATFORM_RE.search(normalize_slashes(p)) for p in patch_paths(tool_input)):
        return (
            "[CROSS-PLATFORM SMOKE ADVISED] You modified installation, workflow, extension, or "
            "path-resolution files via apply_patch. Before wrapping up, run focused smoke tests "
            "or confirm the GitHub Actions cross-platform smoke matrix covers this change."
        )
    return context


def _file_edit_context(tool: str, tool_input: Payload, workflow: str, context: str) -> str:
    if not FILE_EDIT_RE.search(tool):
        return context
    file_path = first_alt(tool_input.get("filePath"), tool_input.get("path"))
    if file_path:
        return _edited_file_context(file_path, workflow, context)
    return _patch_context(tool, tool_input, context)


def _reference_saved_context(workflow: str) -> str:
    if workflow == LIBRARY_WIKI:
        return (
            "[REFERENCE SAVED] Reference saved into a library-wiki project. Consider "
            "refreshing knowledge pages, synthesis notes, or dashboard views next."
        )
    return (
        '[REFERENCE SAVED] Reference saved. Use draft_action(action="list_citations") or '
        'reference_action(action="evidence_pack") to see citation keys and findings for drafts.'
    )


def _concept_validated_context(workflow: str) -> str:
    if workflow == LIBRARY_WIKI:
        return (
            '[MANUSCRIPT CHECK IN LIBRARY MODE] validation_action(action="concept") was run inside a '
            "library-wiki project. If you are moving toward drafting, switch workflow_mode to "
            "manuscript so later gates apply."
        )
    return (
        "[CONCEPT VALIDATED] Check the novelty score. If < 75, concept needs improvement "
        "before drafting. Consider CGU tools (cgu_frame, cgu_diverge, cgu_judge) for enhancement."
    )


def _mcp_tool_context(tool: str, tool_input: Payload, workflow: str, context: str) -> str:
    if _is_insert_citation_call(tool, tool_input):
        context = (
            "[CITATION ADDED] After inserting citations, remember to run "
            'draft_action(action="sync_references") when done to generate the References section.'
        )
    if _is_save_reference_call(tool, tool_input):
        context = _reference_saved_context(workflow)
    return context


def _commit_context(tool: str, tool_input: Payload, context: str) -> str:
    if TERMINAL_RE.search(tool) and GIT_COMMIT_RE.search(alt(tool_input.get("command"))):
        return (
            "[POST-COMMIT] Git commit detected. Remember to: 1) Update memory-bank "
            '(progress.md, activeContext.md), 2) workspace_state_action(action="sync"), '
            "3) Consider CHANGELOG update."
        )
    return context


def build_context(tool: str, tool_input: Payload, workflow: str) -> str:
    """Reminder text for a finished tool call (the last matching rule wins)."""
    context = _draft_tool_context(tool, tool_input, workflow)
    context = _file_edit_context(tool, tool_input, workflow, context)
    context = _mcp_tool_context(tool, tool_input, workflow, context)
    context = _commit_context(tool, tool_input, context)
    if _is_validate_concept_call(tool, tool_input):
        context = _concept_validated_context(workflow)
    return context


def run(payload: Payload, ctx: HookContext) -> HookResult:
    tool = get_tool_name(payload)
    if not tool:
        return None
    context = build_context(tool, get_tool_input(payload), active_workflow_mode(ctx.workspace_root))
    append_audit(ctx, "post_tool_use", tool=tool)
    return build_output(EVENT, context) if context else None
