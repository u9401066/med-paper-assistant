"""Handlers that triage, annotate, search and queue library notes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..._shared import (
    log_tool_call,
    log_tool_error,
    log_tool_result,
)
from ..library_note_support import default_status as _default_status
from .constants import ALLOWED_LIBRARY_SECTIONS, TRIAGE_PROGRESSION
from .content import (
    _ensure_frontmatter_defaults,
    _parse_frontmatter,
    _render_note_content,
    _rewrite_frontmatter,
)
from .context import _require_library_project
from .index import _collect_notes, _resolve_note_reference_or_error
from .normalize import (
    _current_timestamp,
    _dedupe_text_values,
    _normalize_related_note_refs,
    _normalize_section,
    _resolve_section_dir,
    _split_multivalue,
)


def _triage_next_status(status: str, resolved_target: str, source_note: dict[str, Any]) -> str:
    next_status = status.strip()
    if next_status:
        return next_status
    if resolved_target != source_note["section"]:
        return _default_status(resolved_target)
    return source_note["status_display"] or source_note["status"]


def _write_triaged_note(
    source_path: Path,
    target_path: Path,
    source_note: dict[str, Any],
    updates: dict[str, Any],
) -> None:
    content = source_path.read_text(encoding="utf-8")
    updated_content = _rewrite_frontmatter(content, updates, section=source_note["section"])
    target_path.write_text(updated_content, encoding="utf-8")
    if source_path != target_path:
        source_path.unlink()


def triage_library_note(
    note_ref: str,
    target_section: str = "",
    status: str = "",
    tags_csv: str = "",
    related_notes_csv: str = "",
    project: Optional[str] = None,
) -> str:
    """Advance a library note through inbox/concepts/projects with optional metadata updates."""
    log_tool_call(
        "triage_library_note",
        {
            "note_ref": note_ref,
            "target_section": target_section,
            "project": project,
        },
    )

    if not note_ref.strip():
        return "❌ note_ref cannot be empty."

    info, error_msg = _require_library_project("triage_library_note", project)
    if info is None:
        return error_msg

    notes = _collect_notes(info, ALLOWED_LIBRARY_SECTIONS)
    if not notes:
        return "No library notes yet. Use `write_library_note` first."

    source_note, error_msg = _resolve_note_reference_or_error(note_ref, notes)
    if source_note is None:
        return error_msg

    resolved_target = (
        _normalize_section(target_section)
        if target_section.strip()
        else TRIAGE_PROGRESSION[source_note["section"]]
    )
    if resolved_target not in ALLOWED_LIBRARY_SECTIONS:
        allowed = ", ".join(ALLOWED_LIBRARY_SECTIONS)
        return f"❌ Invalid target section '{target_section}'. Use one of: {allowed}."

    merged_tags = _dedupe_text_values(
        list(source_note.get("tags", [])) + _split_multivalue(tags_csv)
    )
    merged_related = _normalize_related_note_refs(
        list(source_note.get("related_notes", [])) + _split_multivalue(related_notes_csv)
    )
    has_metadata_changes = bool(status.strip() or tags_csv.strip() or related_notes_csv.strip())
    if resolved_target == source_note["section"] and not has_metadata_changes:
        return f"Note already sits in the final triage section: {source_note['section']}/{source_note['filename']}."

    target_dir, error_msg = _resolve_section_dir(info, resolved_target)
    if target_dir is None:
        return error_msg

    source_path = Path(source_note["path"])
    target_path = target_dir / source_note["filename"]
    if source_path != target_path and target_path.exists():
        result = f"❌ Target note already exists: {target_path.name} in {target_dir.name}/"
        log_tool_result("triage_library_note", result, success=False)
        return result

    next_status = _triage_next_status(status, resolved_target, source_note)

    try:
        _write_triaged_note(
            source_path,
            target_path,
            source_note,
            {
                "section": resolved_target,
                "status": next_status,
                "tags": merged_tags,
                "related_notes": merged_related,
                "updated_at": _current_timestamp(),
            },
        )
    except Exception as exc:
        log_tool_error(
            "triage_library_note",
            exc,
            {"source": str(source_path), "target": str(target_path)},
        )
        return f"❌ Error triaging note: {exc}"

    log_tool_result(
        "triage_library_note",
        f"triaged {source_note['filename']} to {resolved_target}",
        success=True,
    )
    return (
        f"✅ Library note triaged successfully.\n\n"
        f"**File:** {source_note['filename']}\n"
        f"**From:** {source_note['section']}/\n"
        f"**To:** {resolved_target}/\n"
        f"**Status:** {next_status}\n"
        f"**Path:** {target_path}"
    )


def _patch_note_metadata(
    note: dict[str, Any],
    note_path: Path,
    *,
    title: str,
    status: str,
    tags_csv: str,
    add_tags_csv: str,
    remove_tags_csv: str,
    related_notes_csv: str,
    note_type: str,
) -> tuple[list[str], list[str]]:
    """Rewrite the note frontmatter in place; return the resulting tags and related notes."""
    content = note_path.read_text(encoding="utf-8")
    frontmatter, body = _parse_frontmatter(content)
    updated_frontmatter = _ensure_frontmatter_defaults(
        frontmatter,
        fallback_title=note["title"],
        section=note["section"],
    )

    current_tags = (
        _dedupe_text_values(_split_multivalue(tags_csv))
        if tags_csv.strip()
        else list(updated_frontmatter.get("tags", []))
    )
    current_tags = _dedupe_text_values(current_tags + _split_multivalue(add_tags_csv))
    removals = {tag.lower() for tag in _split_multivalue(remove_tags_csv)}
    if removals:
        current_tags = [tag for tag in current_tags if tag.lower() not in removals]

    merged_related = _normalize_related_note_refs(
        list(updated_frontmatter.get("related_notes", [])) + _split_multivalue(related_notes_csv)
    )

    if title.strip():
        updated_frontmatter["title"] = title.strip()
    if status.strip():
        updated_frontmatter["status"] = status.strip()
    if note_type.strip():
        updated_frontmatter["type"] = note_type.strip()
    updated_frontmatter["tags"] = current_tags
    updated_frontmatter["related_notes"] = merged_related
    updated_frontmatter["updated_at"] = _current_timestamp()

    note_path.write_text(_render_note_content(updated_frontmatter, body), encoding="utf-8")
    return current_tags, merged_related


def update_library_note_metadata(
    note_ref: str,
    title: str = "",
    status: str = "",
    tags_csv: str = "",
    add_tags_csv: str = "",
    remove_tags_csv: str = "",
    related_notes_csv: str = "",
    note_type: str = "",
    project: Optional[str] = None,
) -> str:
    """Patch library note frontmatter metadata without resubmitting the full note body."""
    log_tool_call(
        "update_library_note_metadata",
        {"note_ref": note_ref, "project": project},
    )

    if not note_ref.strip():
        return "❌ note_ref cannot be empty."
    if not any(
        [
            title.strip(),
            status.strip(),
            tags_csv.strip(),
            add_tags_csv.strip(),
            remove_tags_csv.strip(),
            related_notes_csv.strip(),
            note_type.strip(),
        ]
    ):
        return "❌ No metadata changes requested. Provide title, status, tags, add/remove tags, related notes, or note type."

    info, error_msg = _require_library_project("update_library_note_metadata", project)
    if info is None:
        return error_msg

    notes = _collect_notes(info, ALLOWED_LIBRARY_SECTIONS)
    if not notes:
        return "No library notes yet. Use `write_library_note` first."

    note, error_msg = _resolve_note_reference_or_error(note_ref, notes)
    if note is None:
        return error_msg

    note_path = Path(note["path"])
    try:
        current_tags, merged_related = _patch_note_metadata(
            note,
            note_path,
            title=title,
            status=status,
            tags_csv=tags_csv,
            add_tags_csv=add_tags_csv,
            remove_tags_csv=remove_tags_csv,
            related_notes_csv=related_notes_csv,
            note_type=note_type,
        )
    except Exception as exc:
        log_tool_error("update_library_note_metadata", exc, {"path": str(note_path)})
        return f"❌ Error updating note metadata: {exc}"

    log_tool_result(
        "update_library_note_metadata",
        f"updated metadata for {note['filename']}",
        success=True,
    )
    return (
        f"✅ Library note metadata updated successfully.\n\n"
        f"**File:** {note['filename']}\n"
        f"**Section:** {note['section']}\n"
        f"**Tags:** {', '.join(current_tags) if current_tags else '[none]'}\n"
        f"**Related notes:** {len(merged_related)}\n"
        f"**Path:** {note_path}"
    )
