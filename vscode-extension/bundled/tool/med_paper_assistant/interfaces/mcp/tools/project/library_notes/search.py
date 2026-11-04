"""Handlers that search library notes and show reading queues."""

from __future__ import annotations

from typing import Any, Optional

from ..._shared import (
    log_tool_call,
    log_tool_result,
)
from .constants import ALLOWED_LIBRARY_SECTIONS, QUEUE_LABELS
from .content import _body_excerpt, _extract_title
from .context import _require_library_project
from .index import _collect_notes, _format_note_label
from .normalize import _default_title_from_filename, _normalize_section, _resolve_section_dir


def _search_notes(
    info: dict[str, Any], sections: tuple[str, ...], query: str
) -> tuple[list[tuple[str, str, str, str]], str]:
    """Return matching notes and an error message (non-empty only when a section is unusable)."""
    query_terms = [term for term in query.lower().split() if term]
    results: list[tuple[str, str, str, str]] = []

    for current_section in sections:
        section_dir, error_msg = _resolve_section_dir(info, current_section, create=False)
        if section_dir is None:
            return [], error_msg

        for note_path in sorted(p for p in section_dir.glob("*.md") if p.is_file()):
            try:
                content = note_path.read_text(encoding="utf-8")
            except Exception:  # nosec B112
                continue

            haystack = content.lower()
            if query_terms and not all(term in haystack for term in query_terms):
                continue

            title = _extract_title(content, _default_title_from_filename(note_path.name))
            results.append((current_section, note_path.name, title, _body_excerpt(content, query)))
    return results, ""


def search_library_notes(query: str, section: str = "all", project: Optional[str] = None) -> str:
    """Search markdown notes in inbox/concepts/projects."""
    log_tool_call(
        "search_library_notes",
        {"query": query, "section": section, "project": project},
    )

    if not query.strip():
        return "❌ Query cannot be empty."

    info, error_msg = _require_library_project("search_library_notes", project)
    if info is None:
        return error_msg

    normalized_section = _normalize_section(section, allow_all=True)
    if normalized_section != "all" and normalized_section not in ALLOWED_LIBRARY_SECTIONS:
        allowed = ", ".join(ALLOWED_LIBRARY_SECTIONS)
        return f"❌ Invalid section '{section}'. Use one of: all, {allowed}."

    sections = ALLOWED_LIBRARY_SECTIONS if normalized_section == "all" else (normalized_section,)
    results, error_msg = _search_notes(info, sections, query)
    if error_msg:
        return error_msg

    if not results:
        result = f"No library notes found matching '{query}'."
        log_tool_result("search_library_notes", result, success=True)
        return result

    lines = [f"# Library Note Search Results ({len(results)})", ""]
    for current_section, filename_match, title, excerpt in results:
        lines.extend(
            [
                f"## {title}",
                f"- Section: {current_section}",
                f"- File: {filename_match}",
                f"- Excerpt: {excerpt}",
                "",
            ]
        )

    log_tool_result("search_library_notes", f"found {len(results)} matches", success=True)
    return "\n".join(lines).strip()


def _render_queue_sections(
    notes: list[dict[str, Any]], requested_queue: str, limit: int
) -> tuple[list[str], int]:
    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in QUEUE_LABELS}
    for note in notes:
        grouped[note["queue_bucket"]].append(note)

    lines: list[str] = []
    total = 0
    for bucket, label in QUEUE_LABELS.items():
        if requested_queue != "all" and requested_queue != bucket:
            continue

        bucket_notes = sorted(
            grouped[bucket],
            key=lambda note: (note.get("updated_at", ""), note["filename"]),
            reverse=True,
        )
        total += len(bucket_notes)
        lines.extend([f"## {label} ({len(bucket_notes)})", ""])
        if not bucket_notes:
            lines.extend(["- [No notes]", ""])
            continue

        for note in bucket_notes[: max(1, limit)]:
            lines.append(_format_note_label(note))
        if len(bucket_notes) > limit:
            lines.append(f"- ... {len(bucket_notes) - limit} more")
        lines.append("")
    return lines, total


def show_reading_queues(
    queue: str = "all",
    limit: int = 10,
    project: Optional[str] = None,
) -> str:
    """Show the current reading queues derived from library note status/section metadata."""
    log_tool_call(
        "show_reading_queues",
        {"queue": queue, "limit": limit, "project": project},
    )

    info, error_msg = _require_library_project("show_reading_queues", project)
    if info is None:
        return error_msg

    notes = _collect_notes(info, ALLOWED_LIBRARY_SECTIONS)
    if not notes:
        return "No library notes yet. Use `write_library_note` or `create_concept_page` first."

    requested_queue = queue.strip().lower() or "all"
    if requested_queue != "all" and requested_queue not in QUEUE_LABELS:
        allowed = ", ".join(["all", *QUEUE_LABELS])
        return f"❌ Invalid queue '{queue}'. Use one of: {allowed}."

    lines = [f"# Reading Queues: {info.get('name', info.get('slug', 'Unknown'))}", ""]
    section_lines, total = _render_queue_sections(notes, requested_queue, limit)
    lines.extend(section_lines)

    lines.append(f"Total queued notes: {total}")
    log_tool_result("show_reading_queues", f"listed {total} queued notes", success=True)
    return "\n".join(lines).strip()
