"""Low-level writers and iterators for materialized Foam notes."""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict, List


class FoamNoteWriterMixin:
    """Low-level writers and iterators for materialized Foam notes."""

    def _append_frontmatter_field(self, lines: List[str], key: str, value: Any) -> None:
        if value is None:
            return

        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
            return

        if isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
            return

        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
                return
            lines.append(f"{key}:")
            for item in value:
                lines.append(f'  - "{self._yaml_escape(str(item))}"')
            return

        lines.append(f'{key}: "{self._yaml_escape(str(value))}"')

    def _write_graph_note(
        self,
        file_path: str,
        *,
        title: str,
        note_type: str,
        aliases: List[str],
        tags: List[str],
        extra_fields: Dict[str, Any],
        body: str,
    ) -> None:
        lines = [
            "---",
            f'title: "{self._yaml_escape(title)}"',
            f'type: "{self._yaml_escape(note_type)}"',
        ]
        self._append_frontmatter_field(lines, "aliases", aliases)
        self._append_frontmatter_field(lines, "tags", tags)
        for key, value in extra_fields.items():
            self._append_frontmatter_field(lines, key, value)
        lines.extend(["---", "", f"# {title}", ""])
        if body.strip():
            lines.append(body.strip())
            lines.append("")

        Path(file_path).write_text("\n".join(lines), encoding="utf-8")

    def _prune_stale_graph_notes(self, directory: str, expected_paths: List[str]) -> None:
        expected = {str(Path(path).resolve()) for path in expected_paths}
        dir_path = Path(directory)
        if not dir_path.exists():
            return

        for candidate in dir_path.glob("*.md"):
            if str(candidate.resolve()) not in expected:
                candidate.unlink()

    def _materialized_page_path(self, page_type: str, slug: str) -> str:
        if page_type == "knowledge_map":
            return os.path.join(self._knowledge_maps_dir(), f"{slug}.md")
        return os.path.join(self._synthesis_pages_dir(), f"{slug}.md")

    def _materialized_page_alias(self, page_type: str, slug: str) -> str:
        prefix = "knowledge-map" if page_type == "knowledge_map" else "synthesis"
        return f"{prefix}-{slug}"

    def _read_materialized_page_title(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if stripped.startswith("title:"):
                        return stripped.split(":", 1)[1].strip().strip('"')
                    if stripped.startswith("# "):
                        return stripped[2:].strip()
        except Exception:  # nosec B110
            pass
        return Path(file_path).stem.replace("-", " ").title()

    def _iter_markdown_pages(
        self, page_dir: str, alias_for: Callable[[str], str]
    ) -> List[Dict[str, str]]:
        if not os.path.isdir(page_dir):
            return []

        pages: List[Dict[str, str]] = []
        for file_name in sorted(os.listdir(page_dir)):
            if not file_name.endswith(".md"):
                continue
            slug = Path(file_name).stem
            file_path = os.path.join(page_dir, file_name)
            pages.append(
                {
                    "slug": slug,
                    "alias": alias_for(slug),
                    "title": self._read_materialized_page_title(file_path),
                    "path": file_path,
                }
            )
        return pages

    def _iter_materialized_pages(self, page_type: str) -> List[Dict[str, str]]:
        page_dir = (
            self._knowledge_maps_dir()
            if page_type == "knowledge_map"
            else self._synthesis_pages_dir()
        )
        return self._iter_markdown_pages(
            page_dir, lambda slug: self._materialized_page_alias(page_type, slug)
        )

    def _iter_library_pages(self) -> List[Dict[str, str]]:
        return self._iter_markdown_pages(
            self._library_pages_dir(),
            lambda slug: "library-overview" if slug == "overview" else slug,
        )

    def _write_materialized_page(
        self,
        *,
        page_type: str,
        title: str,
        query: str,
        focus: str,
        reference_ids: List[str],
        body: str,
        log_event: str,
    ) -> str:
        self._ensure_workspace_scaffolding()

        slug = self._slugify(title)
        alias = self._materialized_page_alias(page_type, slug)
        foam_type = self._foam_note_type(page_type)
        tags = self._build_materialized_page_tags(page_type, query=query, focus=focus)
        generated_at = __import__("datetime").datetime.now().isoformat()
        page_path = self._materialized_page_path(page_type, slug)

        lines = self._build_materialized_page_lines(
            title=title,
            alias=alias,
            foam_type=foam_type,
            tags=tags,
            generated_at=generated_at,
            query=query,
            focus=focus,
            reference_ids=reference_ids,
        )
        lines.extend(["---", "", f"# {title}", "", body.strip(), ""])

        with open(page_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

        self._rebuild_index()
        self._append_log(
            log_event,
            {
                "unique_id": slug,
                "title": title,
                "source": page_type,
                "trust_level": "agent",
                "saved_at": generated_at,
            },
        )
        return page_path

    def _build_materialized_page_lines(
        self,
        *,
        title: str,
        alias: str,
        foam_type: str,
        tags: List[str],
        generated_at: str,
        query: str,
        focus: str,
        reference_ids: List[str],
    ) -> List[str]:
        lines = [
            "---",
            f'title: "{self._yaml_escape(title)}"',
            f'type: "{foam_type}"',
            "aliases:",
            f'  - "{alias}"',
        ]
        lines.append("tags:")
        for tag in tags:
            lines.append(f'  - "{self._yaml_escape(tag)}"')
        lines.extend(
            [
                f'note_class: "{foam_type}"',
                'note_domain: "synthesis"',
                f'project: "{self._yaml_escape(self._current_project_slug())}"',
                'source_kind: "materialized"',
                f'query_state: "{"query-backed" if query else "static"}"',
            ]
        )
        lines.extend(
            [
                f'generated_at: "{generated_at}"',
                f"reference_count: {len(reference_ids)}",
            ]
        )
        if query:
            lines.append(f'query: "{self._yaml_escape(query)}"')
        if focus:
            lines.append(f'focus: "{self._yaml_escape(focus)}"')

        if reference_ids:
            lines.append("source_refs:")
            for ref_id in reference_ids:
                lines.append(f'  - "{self._yaml_escape(ref_id)}"')
        else:
            lines.append("source_refs: []")
        return lines
