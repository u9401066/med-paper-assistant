"""Handlers that create and materialize concept pages."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Optional

from med_paper_assistant.shared.path_guard import PathGuardError
from med_paper_assistant.shared.yaml_escape import escape_yaml_value as _yaml_escape

from ..._shared import (
    log_tool_call,
    log_tool_error,
    log_tool_result,
)
from .constants import ALLOWED_LIBRARY_SECTIONS
from .content import _rewrite_frontmatter
from .context import _require_library_project
from .index import _collect_notes, _resolve_note_reference_or_error
from .normalize import (
    _current_timestamp,
    _dedupe_text_values,
    _default_title_from_filename,
    _normalize_filename,
    _normalize_note_reference,
    _normalize_related_note_refs,
    _resolve_note_path,
    _resolve_section_dir,
    _slugify_filename_candidate,
    _split_multivalue,
)


def _concept_body_lines(
    summary: str, source_links: list[str], question_lines: list[str]
) -> list[str]:
    body_lines = [
        "## Summary",
        "",
        summary.strip() or "[Add concept summary]",
        "",
        "## Source Notes",
        "",
    ]
    if source_links:
        body_lines.extend(f"- {link}" for link in source_links)
    else:
        body_lines.append("- [Add linked source notes]")

    body_lines.extend(
        [
            "",
            "## Key Claims",
            "",
            "- [Claim 1]",
            "",
            "## Evidence Gaps",
            "",
            "- [Gap or contradiction]",
            "",
            "## Open Questions",
            "",
        ]
    )
    if question_lines:
        body_lines.extend(f"- {line}" for line in question_lines)
    else:
        body_lines.append("- [Open question]")
    return body_lines


def _concept_frontmatter_lines(
    resolved_title: str, tags: list[str], source_refs: list[str]
) -> list[str]:
    frontmatter_lines = [
        "---",
        f'title: "{_yaml_escape(resolved_title)}"',
        'type: "library-concept"',
        'section: "concepts"',
        'status: "curated"',
    ]
    if tags:
        frontmatter_lines.append("tags:")
        for tag in tags:
            frontmatter_lines.append(f'  - "{_yaml_escape(tag)}"')
    else:
        frontmatter_lines.append("tags: []")
    if source_refs:
        frontmatter_lines.append("related_notes:")
        for ref in source_refs:
            frontmatter_lines.append(f'  - "{_yaml_escape(ref)}"')
    else:
        frontmatter_lines.append("related_notes: []")
    frontmatter_lines.extend(
        [
            f'updated_at: "{_current_timestamp()}"',
            "---",
            "",
            f"# {resolved_title}",
            "",
        ]
    )
    return frontmatter_lines


def create_concept_page(
    filename: str,
    title: str,
    summary: str = "",
    source_notes_csv: str = "",
    tags_csv: str = "",
    open_questions: str = "",
    project: Optional[str] = None,
) -> str:
    """Create or update a structured concept page under concepts/."""
    log_tool_call(
        "create_concept_page",
        {"filename": filename, "title": title, "project": project},
    )

    info, error_msg = _require_library_project("create_concept_page", project)
    if info is None:
        return error_msg

    concepts_dir, error_msg = _resolve_section_dir(info, "concepts")
    if concepts_dir is None:
        return error_msg

    try:
        normalized_filename = _normalize_filename(filename)
    except ValueError as exc:
        return f"❌ {exc}"

    note_path = _resolve_note_path(concepts_dir, normalized_filename)
    note_exists = note_path.exists()
    tags = _dedupe_text_values(_split_multivalue(tags_csv))
    source_refs = _normalize_related_note_refs(_split_multivalue(source_notes_csv))
    source_links = [
        f"[[{_normalize_note_reference(ref).split(':', 1)[-1]}]]" for ref in source_refs
    ]
    question_lines = [line.strip() for line in open_questions.splitlines() if line.strip()]

    resolved_title = title.strip() or _default_title_from_filename(normalized_filename)
    body_lines = _concept_body_lines(summary, source_links, question_lines)
    frontmatter_lines = _concept_frontmatter_lines(resolved_title, tags, source_refs)

    final_content = "\n".join(frontmatter_lines + body_lines)
    if not final_content.endswith("\n"):
        final_content += "\n"

    try:
        note_path.write_text(final_content, encoding="utf-8")
    except Exception as exc:
        log_tool_error("create_concept_page", exc, {"path": str(note_path)})
        return f"❌ Error writing concept page: {exc}"

    action = "updated" if note_exists else "created"
    log_tool_result("create_concept_page", f"{action} {note_path.name}", success=True)
    return (
        f"✅ Concept page {action} successfully.\n\n"
        f"**File:** {note_path.name}\n"
        f"**Path:** {note_path}\n"
        f"**Linked source notes:** {len(source_links)}"
    )


def _resolve_source_notes(
    source_refs: list[str], notes: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str], str]:
    """Resolve unique source notes; the last item is a non-empty error message on failure."""
    source_notes: list[dict[str, Any]] = []
    normalized_refs: list[str] = []
    seen_note_ids: set[str] = set()
    for source_ref in source_refs:
        source_note, error_msg = _resolve_note_reference_or_error(source_ref, notes)
        if source_note is None:
            return [], [], error_msg
        if source_note["id"] in seen_note_ids:
            continue
        seen_note_ids.add(source_note["id"])
        source_notes.append(source_note)
        normalized_refs.append(source_note["id"])
    return source_notes, normalized_refs, ""


def _shared_source_tags(source_notes: list[dict[str, Any]]) -> list[str]:
    tag_counts = Counter(tag for note in source_notes for tag in note.get("tags", []))
    return sorted(tag for tag, count in tag_counts.items() if count == len(source_notes))


def _derive_concept_title(
    title: str, source_notes: list[dict[str, Any]], shared_tags: list[str]
) -> str:
    if title.strip():
        return title.strip()
    if len(source_notes) == 1:
        return f"{source_notes[0]['title']} Concept"
    if shared_tags:
        return f"{shared_tags[0].replace('-', ' ').title()} Concept"
    return "Materialized Concept"


def _derive_concept_filename(
    filename: str, source_notes: list[dict[str, Any]], shared_tags: list[str]
) -> str:
    if filename.strip():
        return filename
    if len(source_notes) == 1:
        return f"{source_notes[0]['stem']}-concept"
    if shared_tags:
        return f"{_slugify_filename_candidate(shared_tags[0])}-concept"
    return f"{_slugify_filename_candidate(source_notes[0]['stem'])}-concept"


def _derive_concept_summary(
    summary: str, source_notes: list[dict[str, Any]], shared_tags: list[str]
) -> str:
    resolved_summary = summary.strip()
    if resolved_summary:
        return resolved_summary
    if len(source_notes) == 1:
        source_note = source_notes[0]
        return (
            f"Derived from {source_note['title']} in {source_note['section']} to promote the idea into a reusable concept page. "
            f"Evidence snapshot: {source_note['excerpt']}"
        )
    source_sections = ", ".join(sorted({note["section"] for note in source_notes}))
    focus_hint = f" around {shared_tags[0]}" if shared_tags else ""
    return f"Derived from {len(source_notes)} library notes across {source_sections}{focus_hint} to capture a reusable concept for later synthesis."


def _next_source_status(source_note: dict[str, Any]) -> str:
    source_status = source_note["status_display"] or source_note["status"]
    if source_note["section"] == "inbox" and source_status.lower() in {
        "captured",
        "reading",
        "reviewing",
        "active",
        "in-progress",
    }:
        return "triaged"
    if source_note["section"] == "concepts" and source_status.lower() == "curated":
        return "linked"
    return source_status


def _link_source_to_concept(
    source_note: dict[str, Any], concept_ref: str, next_status: str
) -> None:
    source_path = Path(source_note["path"])
    source_content = source_path.read_text(encoding="utf-8")
    updated_source = _rewrite_frontmatter(
        source_content,
        {
            "status": next_status,
            "related_notes": _normalize_related_note_refs(
                list(source_note.get("related_notes", [])) + [concept_ref]
            ),
            "updated_at": _current_timestamp(),
        },
        section=source_note["section"],
    )
    source_path.write_text(updated_source, encoding="utf-8")


def materialize_concept_page(
    source_notes_csv: str,
    filename: str = "",
    title: str = "",
    summary: str = "",
    tags_csv: str = "",
    open_questions: str = "",
    project: Optional[str] = None,
) -> str:
    """Materialize a concept page from existing library note(s) and link the sources back to it."""
    log_tool_call(
        "materialize_concept_page",
        {"source_notes_csv": source_notes_csv, "project": project},
    )

    source_refs = _split_multivalue(source_notes_csv)
    if not source_refs:
        return "❌ source_notes_csv cannot be empty."

    info, error_msg = _require_library_project("materialize_concept_page", project)
    if info is None:
        return error_msg

    notes = _collect_notes(info, ALLOWED_LIBRARY_SECTIONS)
    if not notes:
        return "No library notes yet. Use `write_library_note` first."

    source_notes, normalized_refs, error_msg = _resolve_source_notes(source_refs, notes)
    if error_msg:
        return error_msg

    shared_tags = _shared_source_tags(source_notes)
    resolved_title = _derive_concept_title(title, source_notes, shared_tags)
    resolved_filename = _derive_concept_filename(filename, source_notes, shared_tags)
    resolved_summary = _derive_concept_summary(summary, source_notes, shared_tags)
    resolved_tags = _dedupe_text_values(
        [
            *_split_multivalue(tags_csv),
            *(tag for note in source_notes for tag in note.get("tags", [])),
            "concept",
        ]
    )

    # The registered create_concept_page tool turns path-guard failures into "❌" messages.
    try:
        concept_result = create_concept_page(
            filename=resolved_filename,
            title=resolved_title,
            summary=resolved_summary,
            source_notes_csv=",".join(normalized_refs),
            tags_csv=",".join(resolved_tags),
            open_questions=open_questions,
            project=project,
        )
    except PathGuardError as exc:
        concept_result = f"❌ {exc}"
    if concept_result.startswith("❌"):
        return concept_result

    concept_ref = f"concepts:{Path(_normalize_filename(resolved_filename)).stem.lower()}"
    promoted_sources = 0

    for source_note in source_notes:
        next_status = _next_source_status(source_note)
        try:
            _link_source_to_concept(source_note, concept_ref, next_status)
            promoted_sources += 1
        except Exception as exc:
            log_tool_error(
                "materialize_concept_page",
                exc,
                {"path": str(Path(source_note["path"])), "concept_ref": concept_ref},
            )
            return f"❌ Error linking source note back to concept: {exc}"

    log_tool_result(
        "materialize_concept_page",
        f"materialized {concept_ref} from {len(source_notes)} notes",
        success=True,
    )
    return (
        f"✅ Concept page materialized successfully.\n\n"
        f"**File:** {_normalize_filename(resolved_filename)}\n"
        f"**Title:** {resolved_title}\n"
        f"**Source notes:** {len(source_notes)}\n"
        f"**Linked sources updated:** {promoted_sources}\n\n"
        f"{concept_result}"
    )
