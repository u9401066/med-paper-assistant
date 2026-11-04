"""Journal/author/topic context hubs for the Foam graph."""

import os
from typing import Any, Dict, List


class FoamContextMixin:
    """Journal/author/topic context hubs for the Foam graph."""

    def _extract_first_author_slug(self, payload: Dict[str, Any]) -> str:
        authors_full = payload.get("authors_full", [])
        authors = payload.get("authors", [])

        candidate = ""
        if authors_full and isinstance(authors_full[0], dict):
            candidate = str(authors_full[0].get("last_name", ""))
        elif authors:
            candidate = str(authors[0]).split()[0]

        return self._slugify(candidate, fallback="")

    def _author_context_labels(self, payload: Dict[str, Any]) -> List[str]:
        labels: List[str] = []
        authors_full = payload.get("authors_full", [])
        if isinstance(authors_full, list):
            for author in authors_full:
                if not isinstance(author, dict):
                    continue
                last_name = str(author.get("last_name", "")).strip()
                fore_name = str(
                    author.get("fore_name") or author.get("first_name") or author.get("name") or ""
                ).strip()
                label = " ".join(part for part in [last_name, fore_name] if part).strip()
                if label:
                    labels.append(label)

        if not labels:
            labels = self._dedupe_strings(payload.get("authors", []))

        return self._dedupe_strings(labels)[:4]

    def _context_alias(self, kind: str, label: str) -> str:
        return f"{kind}-{self._slugify(label, fallback=kind)}"

    def _reference_context_entries(
        self, payload: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, str]]]:
        contexts: Dict[str, List[Dict[str, str]]] = {
            "journal": [],
            "authors": [],
            "topics": [],
            "mesh": [],
            "sections": [],
        }

        journal = str(payload.get("journal", "")).strip()
        if journal:
            contexts["journal"].append(
                {
                    "kind": "journal",
                    "label": journal,
                    "alias": self._context_alias("journal", journal),
                }
            )

        for author in self._author_context_labels(payload):
            contexts["authors"].append(
                {"kind": "author", "label": author, "alias": self._context_alias("author", author)}
            )

        for keyword in self._dedupe_strings(payload.get("keywords", []))[:5]:
            contexts["topics"].append(
                {"kind": "topic", "label": keyword, "alias": self._context_alias("topic", keyword)}
            )

        for mesh_term in self._dedupe_strings(payload.get("mesh_terms", []))[:5]:
            contexts["mesh"].append(
                {
                    "kind": "mesh",
                    "label": mesh_term,
                    "alias": self._context_alias("mesh", mesh_term),
                }
            )

        for section in self._dedupe_strings(payload.get("fulltext_sections", []))[:6]:
            contexts["sections"].append(
                {
                    "kind": "section",
                    "label": section,
                    "alias": self._context_alias("section", section),
                }
            )

        return contexts

    def _build_reference_graph_context(self, payload: Dict[str, Any]) -> str:
        contexts = self._reference_context_entries(payload)
        lines: List[str] = []

        if contexts["journal"]:
            lines.append(f"- Journal hub: [[{contexts['journal'][0]['alias']}]]")
        if contexts["authors"]:
            lines.append(
                "- Author hubs: "
                + ", ".join(f"[[{item['alias']}]]" for item in contexts["authors"])
            )
        if contexts["topics"]:
            lines.append(
                "- Topic hubs: " + ", ".join(f"[[{item['alias']}]]" for item in contexts["topics"])
            )
        if contexts["mesh"]:
            lines.append(
                "- MeSH hubs: " + ", ".join(f"[[{item['alias']}]]" for item in contexts["mesh"])
            )
        if contexts["sections"]:
            lines.append(
                "- Section hubs: "
                + ", ".join(f"[[{item['alias']}]]" for item in contexts["sections"])
            )

        visible_tags = self._visible_graph_tags(payload)
        if visible_tags:
            lines.append("- Graph tags: " + ", ".join(visible_tags))

        return "\n".join(lines)

    def _materialize_reference_context_notes(self) -> Dict[str, Any]:
        expected_paths: List[str] = []
        project_slug = self._current_project_slug()

        context_nodes = self._collect_context_nodes()

        materialized_nodes: List[Dict[str, Any]] = []
        for node in sorted(
            context_nodes.values(), key=lambda item: (item["kind"], item["label"].lower())
        ):
            note_path = os.path.join(self._context_notes_dir(), f"{node['alias']}.md")
            expected_paths.append(note_path)
            materialized_nodes.append(self._write_context_note(node, note_path, project_slug))

        self._prune_stale_graph_notes(self._context_notes_dir(), expected_paths)
        return {"nodes": materialized_nodes, "count": len(materialized_nodes)}

    def _collect_context_nodes(self) -> Dict[str, Dict[str, Any]]:
        context_nodes: Dict[str, Dict[str, Any]] = {}

        for reference_id in sorted(self.list_references()):
            metadata = self.get_metadata(reference_id)
            if not metadata:
                continue

            citation_key = metadata.get("citation_key") or reference_id
            title = metadata.get("title", reference_id)
            year = str(metadata.get("year", "")).strip()
            for items in self._reference_context_entries(metadata).values():
                for item in items:
                    node = context_nodes.setdefault(
                        item["alias"],
                        {
                            "kind": item["kind"],
                            "label": item["label"],
                            "alias": item["alias"],
                            "references": [],
                        },
                    )
                    node["references"].append(
                        {
                            "citation_key": citation_key,
                            "title": title,
                            "year": year,
                        }
                    )
        return context_nodes

    def _write_context_note(
        self, node: Dict[str, Any], note_path: str, project_slug: str
    ) -> Dict[str, Any]:
        references = sorted(
            node["references"],
            key=lambda item: (item["title"].lower(), item["citation_key"]),
        )
        body_lines = [
            f"- Context kind: {node['kind']}",
            f"- Linked references: {len(references)}",
            "",
            "## References",
            "",
        ]
        for reference in references:
            year_text = f" ({reference['year']})" if reference["year"] else ""
            body_lines.append(f"- [[{reference['citation_key']}]]: {reference['title']}{year_text}")

        note_type = f"{node['kind']}-note"
        self._write_graph_note(
            note_path,
            title=f"{node['kind'].title()}: {node['label']}",
            note_type=note_type,
            aliases=[node["alias"]],
            tags=self._build_graph_note_tags(
                note_type,
                "taxonomy",
                [
                    f"context/{node['kind']}",
                    f"label/{self._slugify(node['label'], fallback=node['kind'])}",
                ],
            ),
            extra_fields={
                "note_class": note_type,
                "note_domain": "taxonomy",
                "project": project_slug,
                "context_kind": node["kind"],
                "context_value": node["label"],
                "linked_references": [reference["citation_key"] for reference in references],
                "review_state": "n/a",
            },
            body="\n".join(body_lines),
        )
        return {
            "alias": node["alias"],
            "title": f"{node['kind'].title()}: {node['label']}",
            "kind": node["kind"],
            "reference_count": len(references),
        }
