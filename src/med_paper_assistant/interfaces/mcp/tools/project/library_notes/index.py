"""Note index and graph helpers for library notes."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from ..library_note_support import default_queue_bucket as _default_queue_bucket
from ..library_note_support import default_status as _default_status
from .content import (
    _body_excerpt,
    _extract_asset_links,
    _extract_links,
    _extract_placeholder_markers,
    _extract_title,
    _parse_frontmatter,
    _render_note_content,
)
from .normalize import (
    _coerce_string_list,
    _current_timestamp,
    _dedupe_text_values,
    _default_title_from_filename,
    _normalize_note_reference,
    _normalize_related_note_refs,
)


def _note_lookup_keys(note: dict[str, Any]) -> set[str]:
    filename = note["filename"].lower()
    stem = note["stem"].lower()
    section = note["section"]
    return {
        stem,
        filename,
        f"{section}:{stem}",
        f"{section}:{filename}",
    }


def _queue_bucket_for_note(note: dict[str, Any]) -> str:
    status = str(note.get("status", "")).strip().lower()
    if status in {"blocked", "waiting", "on-hold"}:
        return "blocked"
    if note["section"] == "daily" or status in {"logged", "journaled"}:
        return "daily"
    if note["section"] == "review" or status in {"reviewing", "needs-review", "pending-review"}:
        return "review"
    if status in {"reading", "reviewing", "active", "in-progress"}:
        return "active-reading"
    if note["section"] == "projects" or status in {"synthesized", "ready", "drafting"}:
        return "synthesis"
    if note["section"] == "concepts" or status in {"curated", "triaged", "linked"}:
        return "concept-build"
    return _default_queue_bucket(note["section"])


def _format_note_label(note: dict[str, Any]) -> str:
    tags = note.get("tags", [])
    tag_text = f" | tags: {', '.join(tags[:3])}" if tags else ""
    return (
        f"- [{note['section']}] {note['filename']}: {note['title']} "
        f"(status: {note['status_display'] or note['status']}){tag_text}"
    )


def _read_note_record(note_path: Path, current_section: str) -> Optional[dict[str, Any]]:
    try:
        content = note_path.read_text(encoding="utf-8")
    except Exception:  # nosec B112
        return None

    frontmatter, body = _parse_frontmatter(content)
    status_display = str(frontmatter.get("status") or _default_status(current_section)).strip()
    related_notes = _normalize_related_note_refs(
        _coerce_string_list(frontmatter.get("related_notes"))
    )
    body_links = _extract_links(body)
    title_fallback = _default_title_from_filename(note_path.name)

    return {
        "id": f"{current_section}:{note_path.stem.lower()}",
        "section": current_section,
        "filename": note_path.name,
        "stem": note_path.stem,
        "path": str(note_path),
        "title": str(frontmatter.get("title") or _extract_title(content, title_fallback)),
        "status": status_display.lower(),
        "status_display": status_display,
        "updated_at": str(frontmatter.get("updated_at", "")).strip(),
        "tags": _dedupe_text_values(_coerce_string_list(frontmatter.get("tags"))),
        "related_notes": related_notes,
        "content": content,
        "body": body,
        "excerpt": _body_excerpt(content),
        "body_links": body_links,
        "links": list(dict.fromkeys([*body_links, *related_notes])),
        "placeholder_markers": _extract_placeholder_markers(body),
        "asset_links": _extract_asset_links(body),
    }


def _link_notes(notes: list[dict[str, Any]]) -> None:
    lookup: dict[str, dict[str, Any]] = {}
    for note in notes:
        for key in _note_lookup_keys(note):
            lookup[key] = note

    backlinks: dict[str, set[str]] = defaultdict(set)
    for note in notes:
        resolved_links: list[str] = []
        unresolved_links: list[str] = []
        for link in note["links"]:
            target = lookup.get(link)
            if target and target["id"] != note["id"]:
                resolved_links.append(target["id"])
                backlinks[target["id"]].add(note["id"])
            elif not target:
                unresolved_links.append(link)
        note["linked_note_ids"] = list(dict.fromkeys(resolved_links))
        note["unresolved_links"] = list(dict.fromkeys(unresolved_links))

    for note in notes:
        note["backlink_ids"] = sorted(backlinks.get(note["id"], set()))
        note["queue_bucket"] = _queue_bucket_for_note(note)
        note["is_orphan"] = not note.get("linked_note_ids") and not note.get("backlink_ids")


def _collect_notes(info: dict[str, Any], sections: tuple[str, ...]) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []

    for current_section in sections:
        raw_path = info.get("paths", {}).get(current_section)
        if not raw_path:
            continue
        section_dir = Path(raw_path)
        section_dir.mkdir(parents=True, exist_ok=True)

        for note_path in sorted(p for p in section_dir.glob("*.md") if p.is_file()):
            note = _read_note_record(note_path, current_section)
            if note is not None:
                notes.append(note)

    _link_notes(notes)
    return notes


def _materialize_dashboard_note(
    info: dict[str, Any],
    *,
    directory: str,
    slug: str,
    title: str,
    body_lines: list[str],
    note_type: str,
    tags: list[str],
    extra_fields: Optional[dict[str, Any]] = None,
) -> Path:
    project_root = Path(info.get("paths", {}).get("root", "."))
    target_dir = project_root / "notes" / directory
    target_dir.mkdir(parents=True, exist_ok=True)
    note_path = target_dir / f"{slug}.md"

    frontmatter = {
        "title": title,
        "type": note_type,
        "section": directory,
        "status": "generated",
        "tags": _dedupe_text_values(tags),
        "related_notes": [],
        "updated_at": _current_timestamp(),
        "project": info.get("slug", ""),
        "source_kind": "materialized",
    }
    if extra_fields:
        frontmatter.update(extra_fields)

    body = "\n".join(body_lines).strip()
    note_path.write_text(_render_note_content(frontmatter, body), encoding="utf-8")
    return note_path


def _resolve_note_reference_or_error(
    note_ref: str,
    notes: list[dict[str, Any]],
) -> tuple[Optional[dict[str, Any]], str]:
    lookup: dict[str, dict[str, Any]] = {}
    for note in notes:
        for key in _note_lookup_keys(note):
            lookup[key] = note

    normalized = _normalize_note_reference(note_ref)
    target = lookup.get(normalized)
    if target is None:
        return None, f"❌ Note not found: {note_ref}. Use `section:filename` or the note stem."
    return target, ""


def _path_reason(source: dict[str, Any], target: dict[str, Any]) -> str:
    target_lookup_keys = _note_lookup_keys(target)
    if any(link in target_lookup_keys for link in source.get("body_links", [])):
        return f"{source['title']} links to [[{target['stem']}]]"
    if any(link in _note_lookup_keys(source) for link in target.get("body_links", [])):
        return f"{target['title']} links back to [[{source['stem']}]]"
    if any(link in target_lookup_keys for link in source.get("related_notes", [])):
        return f"{source['title']} references {target['title']} via frontmatter related_notes"
    if any(link in _note_lookup_keys(source) for link in target.get("related_notes", [])):
        return f"{target['title']} references {source['title']} via frontmatter related_notes"

    shared_tags = sorted(set(source.get("tags", [])) & set(target.get("tags", [])))
    if shared_tags:
        return f"shared tags: {', '.join(shared_tags[:3])}"
    return "connected through the note graph"
