"""Handlers that list, read, write and move library notes."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..._shared import (
    log_tool_call,
    log_tool_error,
    log_tool_result,
)
from ..library_note_support import default_status as _default_status
from .constants import ALLOWED_LIBRARY_SECTIONS
from .content import _extract_title, _render_note_content, _rewrite_frontmatter
from .context import _require_library_project
from .normalize import (
    _current_timestamp,
    _dedupe_text_values,
    _default_note_type,
    _default_title_from_filename,
    _normalize_filename,
    _normalize_related_note_refs,
    _normalize_section,
    _normalize_template_name,
    _resolve_note_path,
    _resolve_section_dir,
    _split_multivalue,
)
from .templates import _render_template_body


def list_library_notes(section: str = "all", project: Optional[str] = None) -> str:
    """List markdown notes from inbox/concepts/projects in a library-wiki project."""
    log_tool_call("list_library_notes", {"section": section, "project": project})

    info, error_msg = _require_library_project("list_library_notes", project)
    if info is None:
        return error_msg

    normalized_section = _normalize_section(section, allow_all=True)
    sections = ALLOWED_LIBRARY_SECTIONS if normalized_section == "all" else (normalized_section,)

    output = [f"# Library Notes: {info.get('name', info.get('slug', 'Unknown'))}", ""]
    total_notes = 0

    for current_section in sections:
        section_dir, error_msg = _resolve_section_dir(info, current_section, create=False)
        if section_dir is None:
            return error_msg

        note_paths = sorted(p for p in section_dir.glob("*.md") if p.is_file())
        total_notes += len(note_paths)

        output.extend([f"## {current_section} ({len(note_paths)})", ""])
        if not note_paths:
            output.append("- [No notes yet]")
            output.append("")
            continue

        for note_path in note_paths:
            try:
                note_content = note_path.read_text(encoding="utf-8")
            except Exception:
                note_content = ""
            title = _extract_title(note_content, _default_title_from_filename(note_path.name))
            output.append(f"- {note_path.name}: {title}")
        output.append("")

    log_tool_result("list_library_notes", f"listed {total_notes} library notes", success=True)
    return "\n".join(output).strip()


def read_library_note(section: str, filename: str, project: Optional[str] = None) -> str:
    """Read a markdown note from inbox/concepts/projects."""
    log_tool_call(
        "read_library_note",
        {"section": section, "filename": filename, "project": project},
    )

    info, error_msg = _require_library_project("read_library_note", project)
    if info is None:
        return error_msg

    section_dir, error_msg = _resolve_section_dir(info, section, create=False)
    if section_dir is None:
        return error_msg

    try:
        note_path = _resolve_note_path(section_dir, _normalize_filename(filename))
    except ValueError as exc:
        return f"❌ {exc}"

    if not note_path.exists():
        result = f"❌ Note not found: {note_path.name} in {section_dir.name}/"
        log_tool_result("read_library_note", result, success=False)
        return result

    try:
        content = note_path.read_text(encoding="utf-8")
    except Exception as exc:
        log_tool_error("read_library_note", exc, {"path": str(note_path)})
        return f"❌ Error reading note: {exc}"

    log_tool_result("read_library_note", f"read {note_path.name}", success=True)
    return (
        f"# Library Note: {note_path.name}\n\n"
        f"**Project:** {info.get('name', info.get('slug', 'Unknown'))}\n"
        f"**Section:** {section_dir.name}\n"
        f"**Path:** {note_path}\n\n"
        f"---\n\n{content}"
    )


def _write_next_step(section_name: str) -> str:
    if section_name == "inbox":
        return (
            "\n\nNext step: review the note and move it into `concepts/` or `projects/` using "
            "`move_library_note` when it has been triaged."
        )
    if section_name == "daily":
        return "\n\nNext step: promote durable insights into `inbox/`, `concepts/`, or `review/` once the daily capture is ready."
    return ""


def _compose_note_content(
    content: str,
    *,
    section_name: str,
    filename: str,
    title: str,
    tags_csv: str,
    template: str,
    source_notes_csv: str,
    related_notes_csv: str,
    status: str,
) -> tuple[str, str]:
    """Return the note content to write and the normalized template name."""
    resolved_title = title.strip() or _default_title_from_filename(filename)
    resolved_status = status.strip() or _default_status(section_name)
    normalized_template = _normalize_template_name(template, section_name)
    tags = _dedupe_text_values(_split_multivalue(tags_csv))
    if normalized_template:
        tags = _dedupe_text_values([*tags, f"template/{normalized_template}"])
    source_refs = _normalize_related_note_refs(_split_multivalue(source_notes_csv))
    related_refs = _normalize_related_note_refs(_split_multivalue(related_notes_csv))
    merged_related = _normalize_related_note_refs([*source_refs, *related_refs])

    if content.lstrip().startswith("---\n"):
        return content, normalized_template

    frontmatter = {
        "title": resolved_title,
        "type": _default_note_type(section_name, normalized_template),
        "section": section_name,
        "status": resolved_status,
        "tags": tags,
        "related_notes": merged_related,
        "updated_at": _current_timestamp(),
    }
    body = _render_template_body(
        normalized_template,
        title=resolved_title,
        content=content,
        source_refs=source_refs,
        related_refs=related_refs,
    )
    return _render_note_content(frontmatter, body), normalized_template


def write_library_note(
    section: str,
    filename: str,
    content: str,
    title: str = "",
    tags_csv: str = "",
    template: str = "",
    source_notes_csv: str = "",
    related_notes_csv: str = "",
    status: str = "",
    project: Optional[str] = None,
) -> str:
    """Create or update a markdown note in inbox/concepts/projects."""
    log_tool_call(
        "write_library_note",
        {
            "section": section,
            "filename": filename,
            "content_len": len(content),
            "project": project,
        },
    )

    info, error_msg = _require_library_project("write_library_note", project)
    if info is None:
        return error_msg

    section_dir, error_msg = _resolve_section_dir(info, section)
    if section_dir is None:
        return error_msg

    try:
        normalized_filename = _normalize_filename(filename)
    except ValueError as exc:
        return f"❌ {exc}"

    note_path = _resolve_note_path(section_dir, normalized_filename)
    note_exists = note_path.exists()
    final_content, normalized_template = _compose_note_content(
        content,
        section_name=section_dir.name,
        filename=normalized_filename,
        title=title,
        tags_csv=tags_csv,
        template=template,
        source_notes_csv=source_notes_csv,
        related_notes_csv=related_notes_csv,
        status=status,
    )

    try:
        note_path.write_text(final_content, encoding="utf-8")
    except Exception as exc:
        log_tool_error("write_library_note", exc, {"path": str(note_path)})
        return f"❌ Error writing note: {exc}"

    action = "updated" if note_exists else "created"
    log_tool_result("write_library_note", f"{action} {note_path.name}", success=True)
    template_text = f"\n**Template:** {normalized_template}" if normalized_template else ""
    return (
        f"✅ Library note {action} successfully.\n\n"
        f"**Section:** {section_dir.name}\n"
        f"**File:** {note_path.name}\n"
        f"**Path:** {note_path}{template_text}{_write_next_step(section_dir.name)}"
    )


def _move_note_file(source_path: Path, target_path: Path, from_name: str, to_name: str) -> None:
    content = source_path.read_text(encoding="utf-8")
    updated_content = _rewrite_frontmatter(
        content,
        {
            "section": to_name,
            "status": _default_status(to_name),
            "updated_at": _current_timestamp(),
        },
        section=from_name,
    )
    target_path.write_text(updated_content, encoding="utf-8")
    source_path.unlink()


def move_library_note(
    filename: str,
    from_section: str,
    to_section: str,
    project: Optional[str] = None,
) -> str:
    """Move a markdown note between inbox/concepts/projects."""
    log_tool_call(
        "move_library_note",
        {
            "filename": filename,
            "from_section": from_section,
            "to_section": to_section,
            "project": project,
        },
    )

    info, error_msg = _require_library_project("move_library_note", project)
    if info is None:
        return error_msg

    from_dir, error_msg = _resolve_section_dir(info, from_section)
    if from_dir is None:
        return error_msg
    to_dir, error_msg = _resolve_section_dir(info, to_section)
    if to_dir is None:
        return error_msg

    try:
        normalized_filename = _normalize_filename(filename)
    except ValueError as exc:
        return f"❌ {exc}"

    source_path = _resolve_note_path(from_dir, normalized_filename)
    target_path = _resolve_note_path(to_dir, normalized_filename)
    if not source_path.exists():
        result = f"❌ Note not found: {source_path.name} in {from_dir.name}/"
        log_tool_result("move_library_note", result, success=False)
        return result
    if target_path.exists():
        result = f"❌ Target note already exists: {target_path.name} in {to_dir.name}/"
        log_tool_result("move_library_note", result, success=False)
        return result

    try:
        _move_note_file(source_path, target_path, from_dir.name, to_dir.name)
    except Exception as exc:
        log_tool_error(
            "move_library_note",
            exc,
            {"source": str(source_path), "target": str(target_path)},
        )
        return f"❌ Error moving note: {exc}"

    log_tool_result(
        "move_library_note",
        f"moved {normalized_filename} from {from_dir.name} to {to_dir.name}",
        success=True,
    )
    return (
        f"✅ Library note moved successfully.\n\n"
        f"**File:** {normalized_filename}\n"
        f"**From:** {from_dir.name}/\n"
        f"**To:** {to_dir.name}/\n"
        f"**Path:** {target_path}"
    )
