"""``library_action`` facade handler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..._shared import invoke_tool_handler, normalize_facade_action
from .deps import FACADE_DEPS, FacadeDeps

LIBRARY_ALIASES = {
    "list": "list_notes",
    "read": "read_note",
    "write": "write_note",
    "move": "move_note",
    "triage": "triage_note",
    "metadata": "update_metadata",
    "frontmatter": "update_metadata",
    "search": "search_notes",
    "queues": "show_queues",
    "concept": "create_concept",
    "materialize": "materialize_concept",
    "path": "explain_path",
    "dashboard": "build_dashboard",
}

LibrarySpec = tuple[str, dict[str, Any]]


@dataclass(frozen=True)
class LibraryActionArgs:
    """The ``library_action`` tool parameters, captured once per call."""

    action: str
    section: str
    from_section: str
    to_section: str
    filename: str
    content: str
    title: str
    tags_csv: str
    add_tags_csv: str
    remove_tags_csv: str
    related_notes_csv: str
    source_notes_csv: str
    template: str
    note_type: str
    status: str
    query: str
    queue: str
    view: str
    limit: int
    source_note: str
    target_note: str
    project: Optional[str]


def _note_io_specs(a: LibraryActionArgs) -> dict[str, LibrarySpec]:
    return {
        "list_notes": (
            "list_library_notes",
            {"section": a.section, "project": a.project},
        ),
        "read_note": (
            "read_library_note",
            {"section": a.section, "filename": a.filename, "project": a.project},
        ),
        "write_note": (
            "write_library_note",
            {
                "section": a.section,
                "filename": a.filename,
                "content": a.content,
                "title": a.title,
                "tags_csv": a.tags_csv,
                "template": a.template,
                "source_notes_csv": a.source_notes_csv,
                "related_notes_csv": a.related_notes_csv,
                "status": a.status,
                "project": a.project,
            },
        ),
        "move_note": (
            "move_library_note",
            {
                "filename": a.filename,
                "from_section": a.from_section,
                "to_section": a.to_section,
                "project": a.project,
            },
        ),
    }


def _note_curation_specs(a: LibraryActionArgs) -> dict[str, LibrarySpec]:
    return {
        "triage_note": (
            "triage_library_note",
            {
                "note_ref": a.source_note or a.filename,
                "target_section": a.to_section or (a.section if a.section != "all" else ""),
                "status": a.status,
                "tags_csv": a.tags_csv,
                "related_notes_csv": a.related_notes_csv,
                "project": a.project,
            },
        ),
        "update_metadata": (
            "update_library_note_metadata",
            {
                "note_ref": a.source_note or a.filename,
                "title": a.title,
                "status": a.status,
                "tags_csv": a.tags_csv,
                "add_tags_csv": a.add_tags_csv,
                "remove_tags_csv": a.remove_tags_csv,
                "related_notes_csv": a.related_notes_csv,
                "note_type": a.note_type,
                "project": a.project,
            },
        ),
        "search_notes": (
            "search_library_notes",
            {"query": a.query, "section": a.section, "project": a.project},
        ),
        "show_queues": (
            "show_reading_queues",
            {"queue": a.queue, "limit": a.limit, "project": a.project},
        ),
    }


def _concept_and_dashboard_specs(a: LibraryActionArgs) -> dict[str, LibrarySpec]:
    return {
        "create_concept": (
            "create_concept_page",
            {
                "filename": a.filename,
                "title": a.title,
                "summary": a.content,
                "source_notes_csv": a.source_notes_csv or a.query,
                "tags_csv": a.tags_csv,
                "open_questions": a.status,
                "project": a.project,
            },
        ),
        "materialize_concept": (
            "materialize_concept_page",
            {
                "filename": a.filename,
                "title": a.title,
                "summary": a.content,
                "source_notes_csv": a.source_notes_csv or a.query or a.source_note,
                "tags_csv": a.tags_csv,
                "open_questions": a.status,
                "project": a.project,
            },
        ),
        "explain_path": (
            "explain_library_path",
            {
                "source_note": a.source_note or a.filename,
                "target_note": a.target_note or a.query,
                "project": a.project,
            },
        ),
        "build_dashboard": (
            "build_library_dashboard",
            {"view": a.view, "limit": a.limit, "project": a.project},
        ),
    }


def _build_library_specs(a: LibraryActionArgs) -> dict[str, LibrarySpec]:
    return {
        **_note_io_specs(a),
        **_note_curation_specs(a),
        **_concept_and_dashboard_specs(a),
    }


async def _dispatch_library_action(args: LibraryActionArgs, deps: FacadeDeps) -> str:
    normalized = normalize_facade_action(args.action, LIBRARY_ALIASES)
    action_specs = _build_library_specs(args)

    if normalized not in action_specs:
        supported = ", ".join(sorted(action_specs))
        return f"❌ Unsupported action '{args.action}'. Supported actions: {supported}"

    handler_name, kwargs = action_specs[normalized]
    handler = deps.library_tools.get(handler_name)
    if handler is None:
        return f"❌ Library facade misconfigured: missing handler '{handler_name}'"

    return await invoke_tool_handler(handler, **kwargs)


async def library_action(
    action: str,
    section: str = "all",
    from_section: str = "",
    to_section: str = "",
    filename: str = "",
    content: str = "",
    title: str = "",
    tags_csv: str = "",
    add_tags_csv: str = "",
    remove_tags_csv: str = "",
    related_notes_csv: str = "",
    source_notes_csv: str = "",
    template: str = "",
    note_type: str = "",
    status: str = "",
    query: str = "",
    queue: str = "all",
    view: str = "overview",
    limit: int = 10,
    source_note: str = "",
    target_note: str = "",
    project: Optional[str] = None,
) -> str:
    """
    Run library-wiki note and dashboard actions through one stable entrypoint.

    Actions:
    - list_notes
    - read_note
    - write_note
    - move_note
    - triage_note
    - update_metadata
    - search_notes
    - show_queues
    - create_concept
    - materialize_concept
    - explain_path
    - build_dashboard
    """
    args = LibraryActionArgs(**locals())
    return await _dispatch_library_action(args, FACADE_DEPS.get())
