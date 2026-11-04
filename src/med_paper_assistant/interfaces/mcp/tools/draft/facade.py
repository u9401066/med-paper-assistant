"""Consolidated draft facade tools."""

from __future__ import annotations

from typing import Optional

from mcp.server import MCPServer

from med_paper_assistant.infrastructure.services.drafter import (
    draft_filename_from_section,
    normalize_draft_filename,
)

from .._shared import (
    facade_schema_json,
    invoke_tool_handler,
    normalize_facade_action,
)
from .facade_hooks import _auto_run_post_write_hooks, _infer_section_name
from .facade_specs import (
    DRAFT_ACTION_ALIASES,
    ActionSpec,
    DraftArgs,
    ToolGroups,
    ToolMap,
    build_action_specs,
)


def _write_arguments(args: DraftArgs) -> tuple[str, str, str]:
    """Resolve write inputs; return (filename, content, error)."""
    write_filename = args.filename.strip() or draft_filename_from_section(args.section)
    write_content = args.content or args.new_text or args.notes
    if not write_filename:
        return "", "", "❌ Write action requires either `filename` or `section`."
    if not write_content.strip():
        return "", "", "❌ Write action requires non-empty `content`."
    try:
        write_filename = normalize_draft_filename(write_filename)
    except ValueError as e:
        return "", "", f"❌ Invalid draft filename: {e}"
    return write_filename, write_content, ""


def _count_words_arguments(args: DraftArgs) -> tuple[str, Optional[str], str]:
    """Resolve count_words inputs; return (filename, section, error)."""
    count_filename = args.filename.strip()
    count_section = args.section or None
    if not count_filename and args.section:
        count_filename = draft_filename_from_section(args.section)
        count_section = None
    if not count_filename:
        return "", None, "❌ Count words requires either `filename` or `section`."
    try:
        count_filename = normalize_draft_filename(count_filename)
    except ValueError as e:
        return "", None, f"❌ Invalid draft filename: {e}"
    return count_filename, count_section, ""


def _action_schema(action_specs: dict[str, ActionSpec]) -> str:
    return facade_schema_json(
        tool="draft_action",
        actions={
            name: {"handler": spec[1], "params": sorted(k for k in spec[2])}
            for name, spec in sorted(action_specs.items())
        },
        aliases=DRAFT_ACTION_ALIASES,
        notes=["Use action='list_drafts' to list draft files."],
    )


def _unsupported_action_message(
    action: str, normalized: str, action_specs: dict[str, ActionSpec]
) -> str:
    supported = ", ".join(sorted(action_specs))
    if normalized in {"review_asset", "review_asset_for_insertion"}:
        return (
            f"❌ Unsupported draft action '{action}'. "
            'Use `analysis_action(action="review_asset")` for '
            "figure/table asset review."
        )
    return f"❌ Unsupported action '{action}'. Supported actions: {supported}"


def _post_write_suffix(
    normalized: str, result_text: str, args: DraftArgs, write_filename: str, write_content: str
) -> str:
    if normalized not in {
        "write",
        "patch",
        "insert_figure",
        "insert_table",
    } or result_text.lstrip().startswith("❌"):
        return ""
    hook_filename = write_filename if normalized == "write" else args.filename
    if normalized in {"insert_figure", "insert_table"}:
        hook_filename = args.draft_filename or "manuscript.md"
    hook_section = _infer_section_name(hook_filename, args.section)
    hook_hint = write_content if normalized == "write" else (args.new_text or args.content)
    return _auto_run_post_write_hooks(
        project=args.project,
        filename=hook_filename,
        section=hook_section,
        content_hint=hook_hint,
    )


async def _draft_action(groups: ToolGroups, args: DraftArgs) -> str:
    normalized = normalize_facade_action(args.action, DRAFT_ACTION_ALIASES)

    write_filename, write_content = args.filename, args.content
    count_filename, count_section = args.filename, args.section or None

    if normalized == "write":
        write_filename, write_content, error = _write_arguments(args)
        if error:
            return error

    if normalized == "count_words":
        count_filename, count_section, error = _count_words_arguments(args)
        if error:
            return error

    action_specs = build_action_specs(
        groups, args, write_filename, write_content, count_filename, count_section
    )

    if normalized == "list":
        return _action_schema(action_specs)

    if normalized not in action_specs:
        return _unsupported_action_message(args.action, normalized, action_specs)

    tool_group, handler_name, kwargs = action_specs[normalized]
    handler = tool_group.get(handler_name)
    if handler is None:
        return f"❌ Draft facade misconfigured: missing handler '{handler_name}'"

    result_text = str(await invoke_tool_handler(handler, **kwargs))
    return result_text + _post_write_suffix(
        normalized, result_text, args, write_filename, write_content
    )


def register_draft_facade_tools(
    mcp: MCPServer,
    writing_tools: ToolMap,
    template_tools: ToolMap,
    editing_tools: ToolMap,
    citation_tools: ToolMap,
    figure_tools: Optional[ToolMap] = None,
):
    """Register stable public verbs for manuscript drafting workflows."""

    groups = ToolGroups(
        writing=writing_tools or {},
        template=template_tools or {},
        editing=editing_tools or {},
        citation=citation_tools or {},
        figure=figure_tools or {},
    )

    @mcp.tool()
    async def draft_action(
        action: str,
        filename: str = "",
        caption: str = "",
        figure_number: int = 0,
        table_number: int = 0,
        draft_filename: str = "",
        after_section: str = "",
        content: str = "",
        table_content: str = "",
        topic: str = "",
        notes: str = "",
        target_text: str = "",
        pmid: str = "",
        section: str = "",
        old_text: str = "",
        new_text: str = "",
        claim_type: str = "general",
        max_results: int = 5,
        search_pubmed: bool = True,
        confirm: bool = False,
        project: Optional[str] = None,
    ) -> str:
        """
        Run manuscript drafting actions through one stable entrypoint.

        Actions:
        - check_order
        - draft_section
        - write
        - list
        - read
        - delete
        - insert_citation
        - sync_references
        - count_words
        - list_citations
        - patch
        - suggest_citations
        - scan_citations
        - insert_figure
        - insert_table
        - list_assets
        """
        return await _draft_action(
            groups,
            DraftArgs(
                action=action,
                filename=filename,
                caption=caption,
                figure_number=figure_number,
                table_number=table_number,
                draft_filename=draft_filename,
                after_section=after_section,
                content=content,
                table_content=table_content,
                topic=topic,
                notes=notes,
                target_text=target_text,
                pmid=pmid,
                section=section,
                old_text=old_text,
                new_text=new_text,
                claim_type=claim_type,
                max_results=max_results,
                search_pubmed=search_pubmed,
                confirm=confirm,
                project=project,
            ),
        )

    return {"draft_action": draft_action}


__all__ = ["register_draft_facade_tools"]
