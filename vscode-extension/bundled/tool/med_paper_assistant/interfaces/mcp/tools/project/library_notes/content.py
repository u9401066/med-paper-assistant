"""Frontmatter parsing, rendering and link extraction for library notes."""

from __future__ import annotations

import re
from typing import Any

from med_paper_assistant.shared.yaml_escape import escape_yaml_value as _yaml_escape

from ..library_note_support import default_status as _default_status
from .constants import ASSET_LINK_PATTERN, FRONTMATTER_FIELD_ORDER, PLACEHOLDER_PATTERN
from .normalize import (
    _coerce_string_list,
    _dedupe_text_values,
    _default_title_from_filename,
    _normalize_note_reference,
    _normalize_related_note_refs,
)


def _extract_title(content: str, fallback: str) -> str:
    title_match = re.search(r'^title:\s*"?(.+?)"?$', content, flags=re.MULTILINE)
    if title_match:
        return title_match.group(1).strip().strip('"')

    heading_match = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
    if heading_match:
        return heading_match.group(1).strip()

    return fallback


def _body_excerpt(content: str, query: str = "") -> str:
    body = re.sub(r"(?s)^---\n.*?\n---\n?", "", content).replace("\n", " ").strip()
    if not body:
        return "[Empty note]"

    if query:
        query_lower = query.lower()
        idx = body.lower().find(query_lower)
        if idx >= 0:
            start = max(0, idx - 60)
            end = min(len(body), idx + 120)
            excerpt = body[start:end].strip()
            if start > 0:
                excerpt = "..." + excerpt
            if end < len(body):
                excerpt += "..."
            return excerpt

    return body[:160] + ("..." if len(body) > 160 else "")


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", content, flags=re.DOTALL)
    if not match:
        return {}, content

    frontmatter_text, body = match.groups()
    frontmatter: dict[str, Any] = {}
    lines = frontmatter_text.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index]
        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not key_match:
            index += 1
            continue

        key, raw_value = key_match.groups()
        raw_value = raw_value.strip()
        if raw_value == "[]":
            frontmatter[key] = []
            index += 1
            continue

        if raw_value == "":
            list_values: list[str] = []
            index += 1
            while index < len(lines) and re.match(r"^\s*-\s+", lines[index]):
                item = re.sub(r"^\s*-\s+", "", lines[index]).strip().strip('"')
                if item:
                    list_values.append(item)
                index += 1
            frontmatter[key] = list_values
            continue

        frontmatter[key] = raw_value.strip('"')
        index += 1

    return frontmatter, body


def _ensure_frontmatter_defaults(
    frontmatter: dict[str, Any],
    *,
    fallback_title: str,
    section: str,
) -> dict[str, Any]:
    normalized: dict[str, Any] = dict(frontmatter)
    normalized_section = str(normalized.get("section") or section).strip() or section
    normalized["title"] = str(normalized.get("title") or fallback_title).strip() or fallback_title
    normalized["type"] = str(normalized.get("type") or "library-note").strip() or "library-note"
    normalized["section"] = normalized_section
    normalized["status"] = str(
        normalized.get("status") or _default_status(normalized_section)
    ).strip() or _default_status(normalized_section)
    normalized["tags"] = _dedupe_text_values(_coerce_string_list(normalized.get("tags")))
    normalized["related_notes"] = _normalize_related_note_refs(
        _coerce_string_list(normalized.get("related_notes"))
    )
    return normalized


def _serialize_frontmatter(frontmatter: dict[str, Any]) -> str:
    lines = ["---"]
    emitted: set[str] = set()
    ordered_keys = [*FRONTMATTER_FIELD_ORDER, *frontmatter.keys()]

    for key in ordered_keys:
        if key in emitted or key not in frontmatter:
            continue
        emitted.add(key)
        value = frontmatter[key]

        if isinstance(value, list):
            values = [str(item).strip() for item in value if str(item).strip()]
            if values:
                lines.append(f"{key}:")
                lines.extend(f'  - "{_yaml_escape(item)}"' for item in values)
            else:
                lines.append(f"{key}: []")
            continue

        lines.append(f'{key}: "{_yaml_escape(str(value))}"')

    lines.append("---")
    return "\n".join(lines)


def _render_note_content(frontmatter: dict[str, Any], body: str) -> str:
    rendered_body = body.lstrip("\n")
    content = _serialize_frontmatter(frontmatter)
    if rendered_body:
        content += "\n\n" + rendered_body
    else:
        content += "\n"
    if not content.endswith("\n"):
        content += "\n"
    return content


def _rewrite_frontmatter(
    content: str,
    updates: dict[str, Any],
    *,
    section: str,
) -> str:
    frontmatter, body = _parse_frontmatter(content)
    normalized = _ensure_frontmatter_defaults(
        frontmatter,
        fallback_title=_extract_title(content, _default_title_from_filename("note.md")),
        section=section,
    )

    for key, value in updates.items():
        if value is None:
            continue
        if key == "tags":
            normalized[key] = _dedupe_text_values(_coerce_string_list(value))
            continue
        if key == "related_notes":
            normalized[key] = _normalize_related_note_refs(_coerce_string_list(value))
            continue
        normalized[key] = str(value).strip()

    return _render_note_content(normalized, body)


def _extract_links(content: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for match in re.findall(r"\[\[([^\]]+)\]\]", content):
        normalized = _normalize_note_reference(match)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        links.append(normalized)
    return links


def _extract_placeholder_markers(content: str) -> list[str]:
    markers: list[str] = []
    seen: set[str] = set()
    for match in PLACEHOLDER_PATTERN.findall(content):
        marker = str(match).strip()
        if not marker:
            continue
        normalized = marker.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        markers.append(marker)
    return markers


def _extract_asset_links(content: str) -> list[str]:
    assets: list[str] = []
    seen: set[str] = set()
    for match in ASSET_LINK_PATTERN.findall(content):
        candidate = str(match).split("|", 1)[0].split("#", 1)[0].strip()
        lowered = candidate.lower()
        if not candidate:
            continue
        if not (
            lowered.startswith(("figure-", "table-", "asset-", "img-"))
            or lowered.endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf", ".csv", ".md")
            )
        ):
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        assets.append(candidate)
    return assets


def _refs_to_links(values: list[str]) -> list[str]:
    links: list[str] = []
    for value in values:
        normalized = _normalize_note_reference(value)
        if not normalized:
            continue
        links.append(f"[[{normalized.split(':', 1)[-1]}]]")
    return links
