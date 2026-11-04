"""Publish-safe export bundle of the Foam notes."""

import os
from typing import Any, Dict, List

from med_paper_assistant.shared.path_guard import (
    PathGuardError,
)


class FoamPublishMixin:
    """Publish-safe export bundle of the Foam notes."""

    def _write_publish_safe_bundle(
        self,
        *,
        library_pages: List[Dict[str, str]],
        knowledge_maps: List[Dict[str, str]],
        synthesis_pages: List[Dict[str, str]],
        draft_section_nodes: List[Dict[str, str]],
        asset_nodes: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        publish_dir = self._publish_notes_dir()
        entries = self._publish_reference_entries()

        entries.extend(library_pages)
        entries.extend(knowledge_maps)
        entries.extend(synthesis_pages)
        entries.extend(draft_section_nodes)
        entries.extend(asset_nodes.get("figures", []))
        entries.extend(asset_nodes.get("tables", []))

        deduped_entries = self._dedupe_publish_entries(entries)

        link_note_path = self._write_publish_link_note(publish_dir, deduped_entries)
        publish_index_path = self._write_publish_index_note(
            publish_dir, library_pages, knowledge_maps, synthesis_pages, len(deduped_entries)
        )

        return [
            {
                "alias": "publish-reference-links",
                "title": "Publish-Safe Reference Links",
                "path": link_note_path,
            },
            {
                "alias": "publish-knowledge-base",
                "title": "Publish-Safe Knowledge Base",
                "path": publish_index_path,
            },
        ]

    def _publish_reference_entries(self) -> List[Dict[str, str]]:
        entries: List[Dict[str, str]] = []

        for ref_id in sorted(self.list_references()):
            metadata = self.get_metadata(ref_id)
            if not metadata:
                continue
            citation_key = metadata.get("citation_key") or ref_id
            try:
                note_path = self._reference_dir(ref_id) / self._citation_note_filename(citation_key)
            except (PathGuardError, ValueError):
                continue
            if not os.path.exists(note_path):
                continue
            entries.append(
                {
                    "alias": citation_key,
                    "title": metadata.get("title", ref_id),
                    "path": str(note_path),
                }
            )
        return entries

    def _dedupe_publish_entries(self, entries: List[Dict[str, str]]) -> List[Dict[str, str]]:
        deduped_entries: List[Dict[str, str]] = []
        seen_aliases: set[str] = set()
        for entry in entries:
            alias = str(entry.get("alias", "")).strip()
            path = str(entry.get("path", "")).strip()
            if not alias or not path or alias in seen_aliases:
                continue
            seen_aliases.add(alias)
            deduped_entries.append(entry)
        return deduped_entries

    def _write_publish_link_note(
        self, publish_dir: str, deduped_entries: List[Dict[str, str]]
    ) -> str:
        link_lines = [
            "## How To Use",
            "",
            "- Copy the definitions below into any plain Markdown export that cannot resolve wikilinks.",
            "",
            "## Reference Definitions",
            "",
        ]
        for entry in deduped_entries:
            relative_path = os.path.relpath(entry["path"], publish_dir).replace(os.sep, "/")
            link_lines.append(
                f'[{entry["alias"]}]: {relative_path} "{self._yaml_escape(entry["title"])}"'
            )

        link_note_path = os.path.join(publish_dir, "reference-links.md")
        self._write_graph_note(
            link_note_path,
            title="Publish-Safe Reference Links",
            note_type="publish-links",
            aliases=["publish-reference-links"],
            tags=self._build_graph_note_tags(
                "publish-links",
                "export",
                ["publish-safe", "export/links"],
            ),
            extra_fields={
                "note_class": "publish-links",
                "note_domain": "export",
                "project": self._current_project_slug(),
                "reference_count": len(deduped_entries),
                "review_state": "n/a",
            },
            body="\n".join(link_lines),
        )
        return link_note_path

    def _publish_index_lines(
        self,
        publish_dir: str,
        library_pages: List[Dict[str, str]],
        knowledge_maps: List[Dict[str, str]],
        synthesis_pages: List[Dict[str, str]],
    ) -> List[str]:
        index_lines = [
            "## Core Pages",
            "",
            "- [Knowledge Base Index](../index.md)",
        ]
        for page in library_pages:
            relative_path = os.path.relpath(page["path"], publish_dir).replace(os.sep, "/")
            index_lines.append(f"- [{page['title']}]({relative_path})")

        if knowledge_maps:
            index_lines.extend(["", "## Knowledge Maps", ""])
            for page in knowledge_maps:
                relative_path = os.path.relpath(page["path"], publish_dir).replace(os.sep, "/")
                index_lines.append(f"- [{page['title']}]({relative_path})")

        if synthesis_pages:
            index_lines.extend(["", "## Synthesis Pages", ""])
            for page in synthesis_pages:
                relative_path = os.path.relpath(page["path"], publish_dir).replace(os.sep, "/")
                index_lines.append(f"- [{page['title']}]({relative_path})")

        index_lines.extend(
            [
                "",
                "## Reference Link Pack",
                "",
                "- [Publish-Safe Reference Links](reference-links.md)",
                "- [[publish-reference-links]]",
            ]
        )
        return index_lines

    def _write_publish_index_note(
        self,
        publish_dir: str,
        library_pages: List[Dict[str, str]],
        knowledge_maps: List[Dict[str, str]],
        synthesis_pages: List[Dict[str, str]],
        reference_count: int,
    ) -> str:
        index_lines = self._publish_index_lines(
            publish_dir, library_pages, knowledge_maps, synthesis_pages
        )

        publish_index_path = os.path.join(publish_dir, "knowledge-base.md")
        self._write_graph_note(
            publish_index_path,
            title="Publish-Safe Knowledge Base",
            note_type="publish-index",
            aliases=["publish-knowledge-base"],
            tags=self._build_graph_note_tags(
                "publish-index",
                "export",
                ["publish-safe", "export/index"],
            ),
            extra_fields={
                "note_class": "publish-index",
                "note_domain": "export",
                "project": self._current_project_slug(),
                "reference_count": reference_count,
                "review_state": "n/a",
            },
            body="\n".join(index_lines),
        )
        return publish_index_path
