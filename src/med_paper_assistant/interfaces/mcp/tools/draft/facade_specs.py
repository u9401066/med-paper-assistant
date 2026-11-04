"""Request model, aliases and action specs for the consolidated draft facade."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Optional

ToolMap = Mapping[str, Callable[..., Any]]
ActionSpec = tuple[ToolMap, str, dict[str, Any]]

DRAFT_ACTION_ALIASES = {
    "order": "check_order",
    "check_writing_order": "check_order",
    "section": "draft_section",
    "create": "write",
    "update": "write",
    "write_draft": "write",
    "actions": "list",
    "help": "list",
    "list": "list",
    "list_drafts": "list_drafts",
    "read_draft": "read",
    "delete_draft": "delete",
    "cite": "insert_citation",
    "sync": "sync_references",
    "words": "count_words",
    "citations": "list_citations",
    "available_citations": "list_citations",
    "get_available_citations": "list_citations",
    "edit": "patch",
    "patch_draft": "patch",
    "suggest": "suggest_citations",
    "scan_draft_citations": "scan_citations",
    "scan": "scan_citations",
    "review_asset_for_insertion": "review_asset",
    "review_asset": "review_asset",
    "review": "review_asset",
    "figure": "insert_figure",
    "table": "insert_table",
    "assets": "list_assets",
    "asset": "list_assets",
}


@dataclass(frozen=True)
class ToolGroups:
    writing: ToolMap
    template: ToolMap
    editing: ToolMap
    citation: ToolMap
    figure: ToolMap


@dataclass(frozen=True)
class DraftArgs:
    """Arguments of the draft_action tool."""

    action: str
    filename: str = ""
    caption: str = ""
    figure_number: int = 0
    table_number: int = 0
    draft_filename: str = ""
    after_section: str = ""
    content: str = ""
    table_content: str = ""
    topic: str = ""
    notes: str = ""
    target_text: str = ""
    pmid: str = ""
    section: str = ""
    old_text: str = ""
    new_text: str = ""
    claim_type: str = "general"
    max_results: int = 5
    search_pubmed: bool = True
    confirm: bool = False
    project: Optional[str] = None


def _writing_specs(
    groups: ToolGroups, args: DraftArgs, write_filename: str, write_content: str
) -> dict[str, ActionSpec]:
    project = args.project
    return {
        "check_order": (groups.writing, "check_writing_order", {"project": project}),
        "draft_section": (
            groups.writing,
            "draft_section",
            {"topic": args.topic, "notes": args.notes or args.content, "project": project},
        ),
        "write": (
            groups.writing,
            "write_draft",
            {"filename": write_filename, "content": write_content, "project": project},
        ),
        "list_drafts": (groups.writing, "list_drafts", {"project": project}),
        "read": (
            groups.writing,
            "read_draft",
            {"filename": args.filename, "project": project},
        ),
        "delete": (
            groups.writing,
            "delete_draft",
            {"filename": args.filename, "confirm": args.confirm, "project": project},
        ),
    }


def _template_specs(
    groups: ToolGroups, args: DraftArgs, count_filename: str, count_section: Optional[str]
) -> dict[str, ActionSpec]:
    project = args.project
    return {
        "insert_citation": (
            groups.template,
            "insert_citation",
            {
                "filename": args.filename,
                "target_text": args.target_text,
                "pmid": args.pmid,
                "project": project,
            },
        ),
        "sync_references": (
            groups.template,
            "sync_references",
            {"filename": args.filename, "project": project},
        ),
        "count_words": (
            groups.template,
            "count_words",
            {"filename": count_filename, "section": count_section, "project": project},
        ),
    }


def _editing_citation_specs(groups: ToolGroups, args: DraftArgs) -> dict[str, ActionSpec]:
    project = args.project
    return {
        "list_citations": (
            groups.editing,
            "get_available_citations",
            {"project": project},
        ),
        "patch": (
            groups.editing,
            "patch_draft",
            {
                "filename": args.filename,
                "old_text": args.old_text,
                "new_text": args.new_text or args.content,
                "project": project,
            },
        ),
        "suggest_citations": (
            groups.citation,
            "suggest_citations",
            {
                "text": args.content or args.notes,
                "section": args.section,
                "claim_type": args.claim_type,
                "max_results": args.max_results,
                "search_pubmed": args.search_pubmed,
                "project": project,
            },
        ),
        "scan_citations": (
            groups.citation,
            "scan_draft_citations",
            {"filename": args.filename, "project": project},
        ),
    }


def _figure_specs(groups: ToolGroups, args: DraftArgs) -> dict[str, ActionSpec]:
    project = args.project
    return {
        "insert_figure": (
            groups.figure,
            "insert_figure",
            {
                "filename": args.filename,
                "caption": args.caption,
                "figure_number": args.figure_number or None,
                "draft_filename": args.draft_filename or None,
                "after_section": args.after_section or None,
                "project": project,
            },
        ),
        "insert_table": (
            groups.figure,
            "insert_table",
            {
                "filename": args.filename,
                "caption": args.caption,
                "table_number": args.table_number or None,
                "table_content": args.table_content or None,
                "draft_filename": args.draft_filename or None,
                "after_section": args.after_section or None,
                "project": project,
            },
        ),
        "list_assets": (
            groups.figure,
            "list_assets",
            {"project": project},
        ),
    }


def build_action_specs(
    groups: ToolGroups,
    args: DraftArgs,
    write_filename: str,
    write_content: str,
    count_filename: str,
    count_section: Optional[str],
) -> dict[str, ActionSpec]:
    specs = {
        **_writing_specs(groups, args, write_filename, write_content),
        **_template_specs(groups, args, count_filename, count_section),
        **_editing_citation_specs(groups, args),
    }
    if groups.figure:
        specs.update(_figure_specs(groups, args))
    return specs
