"""Normalization and path helpers for library notes."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from med_paper_assistant.shared.path_guard import normalize_relative_filename, resolve_child_path

from .constants import (
    ALLOWED_LIBRARY_SECTIONS,
    SECTION_ALIASES,
    TEMPLATE_ALIASES,
    TEMPLATE_NOTE_TYPES,
)


def _current_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _split_multivalue(raw_value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[\n,]", raw_value) if item.strip()]


def _coerce_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        candidates = value
    elif value is None:
        candidates = []
    else:
        candidates = [value]
    return [str(item).strip() for item in candidates if str(item).strip()]


def _dedupe_text_values(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_values.append(cleaned)
    return unique_values


def _normalize_related_note_refs(values: list[str]) -> list[str]:
    normalized_refs: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _normalize_note_reference(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_refs.append(normalized)
    return normalized_refs


def _slugify_filename_candidate(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-._")
    return slug or "concept-note"


def _normalize_section(section: str, *, allow_all: bool = False) -> str:
    normalized = section.strip().lower()
    if allow_all and normalized in {"", "all"}:
        return "all"
    return SECTION_ALIASES.get(normalized, normalized)


def _normalize_filename(filename: str) -> str:
    return normalize_relative_filename(
        filename,
        field_name="Library note filename",
        default_suffix=".md",
        allowed_suffixes={".md"},
    )


def _resolve_note_path(section_dir: Path, filename: str) -> Path:
    return resolve_child_path(
        section_dir,
        filename,
        field_name="Library note filename",
        allowed_suffixes={".md"},
    )


def _resolve_section_dir(
    info: dict[str, Any], section: str, *, create: bool = True
) -> tuple[Optional[Path], str]:
    """Resolve a library section directory; read-only callers pass ``create=False``."""
    normalized = _normalize_section(section)
    if normalized not in ALLOWED_LIBRARY_SECTIONS:
        allowed = ", ".join(ALLOWED_LIBRARY_SECTIONS)
        return None, f"❌ Invalid section '{section}'. Use one of: {allowed}."
    raw_path = info.get("paths", {}).get(normalized)
    if not raw_path:
        return None, f"❌ Project is missing the '{normalized}' directory."
    section_dir = Path(raw_path)
    if create:
        section_dir.mkdir(parents=True, exist_ok=True)
    return section_dir, ""


def _default_title_from_filename(filename: str) -> str:
    return Path(filename).stem.replace("-", " ").replace("_", " ").strip().title() or "Untitled"


def _normalize_template_name(template: str, section: str = "") -> str:
    normalized = str(template).strip().lower().replace("_", "-")
    if not normalized or normalized == "none":
        return ""
    if normalized == "auto":
        section_map = {
            "inbox": "capture",
            "concepts": "concept",
            "review": "review",
            "daily": "daily",
        }
        return section_map.get(_normalize_section(section), "")
    return TEMPLATE_ALIASES.get(normalized, normalized)


def _default_note_type(section: str, template: str = "") -> str:
    normalized_template = _normalize_template_name(template, section)
    if normalized_template in TEMPLATE_NOTE_TYPES:
        return TEMPLATE_NOTE_TYPES[normalized_template]
    return {
        "concepts": "library-concept",
        "projects": "library-synthesis",
        "review": "library-review",
        "daily": "library-daily",
    }.get(section, "library-note")


def _normalize_note_reference(note_ref: str) -> str:
    candidate = note_ref.strip().replace("\\", "/")
    if not candidate:
        return ""

    candidate = candidate.split("|", 1)[0].split("#", 1)[0].strip().lower()
    path_parts = [part for part in candidate.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] in ALLOWED_LIBRARY_SECTIONS:
        candidate = f"{path_parts[0]}:{path_parts[-1]}"

    if candidate.endswith(".md"):
        candidate = candidate[:-3]

    if ":" in candidate:
        section, value = candidate.split(":", 1)
        if section in ALLOWED_LIBRARY_SECTIONS and value.endswith(".md"):
            value = value[:-3]
        candidate = f"{section}:{value}"

    return candidate
