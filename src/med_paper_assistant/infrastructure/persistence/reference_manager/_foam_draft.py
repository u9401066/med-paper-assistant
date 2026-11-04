"""Draft-section notes linked into the Foam graph."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


class FoamDraftNotesMixin:
    """Draft-section notes linked into the Foam graph."""

    def _section_kind(self, title: str) -> str:
        normalized = self._slugify(title, fallback="section")
        aliases = {
            "introduction": "introduction",
            "background": "introduction",
            "methods": "methods",
            "materials-and-methods": "methods",
            "method": "methods",
            "results": "results",
            "discussion": "discussion",
            "conclusion": "conclusion",
            "abstract": "abstract",
            "title": "title",
        }
        return aliases.get(normalized, normalized)

    def _extract_draft_sections(
        self, markdown_text: str, draft_filename: str
    ) -> List[Dict[str, str]]:
        sections: List[Dict[str, str]] = []
        current_title = Path(draft_filename).stem.replace("_", " ").replace("-", " ").title()
        current_lines: List[str] = []
        saw_heading = False

        def flush() -> None:
            content = "\n".join(current_lines).strip()
            if not content and saw_heading:
                return
            sections.append({"title": current_title, "content": content})

        for line in markdown_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()
                if heading:
                    if current_lines or saw_heading:
                        flush()
                    current_title = heading
                    current_lines = []
                    saw_heading = True
                    continue
            current_lines.append(line.rstrip())

        if current_lines or not saw_heading:
            flush()

        return [section for section in sections if section["title"].strip()]

    def _materialize_draft_section_notes(
        self, asset_aliases: Dict[str, Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        drafts_dir = Path(self._project_root_dir()) / "drafts"
        if not drafts_dir.exists():
            self._prune_stale_graph_notes(self._draft_section_notes_dir(), [])
            return []

        expected_paths: List[str] = []
        nodes: List[Dict[str, Any]] = []
        project_slug = self._current_project_slug()

        for draft_path in sorted(drafts_dir.glob("*.md")):
            try:
                content = draft_path.read_text(encoding="utf-8")
            except Exception:  # nosec B112
                continue

            for section in self._extract_draft_sections(content, draft_path.name):
                note_path, node = self._write_draft_section_note(
                    draft_path, section, asset_aliases, project_slug
                )
                expected_paths.append(note_path)
                nodes.append(node)

        self._prune_stale_graph_notes(self._draft_section_notes_dir(), expected_paths)
        return nodes

    def _write_draft_section_note(
        self,
        draft_path: Path,
        section: Dict[str, str],
        asset_aliases: Dict[str, Dict[str, str]],
        project_slug: str,
    ) -> Tuple[str, Dict[str, Any]]:
        section_title = section["title"]
        section_content = section["content"]
        section_kind = self._section_kind(section_title)
        section_slug = self._slugify(f"{draft_path.stem}-{section_title}")
        alias = f"draft-section-{section_slug}"
        note_path = os.path.join(self._draft_section_notes_dir(), f"{section_slug}.md")

        linked_notes = self._extract_wikilinks(section_content)
        asset_links = self._linked_section_assets(section_content, asset_aliases)
        body_lines = self._draft_section_body_lines(
            draft_path, section_kind, section_content, linked_notes, asset_links
        )

        self._write_graph_note(
            note_path,
            title=f"{section_title} ({draft_path.stem})",
            note_type="draft-section",
            aliases=[alias],
            tags=self._build_graph_note_tags(
                "draft-section",
                "writing",
                [
                    f"draft/{draft_path.stem}",
                    f"section/{section_kind}",
                ],
            ),
            extra_fields={
                "note_class": "draft-section",
                "note_domain": "writing",
                "project": project_slug,
                "draft_file": draft_path.name,
                "section_title": section_title,
                "section_kind": section_kind,
                "review_state": "pending",
                "linked_notes": linked_notes,
                "linked_assets": asset_links,
            },
            body="\n".join(body_lines),
        )
        return note_path, {"alias": alias, "title": f"{section_title} ({draft_path.stem})"}

    def _linked_section_assets(
        self, section_content: str, asset_aliases: Dict[str, Dict[str, str]]
    ) -> List[str]:
        linked_figures = [
            asset_aliases["figure"].get(match)
            for match in re.findall(r"\bFigure\s+(\d+)\b", section_content, flags=re.IGNORECASE)
        ]
        linked_tables = [
            asset_aliases["table"].get(match)
            for match in re.findall(r"\bTable\s+(\d+)\b", section_content, flags=re.IGNORECASE)
        ]
        return [link for link in linked_figures + linked_tables if link]

    def _draft_section_body_lines(
        self,
        draft_path: Path,
        section_kind: str,
        section_content: str,
        linked_notes: List[str],
        asset_links: List[str],
    ) -> List[str]:
        excerpt = self._build_markdown_summary(section_content, max_chars=900)
        body_lines = [
            f"- Draft file: drafts/{draft_path.name}",
            f"- Section kind: {section_kind}",
            f"- Linked notes: {len(linked_notes)}",
            f"- Linked assets: {len(asset_links)}",
        ]

        if linked_notes:
            body_lines.extend(["", "## Linked Notes", ""])
            body_lines.extend(f"- [[{link}]]" for link in linked_notes)

        if asset_links:
            body_lines.extend(["", "## Linked Assets", ""])
            body_lines.extend(f"- [[{link}]]" for link in asset_links)
            body_lines.extend(["", "## Linked Asset Evidence", ""])
            body_lines.extend(f"- [[{link}#^asset-summary]]" for link in asset_links)

        if excerpt:
            body_lines.extend(["", "## Excerpt", "", excerpt])
        return body_lines
