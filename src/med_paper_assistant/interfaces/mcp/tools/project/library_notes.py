"""Library wiki note tools for inbox/concepts/projects workflows."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager
from med_paper_assistant.shared.constants import WORKFLOW_MODES

from .._shared import (
    get_optional_tool_decorator,
    log_agent_misuse,
    log_tool_call,
    log_tool_error,
    log_tool_result,
)

ALLOWED_LIBRARY_SECTIONS = ("inbox", "concepts", "projects")
SECTION_ALIASES = {
    "inbox": "inbox",
    "concept": "concepts",
    "concepts": "concepts",
    "project": "projects",
    "projects": "projects",
}
QUEUE_LABELS = {
    "capture": "Capture Queue",
    "active-reading": "Active Reading",
    "concept-build": "Concept Building",
    "synthesis": "Synthesis Queue",
    "blocked": "Blocked",
}
TRIAGE_PROGRESSION = {
    "inbox": "concepts",
    "concepts": "projects",
    "projects": "projects",
}
FRONTMATTER_FIELD_ORDER = (
    "title",
    "type",
    "section",
    "status",
    "tags",
    "related_notes",
    "updated_at",
)


def _yaml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


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
    candidate = filename.strip().replace("\\", "/").split("/")[-1]
    if not candidate:
        raise ValueError("filename cannot be empty")
    if not candidate.endswith(".md"):
        candidate += ".md"
    return candidate


def _default_title_from_filename(filename: str) -> str:
    return Path(filename).stem.replace("-", " ").replace("_", " ").strip().title() or "Untitled"


def _default_status(section: str) -> str:
    return {
        "inbox": "captured",
        "concepts": "curated",
        "projects": "synthesized",
    }.get(section, "active")


def _default_queue_bucket(section: str) -> str:
    return {
        "inbox": "capture",
        "concepts": "concept-build",
        "projects": "synthesis",
    }.get(section, "capture")


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
    normalized["status"] = (
        str(normalized.get("status") or _default_status(normalized_section)).strip()
        or _default_status(normalized_section)
    )
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


def _collect_notes(info: dict[str, Any], sections: tuple[str, ...]) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []

    for current_section in sections:
        raw_path = info.get("paths", {}).get(current_section)
        if not raw_path:
            continue
        section_dir = Path(raw_path)
        section_dir.mkdir(parents=True, exist_ok=True)

        for note_path in sorted(p for p in section_dir.glob("*.md") if p.is_file()):
            try:
                content = note_path.read_text(encoding="utf-8")
            except Exception:
                continue

            frontmatter, body = _parse_frontmatter(content)
            status_display = str(frontmatter.get("status") or _default_status(current_section)).strip()
            tags = _dedupe_text_values(_coerce_string_list(frontmatter.get("tags")))
            related_notes = _normalize_related_note_refs(
                _coerce_string_list(frontmatter.get("related_notes"))
            )
            body_links = _extract_links(body)
            links = list(dict.fromkeys([*body_links, *related_notes]))

            note = {
                "id": f"{current_section}:{note_path.stem.lower()}",
                "section": current_section,
                "filename": note_path.name,
                "stem": note_path.stem,
                "path": str(note_path),
                "title": str(frontmatter.get("title") or _extract_title(content, _default_title_from_filename(note_path.name))),
                "status": status_display.lower(),
                "status_display": status_display,
                "updated_at": str(frontmatter.get("updated_at", "")).strip(),
                "tags": tags,
                "related_notes": related_notes,
                "content": content,
                "body": body,
                "excerpt": _body_excerpt(content),
                "body_links": body_links,
                "links": links,
            }
            notes.append(note)

    lookup: dict[str, dict[str, Any]] = {}
    for note in notes:
        for key in _note_lookup_keys(note):
            lookup[key] = note

    backlinks: dict[str, set[str]] = defaultdict(set)
    for note in notes:
        resolved_links: list[str] = []
        for link in note["links"]:
            target = lookup.get(link)
            if target and target["id"] != note["id"]:
                resolved_links.append(target["id"])
                backlinks[target["id"]].add(note["id"])
        note["linked_note_ids"] = list(dict.fromkeys(resolved_links))

    for note in notes:
        note["backlink_ids"] = sorted(backlinks.get(note["id"], set()))
        note["queue_bucket"] = _queue_bucket_for_note(note)

    return notes


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


def register_library_note_tools(
    mcp: FastMCP,
    project_manager: ProjectManager,
    *,
    register_public_verbs: bool = True,
) -> dict[str, Any]:
    """Register markdown note tools for library-wiki projects."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    def _resolve_library_project(project: Optional[str]) -> tuple[Optional[dict[str, Any]], str]:
        target_slug = project or project_manager.get_current_project()
        if not target_slug:
            available = project_manager.list_projects().get("projects", [])
            available_slugs = ", ".join(p.get("slug", "") for p in available if p.get("slug"))
            return (
                None,
                "❌ No active project. "
                + (
                    f"Specify a project or switch to one of: {available_slugs}"
                    if available_slugs
                    else "Create a library-wiki project first."
                ),
            )

        if project and project_manager.get_current_project() != project:
            switch_result = project_manager.switch_project(project)
            if not switch_result.get("success"):
                return None, f"❌ {switch_result.get('error', 'Unable to switch project.')}"

        info = project_manager.get_project_info(target_slug)
        if not info.get("success"):
            return None, f"❌ {info.get('error', 'Project not found.')}"

        workflow_mode = info.get("workflow_mode", "manuscript")
        if workflow_mode != "library-wiki":
            workflow_name = WORKFLOW_MODES.get(workflow_mode, {}).get("name", workflow_mode)
            required_name = WORKFLOW_MODES["library-wiki"]["name"]
            return (
                None,
                "❌ Library note tools are only available for "
                f"{required_name} projects.\n\n"
                f"Current workflow: {workflow_name}.\n"
                "Switch the project workflow to `library-wiki` before managing inbox/concepts/projects notes.",
            )

        return info, ""

    def _resolve_section_dir(info: dict[str, Any], section: str) -> tuple[Optional[Path], str]:
        normalized = _normalize_section(section)
        if normalized not in ALLOWED_LIBRARY_SECTIONS:
            allowed = ", ".join(ALLOWED_LIBRARY_SECTIONS)
            return None, f"❌ Invalid section '{section}'. Use one of: {allowed}."

        raw_path = info.get("paths", {}).get(normalized)
        if not raw_path:
            return None, f"❌ Project is missing the '{normalized}' directory."

        section_dir = Path(raw_path)
        section_dir.mkdir(parents=True, exist_ok=True)
        return section_dir, ""

    @tool()
    def list_library_notes(section: str = "all", project: Optional[str] = None) -> str:
        """List markdown notes from inbox/concepts/projects in a library-wiki project."""
        log_tool_call("list_library_notes", {"section": section, "project": project})

        info, error_msg = _resolve_library_project(project)
        if info is None:
            log_agent_misuse("list_library_notes", "library-wiki project required", {"project": project}, error_msg)
            return error_msg

        normalized_section = _normalize_section(section, allow_all=True)
        sections = ALLOWED_LIBRARY_SECTIONS if normalized_section == "all" else (normalized_section,)

        output = [f"# Library Notes: {info.get('name', info.get('slug', 'Unknown'))}", ""]
        total_notes = 0

        for current_section in sections:
            section_dir, error_msg = _resolve_section_dir(info, current_section)
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

    @tool()
    def read_library_note(section: str, filename: str, project: Optional[str] = None) -> str:
        """Read a markdown note from inbox/concepts/projects."""
        log_tool_call(
            "read_library_note",
            {"section": section, "filename": filename, "project": project},
        )

        info, error_msg = _resolve_library_project(project)
        if info is None:
            log_agent_misuse("read_library_note", "library-wiki project required", {"project": project}, error_msg)
            return error_msg

        section_dir, error_msg = _resolve_section_dir(info, section)
        if section_dir is None:
            return error_msg

        try:
            note_path = section_dir / _normalize_filename(filename)
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

    @tool()
    def write_library_note(
        section: str,
        filename: str,
        content: str,
        title: str = "",
        tags_csv: str = "",
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

        info, error_msg = _resolve_library_project(project)
        if info is None:
            log_agent_misuse("write_library_note", "library-wiki project required", {"project": project}, error_msg)
            return error_msg

        section_dir, error_msg = _resolve_section_dir(info, section)
        if section_dir is None:
            return error_msg

        try:
            normalized_filename = _normalize_filename(filename)
        except ValueError as exc:
            return f"❌ {exc}"

        note_path = section_dir / normalized_filename
        note_exists = note_path.exists()
        resolved_title = title.strip() or _default_title_from_filename(normalized_filename)
        resolved_status = status.strip() or _default_status(section_dir.name)
        tags = _dedupe_text_values(_split_multivalue(tags_csv))

        if content.lstrip().startswith("---\n"):
            final_content = content
        else:
            lines = [
                "---",
                f'title: "{_yaml_escape(resolved_title)}"',
                'type: "library-note"',
                f'section: "{section_dir.name}"',
                f'status: "{_yaml_escape(resolved_status)}"',
            ]
            if tags:
                lines.append("tags:")
                for tag in tags:
                    lines.append(f'  - "{_yaml_escape(tag)}"')
            else:
                lines.append("tags: []")
            lines.extend(
                [
                    f'updated_at: "{_current_timestamp()}"',
                    "---",
                    "",
                ]
            )

            body = content.strip()
            if body and not body.startswith("#"):
                body = f"# {resolved_title}\n\n{body}"
            elif not body:
                body = f"# {resolved_title}\n"

            final_content = "\n".join(lines) + body
            if not final_content.endswith("\n"):
                final_content += "\n"

        try:
            note_path.write_text(final_content, encoding="utf-8")
        except Exception as exc:
            log_tool_error("write_library_note", exc, {"path": str(note_path)})
            return f"❌ Error writing note: {exc}"

        action = "updated" if note_exists else "created"
        log_tool_result("write_library_note", f"{action} {note_path.name}", success=True)
        next_step = ""
        if section_dir.name == "inbox":
            next_step = (
                "\n\nNext step: review the note and move it into `concepts/` or `projects/` using "
                "`move_library_note` when it has been triaged."
            )
        return (
            f"✅ Library note {action} successfully.\n\n"
            f"**Section:** {section_dir.name}\n"
            f"**File:** {note_path.name}\n"
            f"**Path:** {note_path}{next_step}"
        )

    @tool()
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

        info, error_msg = _resolve_library_project(project)
        if info is None:
            log_agent_misuse("move_library_note", "library-wiki project required", {"project": project}, error_msg)
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

        source_path = from_dir / normalized_filename
        target_path = to_dir / normalized_filename
        if not source_path.exists():
            result = f"❌ Note not found: {source_path.name} in {from_dir.name}/"
            log_tool_result("move_library_note", result, success=False)
            return result
        if target_path.exists():
            result = f"❌ Target note already exists: {target_path.name} in {to_dir.name}/"
            log_tool_result("move_library_note", result, success=False)
            return result

        try:
            content = source_path.read_text(encoding="utf-8")
            updated_content = _rewrite_frontmatter(
                content,
                {
                    "section": to_dir.name,
                    "status": _default_status(to_dir.name),
                    "updated_at": _current_timestamp(),
                },
                section=from_dir.name,
            )
            target_path.write_text(updated_content, encoding="utf-8")
            source_path.unlink()
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

    @tool()
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

        info, error_msg = _resolve_library_project(project)
        if info is None:
            log_agent_misuse("triage_library_note", "library-wiki project required", {"project": project}, error_msg)
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

        merged_tags = _dedupe_text_values(list(source_note.get("tags", [])) + _split_multivalue(tags_csv))
        merged_related = _normalize_related_note_refs(
            list(source_note.get("related_notes", [])) + _split_multivalue(related_notes_csv)
        )
        has_metadata_changes = bool(status.strip() or tags_csv.strip() or related_notes_csv.strip())
        if resolved_target == source_note["section"] and not has_metadata_changes:
            return (
                f"Note already sits in the final triage section: {source_note['section']}/{source_note['filename']}."
            )

        target_dir, error_msg = _resolve_section_dir(info, resolved_target)
        if target_dir is None:
            return error_msg

        source_path = Path(source_note["path"])
        target_path = target_dir / source_note["filename"]
        if source_path != target_path and target_path.exists():
            result = f"❌ Target note already exists: {target_path.name} in {target_dir.name}/"
            log_tool_result("triage_library_note", result, success=False)
            return result

        next_status = status.strip()
        if not next_status:
            next_status = (
                _default_status(resolved_target)
                if resolved_target != source_note["section"]
                else source_note["status_display"] or source_note["status"]
            )

        try:
            content = source_path.read_text(encoding="utf-8")
            updated_content = _rewrite_frontmatter(
                content,
                {
                    "section": resolved_target,
                    "status": next_status,
                    "tags": merged_tags,
                    "related_notes": merged_related,
                    "updated_at": _current_timestamp(),
                },
                section=source_note["section"],
            )
            target_path.write_text(updated_content, encoding="utf-8")
            if source_path != target_path:
                source_path.unlink()
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

    @tool()
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
            return (
                "❌ No metadata changes requested. Provide title, status, tags, add/remove tags, related notes, or note type."
            )

        info, error_msg = _resolve_library_project(project)
        if info is None:
            log_agent_misuse(
                "update_library_note_metadata",
                "library-wiki project required",
                {"project": project},
                error_msg,
            )
            return error_msg

        notes = _collect_notes(info, ALLOWED_LIBRARY_SECTIONS)
        if not notes:
            return "No library notes yet. Use `write_library_note` first."

        note, error_msg = _resolve_note_reference_or_error(note_ref, notes)
        if note is None:
            return error_msg

        note_path = Path(note["path"])
        try:
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

    @tool()
    def search_library_notes(query: str, section: str = "all", project: Optional[str] = None) -> str:
        """Search markdown notes in inbox/concepts/projects."""
        log_tool_call(
            "search_library_notes",
            {"query": query, "section": section, "project": project},
        )

        if not query.strip():
            return "❌ Query cannot be empty."

        info, error_msg = _resolve_library_project(project)
        if info is None:
            log_agent_misuse("search_library_notes", "library-wiki project required", {"project": project}, error_msg)
            return error_msg

        normalized_section = _normalize_section(section, allow_all=True)
        if normalized_section != "all" and normalized_section not in ALLOWED_LIBRARY_SECTIONS:
            allowed = ", ".join(ALLOWED_LIBRARY_SECTIONS)
            return f"❌ Invalid section '{section}'. Use one of: all, {allowed}."

        sections = ALLOWED_LIBRARY_SECTIONS if normalized_section == "all" else (normalized_section,)
        query_terms = [term for term in query.lower().split() if term]
        results: list[tuple[str, str, str, str]] = []

        for current_section in sections:
            section_dir, error_msg = _resolve_section_dir(info, current_section)
            if section_dir is None:
                return error_msg

            for note_path in sorted(p for p in section_dir.glob("*.md") if p.is_file()):
                try:
                    content = note_path.read_text(encoding="utf-8")
                except Exception:
                    continue

                haystack = content.lower()
                if query_terms and not all(term in haystack for term in query_terms):
                    continue

                title = _extract_title(content, _default_title_from_filename(note_path.name))
                results.append((current_section, note_path.name, title, _body_excerpt(content, query)))

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

    @tool()
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

        info, error_msg = _resolve_library_project(project)
        if info is None:
            log_agent_misuse("show_reading_queues", "library-wiki project required", {"project": project}, error_msg)
            return error_msg

        notes = _collect_notes(info, ALLOWED_LIBRARY_SECTIONS)
        if not notes:
            return "No library notes yet. Use `write_library_note` or `create_concept_page` first."

        requested_queue = queue.strip().lower() or "all"
        if requested_queue != "all" and requested_queue not in QUEUE_LABELS:
            allowed = ", ".join(["all", *QUEUE_LABELS])
            return f"❌ Invalid queue '{queue}'. Use one of: {allowed}."

        grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in QUEUE_LABELS}
        for note in notes:
            grouped[note["queue_bucket"]].append(note)

        lines = [f"# Reading Queues: {info.get('name', info.get('slug', 'Unknown'))}", ""]
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

        lines.append(f"Total queued notes: {total}")
        log_tool_result("show_reading_queues", f"listed {total} queued notes", success=True)
        return "\n".join(lines).strip()

    @tool()
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

        info, error_msg = _resolve_library_project(project)
        if info is None:
            log_agent_misuse("create_concept_page", "library-wiki project required", {"project": project}, error_msg)
            return error_msg

        concepts_dir, error_msg = _resolve_section_dir(info, "concepts")
        if concepts_dir is None:
            return error_msg

        try:
            normalized_filename = _normalize_filename(filename)
        except ValueError as exc:
            return f"❌ {exc}"

        note_path = concepts_dir / normalized_filename
        note_exists = note_path.exists()
        tags = _dedupe_text_values(_split_multivalue(tags_csv))
        source_refs = _normalize_related_note_refs(_split_multivalue(source_notes_csv))
        source_links = [f"[[{_normalize_note_reference(ref).split(':', 1)[-1]}]]" for ref in source_refs]
        question_lines = [line.strip() for line in open_questions.splitlines() if line.strip()]

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

        frontmatter_lines = [
            "---",
            f'title: "{_yaml_escape(title.strip() or _default_title_from_filename(normalized_filename))}"',
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
                f"# {title.strip() or _default_title_from_filename(normalized_filename)}",
                "",
            ]
        )

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

    @tool()
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

        info, error_msg = _resolve_library_project(project)
        if info is None:
            log_agent_misuse(
                "materialize_concept_page",
                "library-wiki project required",
                {"project": project},
                error_msg,
            )
            return error_msg

        notes = _collect_notes(info, ALLOWED_LIBRARY_SECTIONS)
        if not notes:
            return "No library notes yet. Use `write_library_note` first."

        source_notes: list[dict[str, Any]] = []
        normalized_refs: list[str] = []
        seen_note_ids: set[str] = set()
        for source_ref in source_refs:
            source_note, error_msg = _resolve_note_reference_or_error(source_ref, notes)
            if source_note is None:
                return error_msg
            if source_note["id"] in seen_note_ids:
                continue
            seen_note_ids.add(source_note["id"])
            source_notes.append(source_note)
            normalized_refs.append(source_note["id"])

        tag_counts = Counter(tag for note in source_notes for tag in note.get("tags", []))
        shared_tags = sorted(tag for tag, count in tag_counts.items() if count == len(source_notes))

        if title.strip():
            resolved_title = title.strip()
        elif len(source_notes) == 1:
            resolved_title = f"{source_notes[0]['title']} Concept"
        elif shared_tags:
            resolved_title = f"{shared_tags[0].replace('-', ' ').title()} Concept"
        else:
            resolved_title = "Materialized Concept"

        if filename.strip():
            resolved_filename = filename
        elif len(source_notes) == 1:
            resolved_filename = f"{source_notes[0]['stem']}-concept"
        elif shared_tags:
            resolved_filename = f"{_slugify_filename_candidate(shared_tags[0])}-concept"
        else:
            resolved_filename = f"{_slugify_filename_candidate(source_notes[0]['stem'])}-concept"

        resolved_summary = summary.strip()
        if not resolved_summary:
            if len(source_notes) == 1:
                source_note = source_notes[0]
                resolved_summary = (
                    f"Derived from {source_note['title']} in {source_note['section']} to promote the idea into a reusable concept page. "
                    f"Evidence snapshot: {source_note['excerpt']}"
                )
            else:
                source_sections = ", ".join(sorted({note['section'] for note in source_notes}))
                focus_hint = f" around {shared_tags[0]}" if shared_tags else ""
                resolved_summary = (
                    f"Derived from {len(source_notes)} library notes across {source_sections}{focus_hint} to capture a reusable concept for later synthesis."
                )

        resolved_tags = _dedupe_text_values(
            [
                *_split_multivalue(tags_csv),
                *(tag for note in source_notes for tag in note.get("tags", [])),
                "concept",
            ]
        )

        concept_result = create_concept_page(
            filename=resolved_filename,
            title=resolved_title,
            summary=resolved_summary,
            source_notes_csv=",".join(normalized_refs),
            tags_csv=",".join(resolved_tags),
            open_questions=open_questions,
            project=project,
        )
        if concept_result.startswith("❌"):
            return concept_result

        concept_ref = f"concepts:{Path(_normalize_filename(resolved_filename)).stem.lower()}"
        promoted_sources = 0

        for source_note in source_notes:
            source_status = source_note["status_display"] or source_note["status"]
            next_status = source_status
            if source_note["section"] == "inbox" and source_status.lower() in {
                "captured",
                "reading",
                "reviewing",
                "active",
                "in-progress",
            }:
                next_status = "triaged"
            elif source_note["section"] == "concepts" and source_status.lower() == "curated":
                next_status = "linked"

            source_path = Path(source_note["path"])
            try:
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
                promoted_sources += 1
            except Exception as exc:
                log_tool_error(
                    "materialize_concept_page",
                    exc,
                    {"path": str(source_path), "concept_ref": concept_ref},
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

    @tool()
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

        info, error_msg = _resolve_library_project(project)
        if info is None:
            log_agent_misuse("explain_library_path", "library-wiki project required", {"project": project}, error_msg)
            return error_msg

        notes = _collect_notes(info, ALLOWED_LIBRARY_SECTIONS)
        if not notes:
            return "No library notes yet. Use `write_library_note` or `create_concept_page` first."

        source, error_msg = _resolve_note_reference_or_error(source_note, notes)
        if source is None:
            return error_msg

        notes_by_id = {note["id"]: note for note in notes}

        if not target_note.strip():
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
            log_tool_result("explain_library_path", f"explained {source['filename']}", success=True)
            return "\n".join(lines).strip()

        target, error_msg = _resolve_note_reference_or_error(target_note, notes)
        if target is None:
            return error_msg

        if source["id"] == target["id"]:
            return f"Source and target resolve to the same note: {source['title']} ({source['filename']})."

        adjacency: dict[str, set[str]] = defaultdict(set)
        for note in notes:
            for linked_note_id in note.get("linked_note_ids", []):
                adjacency[note["id"]].add(linked_note_id)
                adjacency[linked_note_id].add(note["id"])

        queue: deque[list[str]] = deque([[source["id"]]])
        visited = {source["id"]}
        path: list[str] = []

        while queue:
            current_path = queue.popleft()
            current_id = current_path[-1]
            if current_id == target["id"]:
                path = current_path
                break
            for neighbor_id in sorted(adjacency.get(current_id, set())):
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                queue.append(current_path + [neighbor_id])

        if not path:
            shared_tags = sorted(set(source.get("tags", [])) & set(target.get("tags", [])))
            hint = (
                f"Shared tags: {', '.join(shared_tags)}" if shared_tags else "Try adding explicit [[wikilinks]] between the notes."
            )
            return (
                f"No note-to-note path found between {source['title']} and {target['title']}.\n\n"
                f"Hint: {hint}"
            )

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
            lines.append(
                f"{index}. [{note['section']}] {note['title']} ({note['filename']})"
            )
            if index < len(path):
                next_note = notes_by_id[path[index]]
                lines.append(f"   reason: {_path_reason(note, next_note)}")
        log_tool_result("explain_library_path", f"path {source['filename']} -> {target['filename']}", success=True)
        return "\n".join(lines).strip()

    @tool()
    def build_library_dashboard(
        view: str = "overview",
        limit: int = 10,
        project: Optional[str] = None,
    ) -> str:
        """Build a cross-note dashboard for a library-wiki project."""
        log_tool_call(
            "build_library_dashboard",
            {"view": view, "limit": limit, "project": project},
        )

        info, error_msg = _resolve_library_project(project)
        if info is None:
            log_agent_misuse("build_library_dashboard", "library-wiki project required", {"project": project}, error_msg)
            return error_msg

        notes = _collect_notes(info, ALLOWED_LIBRARY_SECTIONS)
        if not notes:
            return "No library notes yet. Use `write_library_note` or `create_concept_page` first."

        view_name = view.strip().lower() or "overview"
        if view_name not in {"overview", "queues", "concepts", "links", "synthesis"}:
            return "❌ Invalid view. Use one of: overview, queues, concepts, links, synthesis."

        notes_by_id = {note["id"]: note for note in notes}
        section_counts = Counter(note["section"] for note in notes)
        status_counts = Counter(note["status_display"] or note["status"] for note in notes)
        tag_counts = Counter(tag for note in notes for tag in note.get("tags", []))
        connected_notes = sorted(
            notes,
            key=lambda note: (len(note.get("linked_note_ids", [])) + len(note.get("backlink_ids", [])), note["title"]),
            reverse=True,
        )
        orphans = [
            note
            for note in notes
            if not note.get("linked_note_ids") and not note.get("backlink_ids")
        ]
        cross_section_edges = 0
        for note in notes:
            for linked_note_id in note.get("linked_note_ids", []):
                if notes_by_id[linked_note_id]["section"] != note["section"]:
                    cross_section_edges += 1

        lines = [
            f"# Library Dashboard: {info.get('name', info.get('slug', 'Unknown'))}",
            "",
            f"View: {view_name}",
            f"Total notes: {len(notes)}",
            "",
        ]

        if view_name == "overview":
            lines.extend(["## Section Counts", ""])
            lines.extend(f"- {section}: {count}" for section, count in sorted(section_counts.items()))
            lines.extend(["", "## Status Counts", ""])
            lines.extend(f"- {status}: {count}" for status, count in status_counts.most_common(limit))
            lines.extend(["", "## Top Tags", ""])
            if tag_counts:
                lines.extend(f"- {tag}: {count}" for tag, count in tag_counts.most_common(limit))
            else:
                lines.append("- [No tags yet]")
            lines.extend(["", "## Most Connected Notes", ""])
            lines.extend(_format_note_label(note) for note in connected_notes[: max(1, limit)])
            lines.extend(["", "## Orphan Notes", ""])
            if orphans:
                lines.extend(_format_note_label(note) for note in orphans[: max(1, limit)])
            else:
                lines.append("- [No orphan notes]")

        if view_name == "queues":
            queue_counts = Counter(note["queue_bucket"] for note in notes)
            lines.extend(["## Queue Counts", ""])
            for bucket, label in QUEUE_LABELS.items():
                lines.append(f"- {label}: {queue_counts.get(bucket, 0)}")
            lines.extend(["", "## Active Items", ""])
            active_notes = [note for note in notes if note["queue_bucket"] in {"active-reading", "concept-build", "synthesis"}]
            if active_notes:
                lines.extend(_format_note_label(note) for note in active_notes[: max(1, limit)])
            else:
                lines.append("- [No active items]")

        if view_name == "concepts":
            concept_notes = [note for note in notes if note["section"] == "concepts"]
            lines.extend(["## Concept Pages", ""])
            if concept_notes:
                for note in concept_notes[: max(1, limit)]:
                    lines.append(
                        f"- {note['title']} ({note['filename']}) | sources: {len(note.get('linked_note_ids', []))} | backlinks: {len(note.get('backlink_ids', []))}"
                    )
            else:
                lines.append("- [No concept pages yet]")

        if view_name == "links":
            lines.extend(["## Link Health", ""])
            lines.append(f"- Cross-section edges: {cross_section_edges}")
            lines.append(f"- Orphan notes: {len(orphans)}")
            lines.extend(["", "## Most Connected Notes", ""])
            lines.extend(_format_note_label(note) for note in connected_notes[: max(1, limit)])

        if view_name == "synthesis":
            synthesis_notes = [note for note in notes if note["queue_bucket"] == "synthesis"]
            concept_notes = [note for note in notes if note["section"] == "concepts"]
            backlog = [
                note
                for note in notes
                if note["queue_bucket"] in {"active-reading", "concept-build"}
            ]

            tag_to_notes: dict[str, set[str]] = defaultdict(set)
            for note in notes:
                for tag in note.get("tags", []):
                    tag_to_notes[tag].add(note["id"])

            shared_tag_clusters = [
                (tag, len(note_ids))
                for tag, note_ids in tag_to_notes.items()
                if len(note_ids) >= 2
            ]
            shared_tag_clusters.sort(key=lambda item: (item[1], item[0]), reverse=True)

            lines.extend(["## Synthesis Throughput", ""])
            lines.append(f"- Synthesis queue: {len(synthesis_notes)}")
            lines.append(f"- Concept nodes: {len(concept_notes)}")
            lines.append(f"- Pre-synthesis backlog: {len(backlog)}")
            lines.extend(["", "## Synthesis Candidates", ""])
            if shared_tag_clusters:
                for tag, size in shared_tag_clusters[: max(1, limit)]:
                    lines.append(f"- tag:{tag} -> {size} linked notes")
            else:
                lines.append("- [No cross-note tag clusters yet]")

            lines.extend(["", "## Ready-To-Synthesize Notes", ""])
            if synthesis_notes:
                lines.extend(_format_note_label(note) for note in synthesis_notes[: max(1, limit)])
            else:
                lines.append("- [No synthesis notes yet]")

        log_tool_result("build_library_dashboard", f"dashboard {view_name}", success=True)
        return "\n".join(lines).strip()

    return {
        "list_library_notes": list_library_notes,
        "read_library_note": read_library_note,
        "write_library_note": write_library_note,
        "move_library_note": move_library_note,
        "triage_library_note": triage_library_note,
        "update_library_note_metadata": update_library_note_metadata,
        "search_library_notes": search_library_notes,
        "show_reading_queues": show_reading_queues,
        "create_concept_page": create_concept_page,
        "materialize_concept_page": materialize_concept_page,
        "explain_library_path": explain_library_path,
        "build_library_dashboard": build_library_dashboard,
    }