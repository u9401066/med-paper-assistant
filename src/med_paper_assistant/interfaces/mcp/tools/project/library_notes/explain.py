"""Handler that explains a library note or the path between two notes."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Optional

from ..._shared import log_tool_call, log_tool_result
from .constants import ALLOWED_LIBRARY_SECTIONS, QUEUE_LABELS
from .context import _require_library_project
from .index import _collect_notes, _path_reason, _resolve_note_reference_or_error


def _explain_single_note(source: dict[str, Any], notes_by_id: dict[str, dict[str, Any]]) -> str:
    outgoing = [notes_by_id[note_id]["title"] for note_id in source.get("linked_note_ids", [])]
    incoming = [notes_by_id[note_id]["title"] for note_id in source.get("backlink_ids", [])]
    lines = [
        f"# Library Note Explanation: {source['title']}",
        "",
        f"- Section: {source['section']}",
        f"- File: {source['filename']}",
        f"- Status: {source['status_display'] or source['status']}",
        f"- Queue: {QUEUE_LABELS[source['queue_bucket']]}",
        f"- Tags: {', '.join(source['tags']) if source['tags'] else '[none]'}",
        f"- Outgoing note links: {len(outgoing)}",
        f"- Backlinks: {len(incoming)}",
        "",
        "## Outgoing Links",
        "",
    ]
    if outgoing:
        lines.extend(f"- {title}" for title in outgoing)
    else:
        lines.append("- [No outgoing library-note links]")
    lines.extend(["", "## Backlinks", ""])
    if incoming:
        lines.extend(f"- {title}" for title in incoming)
    else:
        lines.append("- [No backlinks yet]")
    lines.extend(["", "## Excerpt", "", source["excerpt"]])
    return "\n".join(lines).strip()


def _find_note_path(
    notes: list[dict[str, Any]], source: dict[str, Any], target: dict[str, Any]
) -> list[str]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for note in notes:
        for linked_note_id in note.get("linked_note_ids", []):
            adjacency[note["id"]].add(linked_note_id)
            adjacency[linked_note_id].add(note["id"])

    queue: deque[list[str]] = deque([[source["id"]]])
    visited = {source["id"]}

    while queue:
        current_path = queue.popleft()
        current_id = current_path[-1]
        if current_id == target["id"]:
            return current_path
        for neighbor_id in sorted(adjacency.get(current_id, set())):
            if neighbor_id in visited:
                continue
            visited.add(neighbor_id)
            queue.append(current_path + [neighbor_id])
    return []


def _render_missing_path(source: dict[str, Any], target: dict[str, Any]) -> str:
    shared_tags = sorted(set(source.get("tags", [])) & set(target.get("tags", [])))
    hint = (
        f"Shared tags: {', '.join(shared_tags)}"
        if shared_tags
        else "Try adding explicit [[wikilinks]] between the notes."
    )
    return (
        f"No note-to-note path found between {source['title']} and {target['title']}.\n\n"
        f"Hint: {hint}"
    )


def _render_note_path(
    source: dict[str, Any],
    target: dict[str, Any],
    path: list[str],
    notes_by_id: dict[str, dict[str, Any]],
) -> str:
    lines = [
        f"# Library Path: {source['title']} -> {target['title']}",
        "",
        f"Path length: {len(path) - 1} hop(s)",
        "",
        "## Steps",
        "",
    ]
    for index, note_id in enumerate(path, start=1):
        note = notes_by_id[note_id]
        lines.append(f"{index}. [{note['section']}] {note['title']} ({note['filename']})")
        if index < len(path):
            next_note = notes_by_id[path[index]]
            lines.append(f"   reason: {_path_reason(note, next_note)}")
    return "\n".join(lines).strip()


def explain_library_path(
    source_note: str,
    target_note: str = "",
    project: Optional[str] = None,
) -> str:
    """Explain a note's context or find a path between two notes in the library graph."""
    log_tool_call(
        "explain_library_path",
        {"source_note": source_note, "target_note": target_note, "project": project},
    )

    info, error_msg = _require_library_project("explain_library_path", project)
    if info is None:
        return error_msg

    notes = _collect_notes(info, ALLOWED_LIBRARY_SECTIONS)
    if not notes:
        return "No library notes yet. Use `write_library_note` or `create_concept_page` first."

    source, error_msg = _resolve_note_reference_or_error(source_note, notes)
    if source is None:
        return error_msg

    notes_by_id = {note["id"]: note for note in notes}

    if not target_note.strip():
        explanation = _explain_single_note(source, notes_by_id)
        log_tool_result("explain_library_path", f"explained {source['filename']}", success=True)
        return explanation

    target, error_msg = _resolve_note_reference_or_error(target_note, notes)
    if target is None:
        return error_msg

    if source["id"] == target["id"]:
        return (
            f"Source and target resolve to the same note: {source['title']} ({source['filename']})."
        )

    path = _find_note_path(notes, source, target)
    if not path:
        return _render_missing_path(source, target)

    rendered = _render_note_path(source, target, path, notes_by_id)
    log_tool_result(
        "explain_library_path",
        f"path {source['filename']} -> {target['filename']}",
        success=True,
    )
    return rendered
