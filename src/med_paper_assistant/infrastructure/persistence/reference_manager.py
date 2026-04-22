import json
import os
import hashlib
import re
import shutil
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from pathlib import Path

import structlog

if TYPE_CHECKING:
    from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager

from med_paper_assistant.domain.services.reference_converter import (
    ReferenceConverter,
)

logger = structlog.get_logger()


class ReferenceManager:
    """
    管理本地文獻參考資料的儲存、檢索和組織。

    重構說明 (2025-12):
    - 使用 ReferenceConverter Domain Service 處理格式轉換
    - 支援多來源：PubMed, Zotero, DOI
    - 唯一識別符：unique_id + citation_key (for Foam)
    - 文獻搜尋由外部 MCP 負責，Agent 協調資料傳遞
    """

    def __init__(
        self,
        base_dir: str = "references",
        project_manager: Optional["ProjectManager"] = None,
        pubmed_api_url: Optional[str] = None,
    ):
        """
        Initialize the ReferenceManager.

        Args:
            base_dir: Default directory to store references (used if no project active).
            project_manager: Optional ProjectManager for multi-project support.
            pubmed_api_url: URL for pubmed-search HTTP API (MCP-to-MCP communication).
        """
        self._default_base_dir = base_dir
        self._project_manager = project_manager
        self._converter = ReferenceConverter()
        self._pubmed_api_url = pubmed_api_url
        # Note: Directory is created on-demand when saving references,
        # not at initialization to avoid polluting root directory

    def _project_root_dir(self) -> str:
        """Get the current project root or best-effort workspace root."""
        if self._project_manager:
            try:
                paths = self._project_manager.get_project_paths()
                return paths.get("root", os.path.dirname(self.base_dir))
            except (ValueError, KeyError):
                pass

        base_path = Path(self.base_dir).resolve()
        return str(base_path.parent)

    def _notes_dir(self) -> str:
        return os.path.join(self._project_root_dir(), "notes")

    def _knowledge_maps_dir(self) -> str:
        return os.path.join(self._notes_dir(), "knowledge-maps")

    def _synthesis_pages_dir(self) -> str:
        return os.path.join(self._notes_dir(), "synthesis-pages")

    def _draft_section_notes_dir(self) -> str:
        return os.path.join(self._notes_dir(), "draft-sections")

    def _figure_notes_dir(self) -> str:
        return os.path.join(self._notes_dir(), "figures")

    def _table_notes_dir(self) -> str:
        return os.path.join(self._notes_dir(), "tables")

    def _context_notes_dir(self) -> str:
        return os.path.join(self._notes_dir(), "context")

    def _library_pages_dir(self) -> str:
        return os.path.join(self._notes_dir(), "library")

    def _current_project_slug(self) -> str:
        if self._project_manager:
            try:
                slug = self._project_manager.get_current_project()
                if slug:
                    return str(slug)
            except Exception:
                pass
        return Path(self._project_root_dir()).name

    def _dedupe_strings(self, values: Any) -> List[str]:
        if isinstance(values, str):
            candidates = [values]
        elif isinstance(values, list):
            candidates = values
        else:
            candidates = []

        deduped: List[str] = []
        seen: set[str] = set()
        for value in candidates:
            if not isinstance(value, str):
                continue
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    def _dedupe_provenance(self, entries: Any) -> List[Dict[str, Any]]:
        if not isinstance(entries, list):
            return []

        deduped: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            marker = json.dumps(entry, sort_keys=True, ensure_ascii=False)
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(entry)
        return deduped

    def _remove_identity_registry_entries(
        self, reference_id: str, payload: Optional[Dict[str, Any]] = None
    ) -> None:
        payload = payload or {}
        registry_specs = [
            (self._hash_registry_path(), [payload.get("content_hash")]),
            (self._pmid_registry_path(), [str(payload.get("pmid"))] if payload.get("pmid") else []),
            (
                self._doi_registry_path(),
                [str(payload.get("doi")).lower()] if payload.get("doi") else [],
            ),
        ]

        for registry_path, explicit_keys in registry_specs:
            registry = self._read_json_file(registry_path, {})
            if not registry:
                continue

            changed = False
            for key in explicit_keys:
                if key and registry.get(key) == reference_id:
                    registry.pop(key, None)
                    changed = True

            for key, value in list(registry.items()):
                if value == reference_id:
                    registry.pop(key, None)
                    changed = True

            if changed:
                self._write_json_file(registry_path, registry)

    def _registry_dir(self) -> str:
        return os.path.join(self._project_root_dir(), "registry")

    def _hash_registry_path(self) -> str:
        return os.path.join(self._registry_dir(), "by-hash.json")

    def _pmid_registry_path(self) -> str:
        return os.path.join(self._registry_dir(), "by-pmid.json")

    def _doi_registry_path(self) -> str:
        return os.path.join(self._registry_dir(), "by-doi.json")

    def _ensure_workspace_scaffolding(self) -> None:
        """Create the minimal directories needed for notes and registries."""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self._notes_dir(), exist_ok=True)
        os.makedirs(self._knowledge_maps_dir(), exist_ok=True)
        os.makedirs(self._synthesis_pages_dir(), exist_ok=True)
        os.makedirs(self._draft_section_notes_dir(), exist_ok=True)
        os.makedirs(self._figure_notes_dir(), exist_ok=True)
        os.makedirs(self._table_notes_dir(), exist_ok=True)
        os.makedirs(self._context_notes_dir(), exist_ok=True)
        os.makedirs(self._library_pages_dir(), exist_ok=True)
        os.makedirs(self._registry_dir(), exist_ok=True)

    def _yaml_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _slugify(self, value: str, fallback: str = "untitled") -> str:
        import re

        normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return normalized or fallback

    def _compute_text_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _extract_markdown_headings(self, markdown_text: str) -> List[str]:
        headings: List[str] = []
        seen: set[str] = set()

        for line in markdown_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue

            heading = stripped.lstrip("#").strip()
            if not heading or heading in seen:
                continue

            seen.add(heading)
            headings.append(heading)

        return headings

    def _infer_markdown_title(self, markdown_text: str, fallback: str) -> str:
        for line in markdown_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                title = stripped.lstrip("#").strip()
                if title:
                    return title
        return fallback

    def _build_markdown_summary(self, markdown_text: str, max_chars: int = 400) -> str:
        summary_parts: List[str] = []
        current_length = 0

        for line in markdown_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            summary_parts.append(stripped)
            current_length += len(stripped) + 1
            if current_length >= max_chars:
                break

        if not summary_parts:
            return ""

        summary = " ".join(summary_parts).strip()
        if len(summary) > max_chars:
            return summary[: max_chars - 3].rstrip() + "..."
        return summary

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

    def _extract_first_author_slug(self, payload: Dict[str, Any]) -> str:
        authors_full = payload.get("authors_full", [])
        authors = payload.get("authors", [])

        candidate = ""
        if authors_full and isinstance(authors_full[0], dict):
            candidate = str(authors_full[0].get("last_name", ""))
        elif authors:
            candidate = str(authors[0]).split()[0]

        return self._slugify(candidate, fallback="")

    def _build_graph_note_tags(
        self,
        note_type: str,
        note_domain: str,
        extra_tags: Optional[List[str]] = None,
    ) -> List[str]:
        candidates = [note_type, f"domain/{note_domain}", "graph/materialized"]
        project_slug = self._current_project_slug()
        if project_slug:
            candidates.append(f"project/{project_slug}")
        if extra_tags:
            candidates.extend(extra_tags)

        deduped: List[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = self._normalize_foam_tag(candidate)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

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

    def _reference_context_entries(self, payload: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
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
                {"kind": "journal", "label": journal, "alias": self._context_alias("journal", journal)}
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
                {"kind": "mesh", "label": mesh_term, "alias": self._context_alias("mesh", mesh_term)}
            )

        for section in self._dedupe_strings(payload.get("fulltext_sections", []))[:6]:
            contexts["sections"].append(
                {"kind": "section", "label": section, "alias": self._context_alias("section", section)}
            )

        return contexts

    def _visible_graph_tags(self, payload: Dict[str, Any]) -> List[str]:
        visible_prefixes = (
            "project/",
            "journal/",
            "author/",
            "topic/",
            "mesh/",
            "section/",
            "study/",
            "trust/",
            "analysis/",
            "fulltext/",
            "usage/",
        )
        return [
            tag
            for tag in self._dedupe_strings(payload.get("tags", []))
            if tag == "reference" or any(tag.startswith(prefix) for prefix in visible_prefixes)
        ][:14]

    def _build_reference_graph_context(self, payload: Dict[str, Any]) -> str:
        contexts = self._reference_context_entries(payload)
        lines: List[str] = []

        if contexts["journal"]:
            lines.append(f"- Journal hub: [[{contexts['journal'][0]['alias']}]]")
        if contexts["authors"]:
            lines.append(
                "- Author hubs: " + ", ".join(f"[[{item['alias']}]]" for item in contexts["authors"])
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
                "- Section hubs: " + ", ".join(f"[[{item['alias']}]]" for item in contexts["sections"])
            )

        visible_tags = self._visible_graph_tags(payload)
        if visible_tags:
            lines.append("- Graph tags: " + ", ".join(visible_tags))

        return "\n".join(lines)

    def _materialize_reference_context_notes(self) -> Dict[str, Any]:
        context_nodes: Dict[str, Dict[str, Any]] = {}
        expected_paths: List[str] = []
        project_slug = self._current_project_slug()

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

        materialized_nodes: List[Dict[str, Any]] = []
        for node in sorted(context_nodes.values(), key=lambda item: (item["kind"], item["label"].lower())):
            note_path = os.path.join(self._context_notes_dir(), f"{node['alias']}.md")
            expected_paths.append(note_path)
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
                body_lines.append(
                    f"- [[{reference['citation_key']}]]: {reference['title']}{year_text}"
                )

            note_type = f"{node['kind']}-note"
            self._write_graph_note(
                note_path,
                title=f"{node['kind'].title()}: {node['label']}",
                note_type=note_type,
                aliases=[node["alias"]],
                tags=self._build_graph_note_tags(
                    note_type,
                    "taxonomy",
                    [f"context/{node['kind']}", f"label/{self._slugify(node['label'], fallback=node['kind'])}"],
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
            materialized_nodes.append(
                {
                    "alias": node["alias"],
                    "title": f"{node['kind'].title()}: {node['label']}",
                    "kind": node["kind"],
                    "reference_count": len(references),
                }
            )

        self._prune_stale_graph_notes(self._context_notes_dir(), expected_paths)
        return {"nodes": materialized_nodes, "count": len(materialized_nodes)}

    def _materialize_library_overview(self, context_nodes: Dict[str, Any]) -> Dict[str, Any]:
        note_path = os.path.join(self._library_pages_dir(), "overview.md")
        project_slug = self._current_project_slug()

        snapshots = self._resolve_reference_snapshots(limit=max(len(self.list_references()), 1))
        total_references = len(snapshots)
        analyzed_count = sum(
            1 for snapshot in snapshots if snapshot["metadata"].get("analysis_completed")
        )
        fulltext_count = sum(
            1 for snapshot in snapshots if snapshot["metadata"].get("fulltext_ingested")
        )

        trust_counts: Dict[str, int] = {}
        source_counts: Dict[str, int] = {}
        journal_counts: Dict[str, int] = {}
        topic_counts: Dict[str, int] = {}
        unresolved_identity: List[Dict[str, str]] = []
        analysis_queue: List[Dict[str, str]] = []
        fulltext_queue: List[Dict[str, str]] = []
        recent_additions: List[Dict[str, str]] = []

        for snapshot in snapshots:
            metadata = snapshot["metadata"]
            reference_id = snapshot["reference_id"]
            citation_key = metadata.get("citation_key") or reference_id
            title = metadata.get("title", reference_id)
            year = str(metadata.get("year", "")).strip()

            trust_level = str(metadata.get("trust_level", "unknown") or "unknown")
            trust_counts[trust_level] = trust_counts.get(trust_level, 0) + 1

            source = str(metadata.get("source", "unknown") or "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1

            journal = str(metadata.get("journal", "")).strip()
            if journal:
                journal_counts[journal] = journal_counts.get(journal, 0) + 1

            for topic in self._dedupe_strings(metadata.get("keywords", []))[:5]:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

            ref_entry = {
                "citation_key": citation_key,
                "title": title,
                "year": year,
            }
            recent_additions.append(ref_entry)

            if reference_id.startswith(("local_", "web_", "markdown_")) and not metadata.get("pmid"):
                unresolved_identity.append(ref_entry)
            if not metadata.get("analysis_completed"):
                analysis_queue.append(ref_entry)
            if not metadata.get("fulltext_ingested"):
                fulltext_queue.append(ref_entry)

        top_context_hubs = sorted(
            context_nodes.get("nodes", []),
            key=lambda node: (-int(node.get("reference_count", 0)), node.get("title", "")),
        )[:8]
        top_journals = sorted(journal_counts.items(), key=lambda item: (-item[1], item[0].lower()))[:8]
        top_topics = sorted(topic_counts.items(), key=lambda item: (-item[1], item[0].lower()))[:8]

        body_lines = [
            "## Library Status",
            "",
            f"- Total references: {total_references}",
            f"- Analysis completed: {analyzed_count}",
            f"- Fulltext ingested: {fulltext_count}",
            f"- Context hubs: {context_nodes.get('count', 0)}",
            "",
            "## Trust Distribution",
            "",
        ]

        if trust_counts:
            for trust_level, count in sorted(trust_counts.items(), key=lambda item: (-item[1], item[0])):
                body_lines.append(f"- {trust_level}: {count}")
        else:
            body_lines.append("- No references in the library yet")

        body_lines.extend(["", "## Source Mix", ""])
        if source_counts:
            for source, count in sorted(source_counts.items(), key=lambda item: (-item[1], item[0])):
                body_lines.append(f"- {source}: {count}")
        else:
            body_lines.append("- No source mix available yet")

        body_lines.extend(["", "## Identity Resolution Queue", ""])
        if unresolved_identity:
            for item in unresolved_identity[:10]:
                year_text = f" ({item['year']})" if item["year"] else ""
                body_lines.append(f"- [[{item['citation_key']}]]: {item['title']}{year_text}")
        else:
            body_lines.append("- No unresolved local identities")

        body_lines.extend(["", "## Analysis Queue", ""])
        if analysis_queue:
            for item in analysis_queue[:10]:
                year_text = f" ({item['year']})" if item["year"] else ""
                body_lines.append(f"- [[{item['citation_key']}]]: {item['title']}{year_text}")
        else:
            body_lines.append("- All references have saved analysis")

        body_lines.extend(["", "## Fulltext Queue", ""])
        if fulltext_queue:
            for item in fulltext_queue[:10]:
                year_text = f" ({item['year']})" if item["year"] else ""
                body_lines.append(f"- [[{item['citation_key']}]]: {item['title']}{year_text}")
        else:
            body_lines.append("- Fulltext available for all references")

        body_lines.extend(["", "## Recent Additions", ""])
        if recent_additions:
            for item in recent_additions[:12]:
                year_text = f" ({item['year']})" if item["year"] else ""
                body_lines.append(f"- [[{item['citation_key']}]]: {item['title']}{year_text}")
        else:
            body_lines.append("- No references added yet")

        body_lines.extend(["", "## Top Context Hubs", ""])
        if top_context_hubs:
            for node in top_context_hubs:
                body_lines.append(
                    f"- [[{node['alias']}]]: {node['title']} ({node.get('reference_count', 0)} refs)"
                )
        else:
            body_lines.append("- No context hubs materialized yet")

        body_lines.extend(["", "## Top Journals", ""])
        if top_journals:
            for journal, count in top_journals:
                body_lines.append(f"- {journal}: {count}")
        else:
            body_lines.append("- No journal metadata yet")

        body_lines.extend(["", "## Top Topics", ""])
        if top_topics:
            for topic, count in top_topics:
                body_lines.append(f"- {topic}: {count}")
        else:
            body_lines.append("- No keyword topics yet")

        self._write_graph_note(
            note_path,
            title="Library Overview",
            note_type="library-overview",
            aliases=["library-overview"],
            tags=self._build_graph_note_tags(
                "library-overview",
                "library",
                ["dashboard/library", "workflow/library-first"],
            ),
            extra_fields={
                "note_class": "library-overview",
                "note_domain": "library",
                "project": project_slug,
                "reference_count": total_references,
                "analysis_completed_count": analyzed_count,
                "analysis_pending_count": len(analysis_queue),
                "fulltext_available_count": fulltext_count,
                "fulltext_missing_count": len(fulltext_queue),
                "identity_resolution_count": len(unresolved_identity),
                "context_hub_count": context_nodes.get("count", 0),
                "review_state": "n/a",
            },
            body="\n".join(body_lines),
        )

        return {"alias": "library-overview", "title": "Library Overview", "path": note_path}

    def _normalize_foam_tag(self, value: str) -> str:
        import re

        normalized = str(value).strip().lower().lstrip("#")
        normalized = normalized.replace("_", "-")
        normalized = re.sub(r"\s+", "-", normalized)
        normalized = re.sub(r"[^a-z0-9/-]+", "-", normalized)
        normalized = re.sub(r"-{2,}", "-", normalized)
        return normalized.strip("-/")

    def _foam_note_type(self, page_type: str) -> str:
        mapping = {
            "knowledge_map": "knowledge-map",
            "synthesis_page": "synthesis-page",
        }
        return mapping.get(page_type, page_type.replace("_", "-"))

    def _build_reference_tags(self, payload: Dict[str, Any]) -> List[str]:
        candidates = [
            payload.get("foam_type") or "reference",
            f"source/{payload.get('source', 'agent') or 'agent'}",
            f"trust/{payload.get('trust_level', 'agent') or 'agent'}",
            "analysis/completed" if payload.get("analysis_completed") else "analysis/pending",
            "fulltext/ingested" if payload.get("fulltext_ingested") else "fulltext/missing",
        ]
        project_slug = payload.get("project") or self._current_project_slug()
        if project_slug:
            candidates.append(f"project/{project_slug}")

        year = str(payload.get("year", "")).strip()
        if year.isdigit():
            candidates.append(f"year/{year}")

        journal_slug = payload.get("journal_slug") or self._slugify(
            payload.get("journal") or payload.get("journal_abbrev") or "", fallback=""
        )
        if journal_slug:
            candidates.append(f"journal/{journal_slug}")

        first_author = payload.get("first_author") or self._extract_first_author_slug(payload)
        if first_author:
            candidates.append(f"author/{first_author}")

        for usage_section in self._dedupe_strings(payload.get("usage_sections", []))[:6]:
            candidates.append(f"usage/{usage_section}")

        for fulltext_section in self._dedupe_strings(payload.get("fulltext_sections", []))[:6]:
            candidates.append(f"section/{fulltext_section}")

        for keyword in self._dedupe_strings(payload.get("keywords", []))[:8]:
            candidates.append(f"topic/{keyword}")

        for mesh_term in self._dedupe_strings(payload.get("mesh_terms", []))[:8]:
            candidates.append(f"mesh/{mesh_term}")

        publication_types = payload.get("publication_types") or payload.get("publication_type") or []
        for publication_type in self._dedupe_strings(publication_types)[:4]:
            candidates.append(f"study/{publication_type}")

        candidates.extend(self._dedupe_strings(payload.get("tags", [])))
        candidates.extend(self._dedupe_strings(payload.get("user_tags", [])))

        deduped: List[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = self._normalize_foam_tag(candidate)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)

        return deduped

    def _build_materialized_page_tags(
        self,
        page_type: str,
        *,
        query: str = "",
        focus: str = "",
    ) -> List[str]:
        candidates = [
            self._foam_note_type(page_type),
            "agent-wiki",
            "materialized",
            "reference-set",
            "domain/synthesis",
        ]
        project_slug = self._current_project_slug()
        if project_slug:
            candidates.append(f"project/{project_slug}")
        if query:
            candidates.append("query-backed")
        if focus:
            candidates.append("focus-driven")
            candidates.append(f"focus/{focus}")

        deduped: List[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = self._normalize_foam_tag(candidate)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)

        return deduped

    def _type_query_block(self, note_type: str, *, format_name: str = "count") -> List[str]:
        lines = [
            "```foam-query",
            "filter:",
            "  and:",
            f'    - type: "{self._yaml_escape(note_type)}"',
        ]
        if format_name == "count":
            lines.append("format: count")
        else:
            lines.extend(
                [
                    "select: [title, type, tags, backlink-count]",
                    "sort: title ASC",
                    f"format: {format_name}",
                ]
            )
        lines.append("```")
        return lines

    def _extract_markdown_section_blocks(self, markdown_text: str) -> List[Dict[str, str]]:
        if not markdown_text.strip():
            return []

        blocks: List[Dict[str, str]] = []
        current_title = ""
        current_lines: List[str] = []

        def flush() -> None:
            title = current_title.strip()
            content = "\n".join(current_lines).strip()
            if not title and not content:
                return
            blocks.append({"title": title or "Evidence Summary", "content": content})

        for line in markdown_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()
                if heading:
                    flush()
                    current_title = heading
                    current_lines = []
                    continue
            current_lines.append(line.rstrip())

        flush()
        return blocks

    def _key_findings_anchor(self) -> str:
        return "^key-findings"

    def _evidence_anchor(self, title: str) -> str:
        return f"^evidence-{self._slugify(title, 'section')}"

    def _build_evidence_block_specs(self, article: Dict[str, Any]) -> List[Dict[str, str]]:
        article_title = str(article.get("title", "")).strip().lower()
        parsed_blocks = self._extract_markdown_section_blocks(article.get("extracted_markdown", ""))

        parsed_by_key: Dict[str, str] = {}
        ordered_parsed: List[Dict[str, str]] = []
        for block in parsed_blocks:
            title = block.get("title", "").strip()
            if not title or title.lower() == article_title:
                continue

            key = self._slugify(title, "section")
            snippet = self._build_markdown_summary(block.get("content", ""), max_chars=480)
            ordered_parsed.append({"title": title, "content": snippet})
            parsed_by_key[key] = snippet

        specs: List[Dict[str, str]] = []
        seen: set[str] = set()
        for section in self._dedupe_strings(article.get("fulltext_sections", [])):
            if section.lower() == article_title:
                continue

            key = self._slugify(section, "section")
            if key in seen:
                continue

            seen.add(key)
            specs.append({"title": section, "content": parsed_by_key.get(key, "")})

        for block in ordered_parsed:
            key = self._slugify(block["title"], "section")
            if key in seen:
                continue

            seen.add(key)
            specs.append(block)

        return specs[:6]

    def _linked_reference_query_block(self, *, format_name: str) -> List[str]:
        lines = [
            "```foam-query",
            "filter:",
            "  and:",
            '    - type: "reference"',
            '    - links_from: "$current"',
        ]
        if format_name == "count":
            lines.append("format: count")
        else:
            lines.extend(
                [
                    "select: [title, type, tags, backlink-count]",
                    "sort: title ASC",
                    f"format: {format_name}",
                ]
            )
        lines.append("```")
        return lines

    def _write_text_source_artifact(self, ref_dir: str, file_name: str, content: str) -> str:
        source_dir = os.path.join(ref_dir, "source")
        os.makedirs(source_dir, exist_ok=True)
        destination = os.path.join(source_dir, file_name)
        with open(destination, "w", encoding="utf-8") as handle:
            handle.write(content)
        return destination

    def _load_reference_analysis(self, reference_id: str) -> Dict[str, Any]:
        analysis_path = Path(self.base_dir) / reference_id / "analysis.json"
        if not analysis_path.is_file():
            return {}

        try:
            return json.loads(analysis_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _resolve_reference_snapshots(
        self,
        reference_ids: Optional[List[str]] = None,
        *,
        query: str = "",
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        selected_ids: List[str] = []
        seen_ids: set[str] = set()

        if reference_ids:
            for ref_id in reference_ids:
                normalized = str(ref_id).strip()
                if not normalized or normalized in seen_ids:
                    continue
                seen_ids.add(normalized)
                selected_ids.append(normalized)
        elif query.strip():
            for metadata in self.search_local(query):
                ref_id = str(metadata.get("unique_id") or metadata.get("pmid") or "").strip()
                if not ref_id or ref_id in seen_ids:
                    continue
                seen_ids.add(ref_id)
                selected_ids.append(ref_id)
                if len(selected_ids) >= limit:
                    break
        else:
            all_metadata: List[Dict[str, Any]] = []
            for ref_id in self.list_references():
                metadata = self.get_metadata(ref_id)
                if not metadata:
                    continue
                metadata = dict(metadata)
                metadata["unique_id"] = metadata.get("unique_id") or ref_id
                all_metadata.append(metadata)

            all_metadata.sort(key=lambda item: item.get("saved_at", ""), reverse=True)
            selected_ids = [
                str(item.get("unique_id") or "").strip()
                for item in all_metadata[:limit]
                if str(item.get("unique_id") or "").strip()
            ]

        snapshots: List[Dict[str, Any]] = []
        for ref_id in selected_ids:
            metadata = self.get_metadata(ref_id)
            if not metadata:
                continue
            snapshots.append(
                {
                    "reference_id": ref_id,
                    "metadata": metadata,
                    "analysis": self._load_reference_analysis(ref_id),
                }
            )

        return snapshots

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
                    if stripped.startswith('title:'):
                        return stripped.split(":", 1)[1].strip().strip('"')
                    if stripped.startswith("# "):
                        return stripped[2:].strip()
        except Exception:
            pass
        return Path(file_path).stem.replace("-", " ").title()

    def _iter_materialized_pages(self, page_type: str) -> List[Dict[str, str]]:
        page_dir = (
            self._knowledge_maps_dir() if page_type == "knowledge_map" else self._synthesis_pages_dir()
        )
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
                    "alias": self._materialized_page_alias(page_type, slug),
                    "title": self._read_materialized_page_title(file_path),
                    "path": file_path,
                }
            )

        return pages

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
        generated_at = __import__('datetime').datetime.now().isoformat()
        page_path = self._materialized_page_path(page_type, slug)

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

    def _build_knowledge_map_body(
        self,
        snapshots: List[Dict[str, Any]],
        *,
        query: str = "",
    ) -> str:
        trust_counts: Dict[str, int] = {}
        missing_analysis: List[str] = []
        unresolved_identity: List[str] = []

        lines = ["## Scope", ""]
        if query:
            lines.append(f"- Query: {query}")
        lines.append(f"- References included: {len(snapshots)}")
        lines.append("")
        lines.append("## Coverage")
        lines.append("")

        for snapshot in snapshots:
            metadata = snapshot["metadata"]
            trust_level = metadata.get("trust_level", "unknown")
            trust_counts[trust_level] = trust_counts.get(trust_level, 0) + 1
            if not metadata.get("analysis_completed"):
                missing_analysis.append(snapshot["reference_id"])
            if str(snapshot["reference_id"]).startswith(("local_", "web_", "markdown_")):
                unresolved_identity.append(snapshot["reference_id"])

        if trust_counts:
            for trust_level, count in sorted(trust_counts.items()):
                lines.append(f"- {trust_level}: {count}")
        else:
            lines.append("- No references selected")

        lines.extend(["", "## Live Reference Count", ""])
        lines.extend(self._linked_reference_query_block(format_name="count"))
        lines.extend(["", "## Live Reference Table", ""])
        lines.extend(self._linked_reference_query_block(format_name="table"))

        lines.extend(["", "## Reference Graph", ""])
        for snapshot in snapshots:
            metadata = snapshot["metadata"]
            analysis = snapshot["analysis"]
            citation_key = metadata.get("citation_key") or snapshot["reference_id"]
            title = metadata.get("title", snapshot["reference_id"])
            year = metadata.get("year", "")
            year_text = f" ({year})" if year else ""
            source = metadata.get("source", "")
            trust_level = metadata.get("trust_level", "")
            summary = (
                analysis.get("summary")
                or metadata.get("analysis_summary")
                or metadata.get("abstract")
                or "No summary available yet."
            )
            summary = summary.replace("\n", " ").strip()
            if len(summary) > 260:
                summary = summary[:257].rstrip() + "..."
            lines.append(
                f"- [[{citation_key}]]: {title}{year_text} [{source}/{trust_level}]"
            )
            lines.append(f"  Evidence: {summary}")

        if snapshots:
            lines.extend(["", "## Embedded Evidence", ""])
            for snapshot in snapshots[:4]:
                metadata = snapshot["metadata"]
                citation_key = metadata.get("citation_key") or snapshot["reference_id"]
                evidence_blocks = self._build_evidence_block_specs(metadata)
                lines.append(f"### [[{citation_key}]]")
                lines.append("")
                lines.append(f"content-card![[{citation_key}#{self._key_findings_anchor()}]]")
                if evidence_blocks:
                    lines.append("")
                    lines.append(
                        f"content-inline![[{citation_key}#{self._evidence_anchor(evidence_blocks[0]['title'])}]]"
                    )
                lines.append("")

        if missing_analysis or unresolved_identity:
            lines.extend(["", "## Next Actions", ""])
            if unresolved_identity:
                lines.append(
                    "- Resolve canonical identity for: "
                    + ", ".join(sorted(set(unresolved_identity)))
                )
            if missing_analysis:
                lines.append(
                    "- Add structured analysis for: "
                    + ", ".join(sorted(set(missing_analysis)))
                )

        return "\n".join(lines)

    def _build_synthesis_body(
        self,
        snapshots: List[Dict[str, Any]],
        *,
        focus: str = "",
        summary_markdown: str = "",
    ) -> str:
        if summary_markdown.strip():
            synthesis_text = summary_markdown.strip()
        else:
            synthesis_lines = ["## Working Synthesis", ""]
            if focus:
                synthesis_lines.append(f"Focus: {focus}")
                synthesis_lines.append("")

            for snapshot in snapshots:
                metadata = snapshot["metadata"]
                analysis = snapshot["analysis"]
                citation_key = metadata.get("citation_key") or snapshot["reference_id"]
                contribution = (
                    analysis.get("summary")
                    or metadata.get("analysis_summary")
                    or metadata.get("abstract")
                    or "No synthesis text available."
                )
                contribution = contribution.replace("\n", " ").strip()
                if len(contribution) > 320:
                    contribution = contribution[:317].rstrip() + "..."
                synthesis_lines.append(f"- [[{citation_key}]]: {contribution}")

            synthesis_text = "\n".join(synthesis_lines)

        gaps = [
            snapshot["reference_id"]
            for snapshot in snapshots
            if not snapshot["metadata"].get("analysis_completed")
        ]
        no_fulltext = [
            snapshot["reference_id"]
            for snapshot in snapshots
            if not snapshot["metadata"].get("fulltext_ingested")
        ]

        lines = [synthesis_text, "", "## Evidence Base", ""]
        for snapshot in snapshots:
            metadata = snapshot["metadata"]
            citation_key = metadata.get("citation_key") or snapshot["reference_id"]
            year = metadata.get("year", "")
            title = metadata.get("title", snapshot["reference_id"])
            year_text = f" ({year})" if year else ""
            lines.append(f"- [[{citation_key}]]: {title}{year_text}")

        lines.extend(["", "## Live Evidence Table", ""])
        lines.extend(self._linked_reference_query_block(format_name="table"))

        if snapshots:
            lines.extend(["", "## Embedded Evidence", ""])
            for snapshot in snapshots[:4]:
                metadata = snapshot["metadata"]
                citation_key = metadata.get("citation_key") or snapshot["reference_id"]
                evidence_blocks = self._build_evidence_block_specs(metadata)
                lines.append(f"### [[{citation_key}]]")
                lines.append("")
                lines.append(f"content-card![[{citation_key}#{self._key_findings_anchor()}]]")
                if evidence_blocks:
                    lines.append("")
                    lines.append(
                        f"content-inline![[{citation_key}#{self._evidence_anchor(evidence_blocks[0]['title'])}]]"
                    )
                lines.append("")

        if gaps or no_fulltext:
            lines.extend(["", "## Gaps", ""])
            if gaps:
                lines.append("- Missing structured analysis: " + ", ".join(sorted(set(gaps))))
            if no_fulltext:
                lines.append("- Fulltext not yet ingested: " + ", ".join(sorted(set(no_fulltext))))

        return "\n".join(lines)

    def _read_json_file(self, file_path: str, default: Any) -> Any:
        if not os.path.exists(file_path):
            return default

        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return default

    def _write_json_file(self, file_path: str, payload: Any) -> None:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

    def _build_citation_key(self, article: Dict[str, Any], fallback_id: str) -> str:
        """Build a Foam-friendly citation key for verified and local references."""
        authors_full = article.get("authors_full", [])
        authors = article.get("authors", [])
        year = str(article.get("year", ""))

        first_author = ""
        if authors_full and isinstance(authors_full[0], dict):
            first_author = authors_full[0].get("last_name", "").lower()
        elif authors:
            first_author = authors[0].split()[0].lower() if authors[0] else ""

        import re

        first_author = re.sub(r"[^a-z0-9]", "", first_author)
        if not first_author:
            first_author = "local"

        return f"{first_author}{year}_{fallback_id}"

    def _normalize_reference_payload(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize metadata so metadata.json and Foam note stay in sync."""
        payload = dict(article)

        citation = payload.get("citation") or payload.get("citations")
        if not citation:
            citation = self._format_citation(payload)
        payload["citation"] = citation

        verified = bool(payload.get("verified", payload.get("_verified", False)))
        payload["verified"] = verified
        payload["data_source"] = (
            payload.get("data_source") or payload.get("_data_source") or payload.get("source", "agent")
        )

        payload["agent_notes"] = payload.get("agent_notes", payload.get("_agent_notes", ""))
        payload["user_notes"] = payload.get("user_notes", payload.get("_user_notes", ""))
        payload["user_tags"] = payload.get("user_tags", payload.get("_user_tags", []))

        payload["content_hash"] = payload.get("content_hash", payload.get("_content_hash", ""))
        payload["imported_from"] = payload.get("imported_from", "")
        payload["fulltext_ingested"] = bool(payload.get("fulltext_ingested", False))
        payload["fulltext_unavailable_reason"] = payload.get("fulltext_unavailable_reason", "")
        payload["asset_aware_doc_id"] = payload.get("asset_aware_doc_id")
        payload["fulltext_sections"] = payload.get("fulltext_sections", [])
        payload["analysis_completed"] = bool(payload.get("analysis_completed", False))
        payload["analysis_summary"] = payload.get("analysis_summary", "")
        payload["usage_sections"] = payload.get("usage_sections", [])
        payload["keywords"] = self._dedupe_strings(payload.get("keywords", []))
        payload["mesh_terms"] = self._dedupe_strings(payload.get("mesh_terms", []))
        payload["publication_types"] = self._dedupe_strings(
            payload.get("publication_types") or payload.get("publication_type") or []
        )
        payload["legacy_aliases"] = self._dedupe_strings(payload.get("legacy_aliases", []))
        payload["note_materialized"] = True
        payload["provenance"] = self._dedupe_provenance(payload.get("provenance", []))

        saved_at = payload.get("saved_at")
        if hasattr(saved_at, "isoformat"):
            payload["saved_at"] = saved_at.isoformat()

        if not payload.get("citation_key") and payload.get("unique_id"):
            payload["citation_key"] = self._build_citation_key(payload, payload["unique_id"])

        if "trust_level" not in payload:
            if verified:
                payload["trust_level"] = "verified"
            elif payload.get("asset_aware_doc_id") or payload.get("fulltext_sections"):
                payload["trust_level"] = "extracted"
            elif payload.get("source") in {"manual", "local", "web", "markdown"}:
                payload["trust_level"] = "user"
            else:
                payload["trust_level"] = "agent"

        payload["foam_type"] = payload.get("foam_type") or "reference"
        payload["note_class"] = payload.get("note_class") or payload["foam_type"]
        payload["note_domain"] = payload.get("note_domain") or "literature"
        payload["project"] = payload.get("project") or self._current_project_slug()
        payload["first_author"] = payload.get("first_author") or self._extract_first_author_slug(payload)
        payload["journal_slug"] = payload.get("journal_slug") or self._slugify(
            payload.get("journal") or payload.get("journal_abbrev") or "", fallback=""
        )
        payload["analysis_state"] = "completed" if payload.get("analysis_completed") else "pending"
        payload["fulltext_state"] = "ingested" if payload.get("fulltext_ingested") else "missing"
        payload["review_state"] = payload.get("review_state") or "n/a"
        payload["tags"] = self._build_reference_tags(payload)

        return payload

    def _upsert_identity_registry(self, payload: Dict[str, Any]) -> None:
        if payload.get("unique_id"):
            self._remove_identity_registry_entries(payload["unique_id"])

        if payload.get("content_hash"):
            by_hash = self._read_json_file(self._hash_registry_path(), {})
            by_hash[payload["content_hash"]] = payload["unique_id"]
            self._write_json_file(self._hash_registry_path(), by_hash)

        if payload.get("pmid"):
            by_pmid = self._read_json_file(self._pmid_registry_path(), {})
            by_pmid[str(payload["pmid"])] = payload["unique_id"]
            self._write_json_file(self._pmid_registry_path(), by_pmid)

        if payload.get("doi"):
            by_doi = self._read_json_file(self._doi_registry_path(), {})
            by_doi[str(payload["doi"]).lower()] = payload["unique_id"]
            self._write_json_file(self._doi_registry_path(), by_doi)

    def _append_log(self, event_type: str, payload: Dict[str, Any]) -> None:
        log_path = os.path.join(self._notes_dir(), "log.md")
        if not os.path.exists(log_path):
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write("# Knowledge Base Log\n\n")

        title = payload.get("title", payload.get("unique_id", "unknown"))
        entry = (
            f"- {payload.get('saved_at', '') or __import__('datetime').datetime.now().isoformat()} "
            f"[{event_type}] {payload.get('unique_id', '')} :: {title} "
            f"(source={payload.get('source', '')}, trust={payload.get('trust_level', '')})\n"
        )
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(entry)

    def _extract_wikilinks(self, content: str) -> List[str]:
        seen: set[str] = set()
        links: List[str] = []
        for match in re.findall(r"\[\[([^\]]+)\]\]", content):
            normalized = str(match).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            links.append(normalized)
        return links

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

    def _extract_draft_sections(self, markdown_text: str, draft_filename: str) -> List[Dict[str, str]]:
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

    def _load_asset_manifest(self) -> Dict[str, Any]:
        manifest_path = os.path.join(self._project_root_dir(), "results", "manifest.json")
        return self._read_json_file(manifest_path, {"figures": [], "tables": []})

    def _read_text_preview(self, file_path: str, max_chars: int = 1200) -> str:
        suffix = Path(file_path).suffix.lower()
        if suffix not in {".md", ".csv", ".html", ".txt"}:
            return ""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except Exception:
            return ""
        return content[:max_chars].strip()

    def _asset_aware_artifact_dir(self, reference_id: str) -> Path:
        return Path(self.base_dir) / reference_id / "artifacts" / "asset-aware"

    def _normalize_match_text(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()

    def _display_line_range(self, line_start: Any, line_end: Any) -> str:
        if not isinstance(line_start, int):
            return ""
        if isinstance(line_end, int) and line_end >= line_start:
            start_display = line_start + 1
            end_display = max(start_display, line_end)
            return str(start_display) if start_display == end_display else f"{start_display}-{end_display}"
        return str(line_start + 1)

    def _segment_bbox(self, segment: Dict[str, Any]) -> List[float]:
        left = segment.get("left")
        top = segment.get("top")
        width = segment.get("width")
        height = segment.get("height")
        if all(isinstance(value, (int, float)) for value in (left, top, width, height)):
            return [float(left), float(top), float(left + width), float(top + height)]
        return []

    def _section_path_from_hierarchy(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, dict):
            ordered_keys = sorted(value.keys(), key=lambda item: int(str(item)) if str(item).isdigit() else str(item))
            return [str(value[key]).strip() for key in ordered_keys if str(value[key]).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _load_reference_asset_contexts(self) -> List[Dict[str, Any]]:
        contexts: List[Dict[str, Any]] = []
        for reference_id in self.list_references():
            metadata = self.get_metadata(reference_id)
            if not metadata:
                continue

            artifact_dir = self._asset_aware_artifact_dir(reference_id)
            manifest = self._read_json_file(str(artifact_dir / "manifest.json"), {})
            blocks = self._read_json_file(str(artifact_dir / "blocks.json"), [])
            segmentation = self._read_json_file(str(artifact_dir / "segmentation.json"), {})
            if not manifest and not blocks and not segmentation:
                continue

            contexts.append(
                {
                    "reference_id": reference_id,
                    "metadata": metadata,
                    "manifest": manifest,
                    "blocks": blocks if isinstance(blocks, list) else [],
                    "segmentation": segmentation if isinstance(segmentation, dict) else {},
                }
            )
        return contexts

    def _score_asset_manifest_candidate(
        self,
        *,
        filename: str,
        caption: str,
        source_asset: Dict[str, Any],
    ) -> int:
        score = 0
        registered_stem = self._normalize_match_text(Path(filename).stem)
        registered_caption = self._normalize_match_text(caption)
        source_caption = self._normalize_match_text(source_asset.get("caption", ""))
        source_id = self._normalize_match_text(source_asset.get("id", ""))
        source_path_stem = self._normalize_match_text(Path(str(source_asset.get("path", ""))).stem)
        source_preview = self._normalize_match_text(source_asset.get("preview", ""))

        if registered_caption and source_caption:
            if registered_caption == source_caption:
                score += 20
            elif registered_caption in source_caption or source_caption in registered_caption:
                score += 10

        if registered_stem and source_path_stem:
            if registered_stem == source_path_stem:
                score += 12
            elif registered_stem in source_path_stem or source_path_stem in registered_stem:
                score += 6

        if registered_stem and source_id:
            if registered_stem == source_id:
                score += 8
            elif registered_stem in source_id or source_id in registered_stem:
                score += 4

        if registered_stem and source_preview and registered_stem in source_preview:
            score += 3

        return score

    def _find_asset_source_block(
        self,
        blocks: List[Dict[str, Any]],
        source_block_id: str,
    ) -> Dict[str, Any]:
        if not source_block_id:
            return {}
        for block in blocks:
            if str(block.get("block_id") or "") == source_block_id:
                return block
        return {}

    def _find_segmentation_segment(
        self,
        segmentation: Dict[str, Any],
        source_asset: Dict[str, Any],
    ) -> Dict[str, Any]:
        segments = segmentation.get("segments", [])
        if not isinstance(segments, list):
            return {}

        source_block_id = str(source_asset.get("source_block_id") or "")
        source_asset_id = str(source_asset.get("id") or "")
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            metadata = segment.get("metadata") or {}
            if source_block_id and (
                str(segment.get("segment_id") or "") == source_block_id
                or str(metadata.get("source_block_id") or "") == source_block_id
            ):
                return segment

        for segment in segments:
            if not isinstance(segment, dict):
                continue
            if source_asset_id and str(segment.get("asset_id") or "") == source_asset_id:
                return segment

        return {}

    def _resolve_asset_source_fragment(
        self,
        asset_type: str,
        filename: str,
        caption: str,
        reference_contexts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        manifest_key = "figures" if asset_type == "figure" else "tables"
        best_match: Dict[str, Any] = {}
        best_score = 0

        for context in reference_contexts:
            manifest_assets = ((context.get("manifest") or {}).get("assets") or {}).get(manifest_key, [])
            if not isinstance(manifest_assets, list):
                continue

            for source_asset in manifest_assets:
                if not isinstance(source_asset, dict):
                    continue

                score = self._score_asset_manifest_candidate(
                    filename=filename,
                    caption=caption,
                    source_asset=source_asset,
                )
                if score <= best_score:
                    continue

                source_block_id = str(source_asset.get("source_block_id") or "")
                block = self._find_asset_source_block(context.get("blocks", []), source_block_id)
                segment = self._find_segmentation_segment(context.get("segmentation", {}), source_asset)

                line_start = None
                line_end = None
                block_metadata = block.get("metadata") or {}
                if isinstance(block_metadata.get("line_start"), int):
                    line_start = int(block_metadata["line_start"])
                elif isinstance(segment.get("line_start"), int):
                    line_start = int(segment["line_start"])
                elif isinstance(source_asset.get("line_start"), int):
                    line_start = int(source_asset["line_start"])

                if isinstance(block_metadata.get("line_end"), int):
                    line_end = int(block_metadata["line_end"])
                elif isinstance(segment.get("line_end"), int):
                    line_end = int(segment["line_end"])
                elif isinstance(source_asset.get("line_end"), int):
                    line_end = int(source_asset["line_end"])

                section_path = self._section_path_from_hierarchy(block.get("section_hierarchy"))
                if not section_path:
                    section_path = self._section_path_from_hierarchy(segment.get("section_hierarchy"))
                if not section_path and source_asset.get("section_title"):
                    section_path = [str(source_asset.get("section_title"))]

                bbox = block.get("bbox") if isinstance(block.get("bbox"), list) else []
                if not bbox:
                    bbox = self._segment_bbox(segment)

                snippet = str(block.get("text") or "").strip()
                if not snippet:
                    snippet = str(segment.get("text") or "").strip()
                if not snippet:
                    snippet = str(source_asset.get("markdown") or source_asset.get("preview") or source_asset.get("caption") or "").strip()

                best_score = score
                best_match = {
                    "reference_id": context["reference_id"],
                    "citation_key": context["metadata"].get("citation_key", context["reference_id"]),
                    "doc_id": context["metadata"].get("asset_aware_doc_id")
                    or (context.get("manifest") or {}).get("doc_id", ""),
                    "asset_id": str(source_asset.get("id") or ""),
                    "source_block_id": source_block_id,
                    "page": block.get("page") or segment.get("page_number") or source_asset.get("page"),
                    "bbox": bbox,
                    "line_start": line_start,
                    "line_end": line_end,
                    "line_range": self._display_line_range(line_start, line_end),
                    "section_path": section_path,
                    "snippet": snippet,
                }

        return best_match if best_score >= 10 else {}

    def _asset_anchor(self, label: str, fallback: str = "fragment") -> str:
        return f"^{self._slugify(label, fallback)}"

    def _build_table_preview_fragments(self, preview: str) -> List[Dict[str, str]]:
        lines = [line.rstrip() for line in preview.splitlines() if line.strip()]
        if len(lines) < 3:
            return []

        if "|" in lines[0] and "|" in lines[1]:
            header = lines[0]
            separator = lines[1]
            rows = [line for line in lines[2:] if "|" in line]
            return [
                {
                    "title": f"Row {index}",
                    "content": "\n".join([header, separator, row]),
                    "anchor": f"^table-row-{index}",
                }
                for index, row in enumerate(rows[:5], start=1)
            ]

        if "," in lines[0]:
            header = lines[0]
            rows = lines[1:6]
            return [
                {
                    "title": f"Row {index}",
                    "content": "\n".join([header, row]),
                    "anchor": f"^table-row-{index}",
                }
                for index, row in enumerate(rows, start=1)
            ]

        return []

    def _materialize_asset_graph_notes(self) -> Dict[str, Any]:
        manifest = self._load_asset_manifest()
        project_root = Path(self._project_root_dir())
        project_slug = self._current_project_slug()
        reference_asset_contexts = self._load_reference_asset_contexts()
        expected_figure_paths: List[str] = []
        expected_table_paths: List[str] = []
        figures: List[Dict[str, Any]] = []
        tables: List[Dict[str, Any]] = []
        aliases: Dict[str, Dict[str, str]] = {"figure": {}, "table": {}}

        from med_paper_assistant.infrastructure.persistence.data_artifact_tracker import DataArtifactTracker

        tracker = DataArtifactTracker(project_root / ".audit", project_root)

        for asset_type, entries, notes_dir, folder in [
            ("figure", manifest.get("figures", []), self._figure_notes_dir(), "figures"),
            ("table", manifest.get("tables", []), self._table_notes_dir(), "tables"),
        ]:
            for entry in entries:
                number = int(entry.get("number", 0) or 0)
                filename = str(entry.get("filename", "")).strip()
                if number <= 0 or not filename:
                    continue

                slug = self._slugify(f"{asset_type}-{number}-{Path(filename).stem}")
                alias = f"{asset_type}-{number}"
                aliases[asset_type][str(number)] = alias
                note_path = os.path.join(notes_dir, f"{slug}.md")
                expected = expected_figure_paths if asset_type == "figure" else expected_table_paths
                expected.append(note_path)

                relative_asset_path = f"results/{folder}/{filename}"
                asset_path = project_root / relative_asset_path
                review = tracker.get_asset_review(relative_asset_path, asset_type=asset_type)
                review_state = "reviewed" if review else "pending"
                fragment_anchors: List[str] = []
                source_fragment = self._resolve_asset_source_fragment(
                    asset_type,
                    filename,
                    str(entry.get("caption", filename)),
                    reference_asset_contexts,
                )

                extra_tags = [
                    f"asset/{asset_type}",
                    f"review/{review_state}",
                    f"number/{number}",
                    f"format/{Path(filename).suffix.lstrip('.').lower() or 'unknown'}",
                ]
                title_prefix = "Figure" if asset_type == "figure" else "Table"
                title = f"{title_prefix} {number}: {entry.get('caption', filename)}"
                summary_anchor = self._asset_anchor("asset-summary")
                fragment_anchors.append(summary_anchor)
                body_lines = [
                    "## Asset Summary",
                    "",
                    f"Caption: {entry.get('caption', filename)}",
                    f"Source asset: {relative_asset_path}",
                    f"Review state: {review_state}",
                    "",
                    summary_anchor,
                ]

                if asset_type == "figure" and asset_path.exists():
                    relative_embed = os.path.relpath(asset_path, Path(note_path).parent).replace("\\", "/")
                    preview_anchor = self._asset_anchor("asset-preview")
                    fragment_anchors.append(preview_anchor)
                    body_lines.extend([
                        "",
                        "## Figure Preview",
                        "",
                        f"![{title}]({relative_embed})",
                        "",
                        preview_anchor,
                    ])

                preview = self._read_text_preview(str(asset_path)) if asset_path.exists() else ""
                if preview:
                    preview_anchor = self._asset_anchor("data-preview")
                    fragment_anchors.append(preview_anchor)
                    body_lines.extend(["", "## Data Preview", "", preview, "", preview_anchor])

                    if asset_type == "table":
                        table_fragments = self._build_table_preview_fragments(preview)
                        if table_fragments:
                            body_lines.extend(["", "## Table Fragments", ""])
                            for fragment in table_fragments:
                                fragment_anchors.append(fragment["anchor"])
                                body_lines.extend(
                                    [
                                        f"### {fragment['title']}",
                                        "",
                                        fragment["content"],
                                        "",
                                        fragment["anchor"],
                                        "",
                                    ]
                                )

                if review:
                    observations = [str(item) for item in review.get("observations", [])]
                    if observations:
                        body_lines.extend(["", "## Review Observations", ""])
                        for index, item in enumerate(observations, start=1):
                            anchor = f"^review-observation-{index}"
                            fragment_anchors.append(anchor)
                            body_lines.extend(
                                [
                                    f"### Observation {index}",
                                    "",
                                    item,
                                    "",
                                    anchor,
                                    "",
                                ]
                            )
                    evidence_excerpt = str(review.get("evidence_excerpt", "")).strip()
                    if evidence_excerpt:
                        excerpt_anchor = self._asset_anchor("evidence-excerpt")
                        fragment_anchors.append(excerpt_anchor)
                        body_lines.extend(
                            [
                                "",
                                "## Evidence Excerpt",
                                "",
                                evidence_excerpt,
                                "",
                                excerpt_anchor,
                            ]
                        )

                if source_fragment:
                    source_fragment_anchor = self._asset_anchor("source-fragment")
                    source_bbox_anchor = self._asset_anchor("source-bbox")
                    source_snippet_anchor = self._asset_anchor("source-snippet")
                    fragment_anchors.extend(
                        [source_fragment_anchor, source_bbox_anchor, source_snippet_anchor]
                    )
                    body_lines.extend(
                        [
                            "",
                            "## Source Fragment",
                            "",
                            f"- Reference: [[{source_fragment['citation_key']}]]",
                            f"- Doc ID: {source_fragment['doc_id'] or 'unknown'}",
                            f"- Asset ID: {source_fragment['asset_id'] or 'unknown'}",
                            f"- Source Block: {source_fragment['source_block_id'] or 'unknown'}",
                            f"- Page: {source_fragment['page'] or 'unknown'}",
                        ]
                    )
                    if source_fragment.get("line_range"):
                        body_lines.append(f"- Lines: {source_fragment['line_range']}")
                    if source_fragment.get("section_path"):
                        body_lines.append(
                            f"- Section: {' > '.join(source_fragment['section_path'])}"
                        )
                    body_lines.extend(["", source_fragment_anchor, ""])

                    if source_fragment.get("bbox"):
                        body_lines.extend(
                            [
                                "### Source Bounding Box",
                                "",
                                f"{source_fragment['bbox']}",
                                "",
                                source_bbox_anchor,
                                "",
                            ]
                        )

                    if source_fragment.get("snippet"):
                        body_lines.extend(
                            [
                                "### Source Snippet",
                                "",
                                source_fragment["snippet"],
                                "",
                                source_snippet_anchor,
                                "",
                            ]
                        )

                self._write_graph_note(
                    note_path,
                    title=title,
                    note_type=f"{asset_type}-note",
                    aliases=[alias, slug],
                    tags=self._build_graph_note_tags(f"{asset_type}-note", "asset", extra_tags),
                    extra_fields={
                        "note_class": f"{asset_type}-note",
                        "note_domain": "asset",
                        "project": project_slug,
                        "asset_type": asset_type,
                        "asset_number": number,
                        "asset_filename": filename,
                        "source_path": relative_asset_path,
                        "review_state": review_state,
                        "fragment_anchors": fragment_anchors,
                        "source_doc_id": source_fragment.get("doc_id") if source_fragment else None,
                        "source_asset_id": source_fragment.get("asset_id") if source_fragment else None,
                        "source_block_id": source_fragment.get("source_block_id") if source_fragment else None,
                        "source_reference": source_fragment.get("citation_key") if source_fragment else None,
                        "source_page": source_fragment.get("page") if source_fragment else None,
                        "source_bbox": source_fragment.get("bbox") if source_fragment else None,
                        "source_line_range": source_fragment.get("line_range") if source_fragment else None,
                        "source_section_path": source_fragment.get("section_path") if source_fragment else None,
                    },
                    body="\n".join(body_lines),
                )

                target_collection = figures if asset_type == "figure" else tables
                target_collection.append({"alias": alias, "title": title, "filename": filename})

        self._prune_stale_graph_notes(self._figure_notes_dir(), expected_figure_paths)
        self._prune_stale_graph_notes(self._table_notes_dir(), expected_table_paths)
        return {"figures": figures, "tables": tables, "aliases": aliases}

    def _materialize_draft_section_notes(self, asset_aliases: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
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
            except Exception:
                continue

            for section in self._extract_draft_sections(content, draft_path.name):
                section_title = section["title"]
                section_content = section["content"]
                section_kind = self._section_kind(section_title)
                section_slug = self._slugify(f"{draft_path.stem}-{section_title}")
                alias = f"draft-section-{section_slug}"
                note_path = os.path.join(self._draft_section_notes_dir(), f"{section_slug}.md")
                expected_paths.append(note_path)

                linked_notes = self._extract_wikilinks(section_content)
                linked_figures = [
                    asset_aliases["figure"].get(match)
                    for match in re.findall(r"\bFigure\s+(\d+)\b", section_content, flags=re.IGNORECASE)
                ]
                linked_tables = [
                    asset_aliases["table"].get(match)
                    for match in re.findall(r"\bTable\s+(\d+)\b", section_content, flags=re.IGNORECASE)
                ]
                asset_links = [link for link in linked_figures + linked_tables if link]

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
                nodes.append({"alias": alias, "title": f"{section_title} ({draft_path.stem})"})

        self._prune_stale_graph_notes(self._draft_section_notes_dir(), expected_paths)
        return nodes

    def _rebuild_index(self) -> Dict[str, Any]:
        index_path = os.path.join(self._notes_dir(), "index.md")
        context_nodes = self._materialize_reference_context_notes()
        library_overview = self._materialize_library_overview(context_nodes)
        asset_nodes = self._materialize_asset_graph_notes()
        draft_section_nodes = self._materialize_draft_section_notes(asset_nodes.get("aliases", {}))
        lines = [
            "# Knowledge Base Index",
            "",
            "## Live Graph Counts",
            "",
            "### References",
            "",
        ]
        lines.extend(self._type_query_block("reference", format_name="count"))
        lines.extend(["", "### Draft Sections", ""])
        lines.extend(self._type_query_block("draft-section", format_name="count"))
        lines.extend(["", "### Figures", ""])
        lines.extend(self._type_query_block("figure-note", format_name="count"))
        lines.extend(["", "### Tables", ""])
        lines.extend(self._type_query_block("table-note", format_name="count"))
        lines.extend(["", "### Library Views", ""])
        lines.extend(self._type_query_block("library-overview", format_name="count"))
        lines.extend(["", f"- Context hubs: {context_nodes['count']}"])
        lines.extend(["", "## References", ""])

        for ref_id in sorted(self.list_references()):
            metadata = self.get_metadata(ref_id)
            if not metadata:
                continue

            citation_key = metadata.get("citation_key") or ref_id
            title = metadata.get("title", ref_id)
            year = metadata.get("year", "")
            source = metadata.get("source", "")
            trust_level = metadata.get("trust_level", "")
            year_text = f" ({year})" if year else ""
            lines.append(
                f"- [[{citation_key}]]: {title}{year_text} [{source}/{trust_level}]"
            )

        knowledge_maps = self._iter_materialized_pages("knowledge_map")
        lines.extend(["", "## Knowledge Maps", ""])
        if knowledge_maps:
            for page in knowledge_maps:
                lines.append(f"- [[{page['alias']}]]: {page['title']} [knowledge_map]")
        else:
            lines.append("- None materialized yet")

        synthesis_pages = self._iter_materialized_pages("synthesis_page")
        lines.extend(["", "## Synthesis Pages", ""])
        if synthesis_pages:
            for page in synthesis_pages:
                lines.append(f"- [[{page['alias']}]]: {page['title']} [synthesis_page]")
        else:
            lines.append("- None materialized yet")

        lines.extend(["", "## Draft Sections", ""])
        if draft_section_nodes:
            for node in sorted(draft_section_nodes, key=lambda item: item["title"]):
                lines.append(f"- [[{node['alias']}]]: {node['title']} [draft-section]")
        else:
            lines.append("- No draft sections materialized yet")

        lines.extend(["", "## Context Hubs", ""])
        if context_nodes["nodes"]:
            for node in sorted(context_nodes["nodes"], key=lambda item: (item["kind"], item["title"])):
                lines.append(f"- [[{node['alias']}]]: {node['title']} [{node['kind']}]")
        else:
            lines.append("- No context hubs materialized yet")

        lines.extend(["", "## Library Views", ""])
        lines.append(f"- [[{library_overview['alias']}]]: {library_overview['title']} [library]")

        lines.extend(["", "## Figures", ""])
        if asset_nodes["figures"]:
            for node in sorted(asset_nodes["figures"], key=lambda item: item["title"]):
                lines.append(f"- [[{node['alias']}]]: {node['title']} [figure]")
        else:
            lines.append("- No figures registered yet")

        lines.extend(["", "## Tables", ""])
        if asset_nodes["tables"]:
            for node in sorted(asset_nodes["tables"], key=lambda item: item["title"]):
                lines.append(f"- [[{node['alias']}]]: {node['title']} [table]")
        else:
            lines.append("- No tables registered yet")

        with open(index_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        return {
            "references": len(self.list_references()),
            "draft_sections": len(draft_section_nodes),
            "context_hubs": context_nodes["count"],
            "library_views": 1,
            "figures": len(asset_nodes["figures"]),
            "tables": len(asset_nodes["tables"]),
        }

    def refresh_foam_graph(self) -> Dict[str, Any]:
        """Regenerate index and graph-facing note nodes for the active project."""
        self._ensure_workspace_scaffolding()
        return self._rebuild_index()

    def _copy_source_artifact(self, file_path: str, ref_dir: str) -> str:
        source_dir = os.path.join(ref_dir, "source")
        os.makedirs(source_dir, exist_ok=True)
        suffix = Path(file_path).suffix or ".bin"
        destination = os.path.join(source_dir, f"original{suffix}")
        shutil.copy2(file_path, destination)
        return destination

    def _persist_extracted_artifacts(self, ref_dir: str, payload: Dict[str, Any]) -> None:
        extracted_markdown = payload.get("extracted_markdown", "")
        manifest = payload.get("asset_aware_manifest")
        blocks = payload.get("asset_aware_blocks")
        segmentation = payload.get("asset_aware_segmentation")
        artifact_dir = os.path.join(ref_dir, "artifacts", "asset-aware")

        if extracted_markdown or manifest or blocks or segmentation:
            os.makedirs(artifact_dir, exist_ok=True)

        if extracted_markdown:
            with open(os.path.join(artifact_dir, "sections.md"), "w", encoding="utf-8") as handle:
                handle.write(extracted_markdown)

        if manifest:
            self._write_json_file(os.path.join(artifact_dir, "manifest.json"), manifest)

        if blocks:
            self._write_json_file(os.path.join(artifact_dir, "blocks.json"), blocks)

        if segmentation:
            self._write_json_file(os.path.join(artifact_dir, "segmentation.json"), segmentation)

    def _files_have_same_content(self, source_path: str, target_path: str) -> bool:
        if not os.path.exists(source_path) or not os.path.exists(target_path):
            return False
        if os.path.getsize(source_path) != os.path.getsize(target_path):
            return False
        return self.compute_content_hash(source_path) == self.compute_content_hash(target_path)

    def _build_conflict_copy_path(self, target_path: str, source_ref_id: str) -> str:
        target = Path(target_path)
        suffix = "".join(target.suffixes)
        stem = target.name[: -len(suffix)] if suffix else target.name
        candidate = target.with_name(f"{stem}.from-{source_ref_id}{suffix}")
        counter = 2

        while candidate.exists():
            candidate = target.with_name(f"{stem}.from-{source_ref_id}.{counter}{suffix}")
            counter += 1

        return str(candidate)

    def _merge_artifact_tree(
        self,
        source_dir: str,
        target_dir: str,
        source_ref_id: str,
        target_root_dir: str,
    ) -> List[str]:
        conflicts: List[str] = []

        for root, _, files in os.walk(source_dir):
            relative_root = os.path.relpath(root, source_dir)
            destination_root = (
                target_dir if relative_root == "." else os.path.join(target_dir, relative_root)
            )
            os.makedirs(destination_root, exist_ok=True)

            for file_name in files:
                source_path = os.path.join(root, file_name)
                destination_path = os.path.join(destination_root, file_name)

                if not os.path.exists(destination_path):
                    shutil.copy2(source_path, destination_path)
                    continue

                if self._files_have_same_content(source_path, destination_path):
                    continue

                conflict_path = self._build_conflict_copy_path(destination_path, source_ref_id)
                shutil.copy2(source_path, conflict_path)
                conflicts.append(os.path.relpath(conflict_path, target_root_dir))

        return conflicts

    def _merge_reference_artifacts(self, source_ref_dir: str, target_ref_dir: str) -> List[str]:
        """Merge durable artifacts from one reference directory into another."""
        if not os.path.exists(source_ref_dir) or source_ref_dir == target_ref_dir:
            return []

        source_ref_id = os.path.basename(source_ref_dir)
        conflicts: List[str] = []

        for relative_dir in ("source", os.path.join("artifacts", "asset-aware")):
            source_dir = os.path.join(source_ref_dir, relative_dir)
            target_dir = os.path.join(target_ref_dir, relative_dir)
            if os.path.isdir(source_dir):
                os.makedirs(target_dir, exist_ok=True)
                conflicts.extend(
                    self._merge_artifact_tree(
                        source_dir,
                        target_dir,
                        source_ref_id,
                        target_ref_dir,
                    )
                )

        source_analysis = os.path.join(source_ref_dir, "analysis.json")
        target_analysis = os.path.join(target_ref_dir, "analysis.json")
        if os.path.exists(source_analysis):
            if not os.path.exists(target_analysis):
                shutil.copy2(source_analysis, target_analysis)
            elif not self._files_have_same_content(source_analysis, target_analysis):
                conflict_path = self._build_conflict_copy_path(target_analysis, source_ref_id)
                shutil.copy2(source_analysis, conflict_path)
                conflicts.append(os.path.relpath(conflict_path, target_ref_dir))

        return conflicts

    def _persist_reference_payload(
        self,
        payload: Dict[str, Any],
        log_event: str,
        *,
        rebuild_index: bool = True,
    ) -> str:
        self._ensure_workspace_scaffolding()
        payload = self._normalize_reference_payload(payload)
        ref_dir = os.path.join(self.base_dir, payload["unique_id"])
        os.makedirs(ref_dir, exist_ok=True)

        self._write_json_file(os.path.join(ref_dir, "metadata.json"), payload)
        if payload.get("provenance"):
            self._write_json_file(os.path.join(ref_dir, "provenance.json"), payload["provenance"])

        content = self._generate_content_md(payload)
        md_filename = f"{payload['citation_key']}.md"
        with open(os.path.join(ref_dir, md_filename), "w", encoding="utf-8") as handle:
            handle.write(content)

        self._persist_extracted_artifacts(ref_dir, payload)
        self._upsert_identity_registry(payload)
        if rebuild_index:
            self._rebuild_index()
        self._append_log(log_event, payload)
        return ref_dir

    def _update_reference_metadata(
        self, reference_id: str, updates: Dict[str, Any], log_event: str
    ) -> str:
        metadata = self.get_metadata(reference_id)
        if not metadata:
            return f"Reference {reference_id} not found."

        metadata.update(updates)
        if not metadata.get("saved_at"):
            metadata["saved_at"] = __import__('datetime').datetime.now().isoformat()

        self._persist_reference_payload(metadata, log_event=log_event)
        return f"Updated {reference_id}."

    def compute_content_hash(self, file_path: str) -> str:
        """Compute a stable SHA256 hash for a local artifact."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @property
    def base_dir(self) -> str:
        """
        Get the current references directory.
        Uses project directory if a project is active, otherwise default.
        """
        if self._project_manager:
            try:
                paths = self._project_manager.get_project_paths()
                return paths.get("references", self._default_base_dir)
            except (ValueError, KeyError):
                pass
        return self._default_base_dir

    def save_reference(self, article: Dict[str, Any], download_pdf: bool = False) -> str:
        """
        Save a reference with provided article metadata.

        檔案結構 (2025-12 重構):
        ```
        references/
        └── {unique_id}/
            ├── {citation_key}.md   ← 主檔案，包含 YAML frontmatter + 內容
            └── metadata.json       ← 程式用完整 metadata
        ```

        支援來源：
        - PubMed (需要 pmid 欄位)
        - Zotero (需要 key 或 zotero_key 欄位)
        - DOI (需要 doi 或 DOI 欄位)

        Args:
            article: Article metadata dictionary from any source.
                     Must contain at least one identifier: pmid, zotero_key/key, or doi/DOI.
            download_pdf: Deprecated - PDF download handled externally.

        Returns:
            Status message with Foam citation key.
        """
        # Use domain converter to standardize format
        try:
            ref = self._converter.convert(article)
        except ValueError as e:
            return f"Error: {str(e)}"

        # Check if already exists
        ref_dir = os.path.join(self.base_dir, ref.unique_id)
        if os.path.exists(ref_dir):
            return f"Reference {ref.unique_id} already exists."

        # Add pre-formatted citation strings to metadata
        ref_dict = ref.to_dict()
        ref_dict["citation"] = self._format_citation(ref_dict)
        ref_dict["saved_at"] = __import__('datetime').datetime.now().isoformat()

        persisted_dir = self._persist_reference_payload(ref_dict, log_event="save_reference")

        # No need for separate alias file - aliases are in frontmatter
        # Foam will recognize [[citation_key]] via the filename and aliases

        foam_tip = f"\n💡 Foam: Use [[{ref.citation_key}]] to link this reference."
        source_info = f" (source: {ref.source})"
        return f"Successfully saved reference {ref.unique_id} to {persisted_dir}.{source_info}{foam_tip}"

    def import_local_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Import a local file into the canonical reference registry."""
        if not os.path.exists(file_path):
            return f"Error: Local file not found: {file_path}"

        content_hash = self.compute_content_hash(file_path)
        existing_ref_id = self._read_json_file(self._hash_registry_path(), {}).get(content_hash)
        if existing_ref_id and self.check_reference_exists(existing_ref_id):
            existing = self.get_metadata(existing_ref_id)
            citation_key = existing.get("citation_key", existing_ref_id)
            return (
                f"Local source already imported as {existing_ref_id}. "
                f"Foam link: [[{citation_key}]]"
            )

        source_metadata = dict(metadata or {})
        source_metadata.setdefault("imported_from", os.path.abspath(file_path))
        source_metadata.setdefault("content_hash", content_hash)
        source_metadata.setdefault("saved_at", __import__('datetime').datetime.now().isoformat())

        try:
            standardized = self._converter.convert(source_metadata)
            payload = standardized.to_dict()
        except ValueError:
            unique_id = f"local_{content_hash[:12]}"
            payload = {
                "unique_id": unique_id,
                "citation_key": self._build_citation_key(source_metadata, unique_id),
                "source": source_metadata.get("source", "manual"),
                "pmid": source_metadata.get("pmid"),
                "doi": source_metadata.get("doi") or source_metadata.get("DOI"),
                "title": source_metadata.get("title", Path(file_path).stem),
                "authors": source_metadata.get("authors", []),
                "authors_full": source_metadata.get("authors_full", []),
                "year": str(source_metadata.get("year", "")),
                "journal": source_metadata.get("journal", ""),
                "journal_abbrev": source_metadata.get("journal_abbrev", ""),
                "volume": source_metadata.get("volume", ""),
                "issue": source_metadata.get("issue", ""),
                "pages": source_metadata.get("pages", ""),
                "abstract": source_metadata.get("abstract", ""),
                "keywords": source_metadata.get("keywords", []),
                "mesh_terms": source_metadata.get("mesh_terms", []),
            }

        payload.update(source_metadata)
        payload.setdefault("data_source", source_metadata.get("data_source", "local_import"))
        payload.setdefault("provenance", [])
        payload["provenance"] = list(payload["provenance"]) + [
            {
                "event": "local_import",
                "source_path": os.path.abspath(file_path),
                "content_hash": content_hash,
                "data_source": payload.get("data_source", "local_import"),
            }
        ]
        if payload.get("asset_aware_doc_id") or payload.get("fulltext_sections"):
            payload["fulltext_ingested"] = True

        self._ensure_workspace_scaffolding()
        ref_dir = os.path.join(self.base_dir, payload["unique_id"])
        os.makedirs(ref_dir, exist_ok=True)
        payload["imported_from"] = self._copy_source_artifact(file_path, ref_dir)
        self._persist_reference_payload(payload, log_event="local_import")

        return (
            f"Successfully imported local source into {payload['unique_id']}. "
            f"Foam link: [[{payload['citation_key']}]]"
        )

    def _import_text_source(
        self,
        *,
        source_kind: str,
        locator: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        log_event: str,
    ) -> str:
        normalized_content = content.strip()
        if not normalized_content:
            return f"Error: Empty {source_kind} content."

        content_hash = self._compute_text_hash(normalized_content)
        existing_ref_id = self._read_json_file(self._hash_registry_path(), {}).get(content_hash)
        if existing_ref_id and self.check_reference_exists(existing_ref_id):
            existing = self.get_metadata(existing_ref_id)
            citation_key = existing.get("citation_key", existing_ref_id)
            return f"{source_kind.title()} source already imported as {existing_ref_id}. Foam link: [[{citation_key}]]"

        source_metadata = dict(metadata or {})
        fallback_title = Path(locator).stem if locator and source_kind == "markdown" else f"{source_kind.title()} source"
        title = source_metadata.get("title") or self._infer_markdown_title(
            normalized_content, fallback_title
        )
        headings = source_metadata.get("fulltext_sections") or self._extract_markdown_headings(
            normalized_content
        )
        abstract = source_metadata.get("abstract") or self._build_markdown_summary(normalized_content)

        payload = {
            "unique_id": source_metadata.get("unique_id") or f"{source_kind}_{content_hash[:12]}",
            "citation_key": source_metadata.get("citation_key"),
            "source": source_metadata.get("source", source_kind),
            "pmid": source_metadata.get("pmid"),
            "doi": source_metadata.get("doi") or source_metadata.get("DOI"),
            "title": title,
            "authors": source_metadata.get("authors", []),
            "authors_full": source_metadata.get("authors_full", []),
            "year": str(source_metadata.get("year", "")),
            "journal": source_metadata.get("journal", ""),
            "journal_abbrev": source_metadata.get("journal_abbrev", ""),
            "volume": source_metadata.get("volume", ""),
            "issue": source_metadata.get("issue", ""),
            "pages": source_metadata.get("pages", ""),
            "abstract": abstract,
            "keywords": source_metadata.get("keywords", []),
            "mesh_terms": source_metadata.get("mesh_terms", []),
        }

        payload.update(source_metadata)
        payload.setdefault("citation_key", self._build_citation_key(payload, payload["unique_id"]))
        payload["content_hash"] = content_hash
        payload["saved_at"] = payload.get("saved_at") or __import__('datetime').datetime.now().isoformat()
        payload["data_source"] = payload.get("data_source") or f"{source_kind}_intake"
        payload["fulltext_sections"] = headings
        payload["fulltext_ingested"] = True
        payload["extracted_markdown"] = normalized_content
        payload["trust_level"] = payload.get("trust_level", "user")
        payload["provenance"] = list(payload.get("provenance", [])) + [
            {
                "event": log_event,
                "source_locator": locator,
                "content_hash": content_hash,
                "data_source": payload["data_source"],
            }
        ]

        self._ensure_workspace_scaffolding()
        ref_dir = os.path.join(self.base_dir, payload["unique_id"])
        os.makedirs(ref_dir, exist_ok=True)
        file_name = "original.md" if source_kind == "markdown" else "captured.md"
        payload["imported_from"] = self._write_text_source_artifact(
            ref_dir, file_name, normalized_content
        )
        self._persist_reference_payload(payload, log_event=log_event)

        return (
            f"Successfully imported {source_kind} source into {payload['unique_id']}. "
            f"Foam link: [[{payload['citation_key']}]]"
        )

    def import_markdown_file(
        self, file_path: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Import a markdown file into the canonical reference registry."""
        if not os.path.exists(file_path):
            return f"Error: Markdown source not found: {file_path}"

        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except Exception as exc:
            return f"Error reading markdown source: {exc}"

        source_metadata = dict(metadata or {})
        source_metadata.setdefault("imported_from", os.path.abspath(file_path))
        return self._import_text_source(
            source_kind="markdown",
            locator=os.path.abspath(file_path),
            content=content,
            metadata=source_metadata,
            log_event="markdown_intake",
        )

    def import_markdown_content(
        self,
        markdown_text: str,
        *,
        source_name: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Import raw markdown text into the canonical reference registry."""
        source_metadata = dict(metadata or {})
        if source_name:
            source_metadata.setdefault("imported_from", source_name)
        return self._import_text_source(
            source_kind="markdown",
            locator=source_name,
            content=markdown_text,
            metadata=source_metadata,
            log_event="markdown_intake",
        )

    def import_web_source(
        self,
        url: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Import a fetched web page snapshot into the canonical reference registry."""
        if not url.strip():
            return "Error: Web source URL is required."

        source_metadata = dict(metadata or {})
        source_metadata.setdefault("url", url)
        source_metadata.setdefault("imported_from", url)
        return self._import_text_source(
            source_kind="web",
            locator=url,
            content=content,
            metadata=source_metadata,
            log_event="web_intake",
        )

    def build_knowledge_map(
        self,
        title: str,
        *,
        reference_ids: Optional[List[str]] = None,
        query: str = "",
        limit: int = 12,
    ) -> str:
        """Materialize a knowledge map note from selected references."""
        clean_title = title.strip() or "Knowledge Map"
        snapshots = self._resolve_reference_snapshots(reference_ids, query=query, limit=limit)
        if not snapshots:
            return "Error: No references available to build a knowledge map."

        body = self._build_knowledge_map_body(snapshots, query=query)
        page_path = self._write_materialized_page(
            page_type="knowledge_map",
            title=clean_title,
            query=query,
            focus="",
            reference_ids=[snapshot["reference_id"] for snapshot in snapshots],
            body=body,
            log_event="knowledge_map_materialized",
        )
        alias = self._materialized_page_alias("knowledge_map", self._slugify(clean_title))
        return f"Knowledge map materialized at {page_path}. Foam link: [[{alias}]]"

    def build_synthesis_page(
        self,
        title: str,
        *,
        reference_ids: Optional[List[str]] = None,
        query: str = "",
        focus: str = "",
        summary_markdown: str = "",
        limit: int = 12,
    ) -> str:
        """Materialize a synthesis note from selected references."""
        clean_title = title.strip() or "Synthesis Page"
        snapshots = self._resolve_reference_snapshots(reference_ids, query=query, limit=limit)
        if not snapshots:
            return "Error: No references available to build a synthesis page."

        body = self._build_synthesis_body(
            snapshots,
            focus=focus,
            summary_markdown=summary_markdown,
        )
        page_path = self._write_materialized_page(
            page_type="synthesis_page",
            title=clean_title,
            query=query,
            focus=focus,
            reference_ids=[snapshot["reference_id"] for snapshot in snapshots],
            body=body,
            log_event="synthesis_page_materialized",
        )
        alias = self._materialized_page_alias("synthesis_page", self._slugify(clean_title))
        return f"Synthesis page materialized at {page_path}. Foam link: [[{alias}]]"

    def materialize_agent_wiki(
        self,
        *,
        knowledge_map_title: str,
        synthesis_title: str = "",
        reference_ids: Optional[List[str]] = None,
        query: str = "",
        focus: str = "",
        summary_markdown: str = "",
        limit: int = 12,
    ) -> str:
        """Materialize the second-stage agent wiki bundle for a reference set."""
        clean_map_title = knowledge_map_title.strip() or "Knowledge Map"
        clean_synthesis_title = synthesis_title.strip() or f"{clean_map_title} synthesis"

        snapshots = self._resolve_reference_snapshots(reference_ids, query=query, limit=limit)
        if not snapshots:
            return "Error: No references available to materialize the agent wiki."

        selected_ids = [snapshot["reference_id"] for snapshot in snapshots]
        knowledge_map_result = self.build_knowledge_map(
            clean_map_title,
            reference_ids=selected_ids,
            query=query,
            limit=limit,
        )
        if knowledge_map_result.startswith("Error:"):
            return knowledge_map_result

        synthesis_result = self.build_synthesis_page(
            clean_synthesis_title,
            reference_ids=selected_ids,
            query=query,
            focus=focus,
            summary_markdown=summary_markdown,
            limit=limit,
        )
        if synthesis_result.startswith("Error:"):
            return synthesis_result

        knowledge_alias = self._materialized_page_alias(
            "knowledge_map", self._slugify(clean_map_title)
        )
        synthesis_alias = self._materialized_page_alias(
            "synthesis_page", self._slugify(clean_synthesis_title)
        )
        return (
            "Agent wiki materialized. "
            f"Knowledge map: [[{knowledge_alias}]]. "
            f"Synthesis page: [[{synthesis_alias}]]."
        )

    def resolve_reference_identity(
        self,
        reference_id: str,
        *,
        verified_article: Optional[Dict[str, Any]] = None,
        pmid: Optional[str] = None,
        agent_notes: str = "",
    ) -> str:
        """Upgrade a local/extracted reference into a canonical verified identity."""
        local_metadata = self.get_metadata(reference_id)
        if not local_metadata:
            return f"Reference {reference_id} not found."

        if verified_article is None and not pmid:
            return "Provide either verified_article metadata or a PMID."

        target_id: str
        if verified_article is not None:
            article = dict(verified_article)
            if agent_notes and not article.get("agent_notes"):
                article["agent_notes"] = agent_notes

            try:
                standardized = self._converter.convert(article)
            except ValueError as exc:
                return f"Error: {exc}"

            target_id = standardized.unique_id
            save_result = self.save_reference(article)
            if save_result.startswith("Error:"):
                return save_result
        else:
            target_id = str(pmid)
            save_result = self.save_reference_mcp(target_id, agent_notes=agent_notes)
            if save_result.startswith("❌") or save_result.startswith("⚠️"):
                return save_result

        canonical_metadata = self.get_metadata(target_id)
        if not canonical_metadata:
            return f"Failed to load canonical reference {target_id} after resolution."

        source_ref_dir = os.path.join(self.base_dir, reference_id)
        target_ref_dir = os.path.join(self.base_dir, target_id)
        merge_conflicts = self._merge_reference_artifacts(source_ref_dir, target_ref_dir)

        merged_provenance = list(canonical_metadata.get("provenance", []))
        merged_provenance.extend(local_metadata.get("provenance", []))
        resolution_event = {
            "event": "identity_resolved",
            "from_reference_id": reference_id,
            "to_reference_id": target_id,
            "resolved_via": "verified_metadata" if verified_article is not None else "pmid",
            "content_hash": local_metadata.get("content_hash", ""),
        }
        if merge_conflicts:
            resolution_event["artifact_conflicts"] = merge_conflicts
        merged_provenance.append(resolution_event)

        merged = dict(canonical_metadata)
        merged["provenance"] = self._dedupe_provenance(merged_provenance)

        for field_name in (
            "content_hash",
            "imported_from",
            "asset_aware_doc_id",
            "fulltext_unavailable_reason",
            "agent_notes",
            "user_notes",
        ):
            if local_metadata.get(field_name) and not merged.get(field_name):
                merged[field_name] = local_metadata[field_name]

        merged["fulltext_ingested"] = bool(
            merged.get("fulltext_ingested") or local_metadata.get("fulltext_ingested")
        )
        merged["analysis_completed"] = bool(
            merged.get("analysis_completed") or local_metadata.get("analysis_completed")
        )

        for list_field in ("fulltext_sections", "usage_sections", "user_tags"):
            merged_values = list(merged.get(list_field, []))
            for value in local_metadata.get(list_field, []):
                if value not in merged_values:
                    merged_values.append(value)
            merged[list_field] = merged_values

        legacy_aliases = list(canonical_metadata.get("legacy_aliases", []))
        legacy_aliases.extend(local_metadata.get("legacy_aliases", []))
        legacy_aliases.extend([local_metadata.get("citation_key", ""), reference_id])
        merged["legacy_aliases"] = [
            alias
            for alias in self._dedupe_strings(legacy_aliases)
            if alias not in {merged.get("citation_key", ""), target_id}
        ]

        if local_metadata.get("analysis_summary") and not merged.get("analysis_summary"):
            merged["analysis_summary"] = local_metadata["analysis_summary"]

        self._persist_reference_payload(
            merged,
            log_event="identity_resolution",
            rebuild_index=False,
        )

        if source_ref_dir != target_ref_dir and os.path.exists(source_ref_dir):
            self._remove_identity_registry_entries(reference_id, local_metadata)
            shutil.rmtree(source_ref_dir)

        self._rebuild_index()

        citation_key = merged.get("citation_key", target_id)
        return f"Resolved {reference_id} -> {target_id}. Foam link: [[{citation_key}]]"

    def update_fulltext_ingestion_status(
        self,
        reference_id: str,
        fulltext_ingested: bool,
        asset_aware_doc_id: Optional[str] = None,
        fulltext_sections: Optional[List[str]] = None,
        fulltext_unavailable_reason: str = "",
    ) -> str:
        """Centralized write path for fulltext ingestion metadata."""
        updates = {
            "fulltext_ingested": fulltext_ingested,
            "asset_aware_doc_id": asset_aware_doc_id,
            "fulltext_sections": fulltext_sections or [],
            "fulltext_unavailable_reason": fulltext_unavailable_reason,
        }
        if fulltext_ingested:
            updates["trust_level"] = "extracted"
        return self._update_reference_metadata(reference_id, updates, log_event="fulltext_status")

    def update_reference_analysis_status(
        self,
        reference_id: str,
        analysis_summary: str,
        usage_sections: Optional[List[str]] = None,
        analysis_completed: bool = True,
    ) -> str:
        """Centralized write path for analysis status metadata."""
        updates = {
            "analysis_completed": analysis_completed,
            "analysis_summary": analysis_summary,
            "usage_sections": usage_sections or [],
        }
        return self._update_reference_metadata(reference_id, updates, log_event="analysis_status")

    def save_reference_by_pmid(self, pmid: str) -> str:
        """
        [DEPRECATED] 舊版接口，保留向後相容。

        新的工作流程應該是:
        1. Agent 呼叫 pubmed-search MCP 的 fetch_article_details(pmid)
        2. Agent 呼叫 mdpaper MCP 的 save_reference(article_metadata)

        或者使用新的 MCP-to-MCP 方法:
        - save_reference_mcp(pmid, agent_notes) - 自動從 pubmed-search 取得驗證資料

        Returns:
            提示訊息，指引使用者使用新的工作流程。
        """
        return (
            f"❌ save_reference_by_pmid is deprecated.\n\n"
            f"New workflows:\n\n"
            f"Option A - Agent-mediated (current):\n"
            f"1. pubmed-search: fetch_article_details(pmid='{pmid}')\n"
            f"2. mdpaper: save_reference(article=<metadata>)\n\n"
            f"Option B - MCP-to-MCP direct (recommended):\n"
            f"1. mdpaper: save_reference_mcp(pmid='{pmid}', agent_notes='...')\n"
            f"   → mdpaper fetches verified data directly from pubmed-search"
        )

    def save_reference_mcp(
        self, pmid: str, agent_notes: str = "", fetch_if_missing: bool = True
    ) -> str:
        """
        Save reference using MCP-to-MCP direct communication.

        This is the NEW preferred method that ensures data integrity:
        1. Agent only passes PMID and optional notes
        2. mdpaper fetches verified metadata directly from pubmed-search HTTP API
        3. Prevents Agent from modifying/hallucinating bibliographic data

        Reference file structure (Layered Trust):
        ```
        ---
        # 🔒 VERIFIED (PubMed, immutable)
        source: pubmed
        pmid: "12345678"
        title: "Original Title from PubMed"
        ...

        # 🤖 AGENT (AI-generated)
        agent_notes: "Notes from AI assistant"

        # ✏️ USER (Human edits)
        user_tags: []
        user_notes: ""
        ---
        ```

        Args:
            pmid: PubMed ID (the ONLY required input from Agent)
            agent_notes: Optional notes from Agent about this reference
            fetch_if_missing: If True, fetch from PubMed if not in cache

        Returns:
            Status message with Foam citation key.
        """
        # Import here to avoid circular dependency
        from med_paper_assistant.infrastructure.services.pubmed_api_client import (
            get_pubmed_api_client,
        )

        # Get the API client
        client = get_pubmed_api_client(base_url=self._pubmed_api_url)

        # Check if pubmed-search API is available
        if not client.check_health():
            logger.warning(
                "[MCP-to-MCP] pubmed-search API not available, "
                "falling back to Agent-provided data requirement"
            )
            return (
                f"⚠️ pubmed-search MCP HTTP API is not available.\n"
                f"Please ensure pubmed-search is running with HTTP API enabled.\n\n"
                f"Alternative: Use the traditional workflow:\n"
                f"1. pubmed-search: fetch_article_details(pmid='{pmid}')\n"
                f"2. mdpaper: save_reference(article=<metadata>)"
            )

        # Fetch verified data directly from pubmed-search
        logger.info(f"[MCP-to-MCP] Fetching PMID:{pmid} from pubmed-search")
        article = client.get_cached_article(pmid, fetch_if_missing=fetch_if_missing)

        if not article:
            return (
                f"❌ Article PMID:{pmid} not found.\n\n"
                f"Please search for it first using pubmed-search MCP, then try again.\n"
                f"Example: search_literature(query='{pmid}[pmid]')"
            )

        # Add layered trust metadata
        article["_data_source"] = "pubmed_mcp_api"
        article["_verified"] = True
        article["_agent_notes"] = agent_notes
        article["_user_notes"] = ""  # Empty, for user to fill
        article["_user_tags"] = []  # Empty, for user to fill

        # Use existing save_reference with verified data
        return self.save_reference(article)

    def _generate_citation_key(self, article: Dict[str, Any]) -> str:
        """
        Generate a human-friendly citation key with PMID for verification.
        Format: 'smith2023_41285088' (author + year + underscore + PMID)

        Args:
            article: Article metadata dictionary.

        Returns:
            Citation key string like 'smith2023_41285088'.
        """
        authors_full = article.get("authors_full", [])
        authors = article.get("authors", [])
        year = article.get("year", "")
        pmid = article.get("pmid", "")

        # Get first author last name
        first_author = ""
        if authors_full and isinstance(authors_full[0], dict):
            first_author = authors_full[0].get("last_name", "").lower()
        elif authors:
            # Fallback: extract from string format "Last First"
            first_author = authors[0].split()[0].lower() if authors[0] else ""

        if not first_author:
            first_author = "unknown"

        # Clean up special characters
        import re

        first_author = re.sub(r"[^a-z]", "", first_author)

        # Format: author + year + underscore + PMID for easy verification
        return f"{first_author}{year}_{pmid}"

    def _create_foam_alias(self, pmid: str, citation_key: str):
        """
        Create a Foam-friendly alias file that redirects to the main content.
        This allows users to use [[smith2023_41285088]] for easy linking and verification.

        Args:
            pmid: PubMed ID.
            citation_key: Human-friendly citation key with PMID (e.g., 'smith2023_41285088').
        """
        alias_path = os.path.join(self.base_dir, f"{citation_key}.md")

        # Since citation_key now includes PMID, collisions are impossible
        # But still check just in case
        if os.path.exists(alias_path):
            return  # Already exists, no need to create

        # Create a redirect file that includes the content
        # This way Foam can preview it directly
        ref_dir = os.path.join(self.base_dir, pmid)
        content_path = os.path.join(ref_dir, "content.md")

        if os.path.exists(content_path):
            with open(content_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Add alias info to the top
            alias_content = f"<!-- Alias for PMID:{pmid} -->\n"
            alias_content += f"<!-- Verify: https://pubmed.ncbi.nlm.nih.gov/{pmid}/ -->\n\n"
            alias_content += content

            with open(alias_path, "w", encoding="utf-8") as f:
                f.write(alias_content)

    def _get_preferred_citation_style(self) -> Optional[str]:
        """
        Get the preferred citation style from project settings.

        Returns:
            Citation style string (e.g., 'apa', 'vancouver') or None if not set.
        """
        if self._project_manager:
            try:
                current_slug = self._project_manager.get_current_project()
                if current_slug:
                    project_info = self._project_manager.get_project_info(current_slug)
                    if project_info.get("success"):
                        settings = project_info.get("settings", {})
                        return settings.get("citation_style")
            except (ValueError, KeyError):
                pass
        return None

    def _format_citation(self, article: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate pre-formatted citation strings in multiple formats.

        Args:
            article: Article metadata dictionary.

        Returns:
            Dictionary with citation strings in different formats.
        """
        authors = article.get("authors", [])
        authors_full = article.get("authors_full", [])
        title = article.get("title", "Unknown Title").rstrip(".")
        journal = article.get("journal", "Unknown Journal")
        journal_abbrev = article.get("journal_abbrev", journal)
        year = article.get("year", "")
        volume = article.get("volume", "")
        issue = article.get("issue", "")
        pages = article.get("pages", "")
        doi = article.get("doi", "")
        pmid = article.get("pmid", "")

        # Format authors for different styles
        def format_vancouver_authors(auth_list, max_authors=6):
            if not auth_list:
                return "Unknown Author"

            formatted = []
            for i, author in enumerate(auth_list[:max_authors]):
                if isinstance(author, dict):
                    if "collective_name" in author:
                        formatted.append(author["collective_name"])
                    else:
                        last = author.get("last_name", "")
                        initials = author.get("initials", "")
                        formatted.append(f"{last} {initials}")
                else:
                    # Fallback for simple string format
                    parts = author.split()
                    if len(parts) >= 2:
                        formatted.append(f"{parts[0]} {''.join([p[0] for p in parts[1:]])}")
                    else:
                        formatted.append(author)

            result = ", ".join(formatted)
            if len(auth_list) > max_authors:
                result += ", et al"
            return result

        def format_apa_authors(auth_list, max_authors=7):
            if not auth_list:
                return "Unknown Author"

            formatted = []
            for author in auth_list[:max_authors]:
                if isinstance(author, dict):
                    if "collective_name" in author:
                        formatted.append(author["collective_name"])
                    else:
                        last = author.get("last_name", "")
                        initials = author.get("initials", "")
                        # APA: Last, F. M.
                        init_formatted = ". ".join(list(initials)) + "." if initials else ""
                        formatted.append(f"{last}, {init_formatted}")
                else:
                    parts = author.split()
                    if len(parts) >= 2:
                        init = ". ".join([p[0] for p in parts[1:]]) + "."
                        formatted.append(f"{parts[0]}, {init}")
                    else:
                        formatted.append(author)

            if len(formatted) == 1:
                result = formatted[0]
            elif len(formatted) == 2:
                result = f"{formatted[0]} & {formatted[1]}"
            else:
                result = ", ".join(formatted[:-1]) + f", & {formatted[-1]}"

            if len(auth_list) > max_authors:
                result = ", ".join(formatted[:6]) + ", ... " + formatted[-1]

            return result

        # Vancouver format
        vancouver_auth = format_vancouver_authors(authors_full or authors)
        vancouver = f"{vancouver_auth}. {title}. {journal_abbrev or journal}. {year}"
        if volume:
            vancouver += f";{volume}"
            if issue:
                vancouver += f"({issue})"
            if pages:
                vancouver += f":{pages}"
        vancouver += "."
        if doi:
            vancouver += f" doi:{doi}"

        # APA format
        apa_auth = format_apa_authors(authors_full or authors)
        apa = f"{apa_auth} ({year}). {title}. *{journal}*"
        if volume:
            apa += f", *{volume}*"
            if issue:
                apa += f"({issue})"
            if pages:
                apa += f", {pages}"
        apa += "."
        if doi:
            apa += f" https://doi.org/{doi}"

        # Nature/Science format
        nature_auth = format_vancouver_authors(authors_full or authors, max_authors=5)
        nature = (
            f"{nature_auth} {title}. *{journal_abbrev or journal}* **{volume}**, {pages} ({year})."
        )
        if doi:
            nature += f" https://doi.org/{doi}"

        # Simple format for in-text
        first_author = ""
        if authors_full:
            first_author = (
                authors_full[0].get("last_name", "")
                if isinstance(authors_full[0], dict)
                else authors[0].split()[0]
                if authors
                else ""
            )
        elif authors:
            first_author = authors[0].split()[0] if authors else ""

        if len(authors) == 1:
            in_text = f"{first_author}, {year}"
        elif len(authors) == 2:
            second_author = ""
            if authors_full and len(authors_full) > 1:
                second_author = (
                    authors_full[1].get("last_name", "")
                    if isinstance(authors_full[1], dict)
                    else authors[1].split()[0]
                )
            elif len(authors) > 1:
                second_author = authors[1].split()[0]
            in_text = f"{first_author} & {second_author}, {year}"
        else:
            in_text = f"{first_author} et al., {year}"

        return {
            "vancouver": vancouver,
            "apa": apa,
            "nature": nature,
            "in_text": in_text,
            "pmid": f"PMID: {pmid}",
            "doi": f"doi:{doi}" if doi else "",
        }

    def _generate_content_md(self, article: Dict[str, Any]) -> str:
        """
        Generate markdown content for the reference.
        Optimized for Foam hover preview - shows citation formats at the top.

        檔案結構重構 (2025-12):
        - aliases 放在 frontmatter 中，供 Foam 識別
        - citation formats 也放在 frontmatter
        - 人類可讀內容在 body

        Layered Trust Architecture (2025-01):
        ```
        ---
        # 🔒 VERIFIED (PubMed, immutable)
        source: pubmed
        verified: true
        ...

        # 🤖 AGENT (AI-generated, editable by AI)
        agent_notes: "..."

        # ✏️ USER (Human-only, never AI-touched)
        user_tags: []
        user_notes: ""
        ---
        ```

        Args:
            article: Article metadata dictionary.

        Returns:
            Markdown formatted content string.
        """
        pmid = article.get("pmid", "")
        unique_id = article.get("unique_id", pmid)
        title = article.get("title", "Unknown Title")
        citation_key = article.get("citation_key", "")

        # Check if this is MCP-to-MCP verified data
        is_verified = article.get("verified", article.get("_verified", False))
        data_source = article.get("data_source", article.get("_data_source", "agent"))
        trust_level = article.get("trust_level", "agent")
        agent_notes = article.get("agent_notes", article.get("_agent_notes", ""))
        user_notes = article.get("user_notes", article.get("_user_notes", ""))
        user_tags = article.get("user_tags", article.get("_user_tags", []))

        # YAML frontmatter for Foam (enables better linking)
        content = "---\n"

        # ========== 🔒 VERIFIED SECTION (from PubMed, immutable) ==========
        content += "# 🔒 VERIFIED DATA (from PubMed - do not modify)\n"
        content += f'source: "{article.get("source", "pubmed")}"\n'
        content += f"verified: {str(is_verified).lower()}\n"
        content += f'data_source: "{data_source}"\n\n'
        content += f'reference_id: "{unique_id}"\n'
        content += f'trust_level: "{trust_level}"\n'

        # Title for Foam completion label display
        content += f'title: "{title}"\n'

        # Aliases for Foam wikilinks - critical for [[citation_key]] to work
        content += "aliases:\n"
        if citation_key:
            content += f"  - {citation_key}\n"  # e.g., greer2017_27345583
        if unique_id:
            content += f'  - "{unique_id}"\n'
        if pmid:
            content += f'  - "PMID:{pmid}"\n'  # e.g., PMID:27345583
            content += f'  - "{pmid}"\n'  # e.g., 27345583
        if article.get("doi"):
            content += f'  - "DOI:{article["doi"]}"\n'
        for alias in article.get("legacy_aliases", []):
            escaped_alias = alias.replace('"', '\\"')
            content += f'  - "{escaped_alias}"\n'
        content += f'type: "{article.get("foam_type", "reference")}"\n'
        content += "tags:\n"
        for tag in article.get("tags", []):
            content += f'  - "{tag}"\n'
        content += "\n"
        content += f'note_class: "{article.get("note_class", article.get("foam_type", "reference"))}"\n'
        content += f'note_domain: "{article.get("note_domain", "literature")}"\n'
        if article.get("project"):
            content += f'project: "{article.get("project")}"\n'
        content += f'source_kind: "{article.get("source", "pubmed")}"\n'
        content += f'trust_state: "{trust_level}"\n'
        content += f'analysis_state: "{"completed" if article.get("analysis_completed", False) else "pending"}"\n'
        content += f'fulltext_state: "{"ingested" if article.get("fulltext_ingested", False) else "missing"}"\n'
        content += f'review_state: "{article.get("review_state", "n/a")}"\n'
        if article.get("journal_slug"):
            content += f'journal_slug: "{article.get("journal_slug")}"\n'

        # Bibliographic info
        content += f'pmid: "{pmid}"\n'
        content += f"year: {article.get('year', '')}\n"
        if article.get("doi"):
            content += f'doi: "{article["doi"]}"\n'
        if article.get("pmc_id"):
            content += f'pmc: "{article["pmc_id"]}"\n'
        if article.get("content_hash"):
            content += f'content_hash: "{article["content_hash"]}"\n'
        if article.get("imported_from"):
            content += f'imported_from: "{article["imported_from"].replace("\\", "\\\\")}"\n'

        # First author last name for easy referencing
        authors_full = article.get("authors_full", [])
        if authors_full and isinstance(authors_full[0], dict):
            first_author = authors_full[0].get("last_name", "")
            content += f'first_author: "{first_author}"\n'

        # Journal info
        content += f'\njournal: "{article.get("journal", "")}"\n'
        if article.get("volume"):
            content += f'volume: "{article.get("volume")}"\n'
        if article.get("issue"):
            content += f'issue: "{article.get("issue")}"\n'
        if article.get("pages"):
            content += f'pages: "{article.get("pages")}"\n'

        content += "\n# Ingestion status\n"
        content += f"fulltext_ingested: {str(article.get('fulltext_ingested', False)).lower()}\n"
        content += f'fulltext_unavailable_reason: "{article.get("fulltext_unavailable_reason", "")}"\n'
        if article.get("asset_aware_doc_id"):
            content += f'asset_aware_doc_id: "{article.get("asset_aware_doc_id")}"\n'
        if article.get("fulltext_sections"):
            content += "fulltext_sections:\n"
            for section in article.get("fulltext_sections", []):
                content += f'  - "{section}"\n'
        else:
            content += "fulltext_sections: []\n"

        content += "\n# Analysis status\n"
        content += f"analysis_completed: {str(article.get('analysis_completed', False)).lower()}\n"
        content += f'analysis_summary: "{article.get("analysis_summary", "").replace("\"", "\\\"")}"\n'
        if article.get("usage_sections"):
            content += "usage_sections:\n"
            for section in article.get("usage_sections", []):
                content += f'  - "{section}"\n'
        else:
            content += "usage_sections: []\n"
        content += f"note_materialized: {str(article.get('note_materialized', True)).lower()}\n"

        # Pre-formatted citations in frontmatter (easy to copy)
        citation = article.get("citation", {})
        if citation:
            content += "\n# Pre-formatted citations\n"
            content += "cite:\n"
            if citation.get("vancouver"):
                # Escape quotes in citation
                vancouver = citation["vancouver"].replace('"', '\\"')
                content += f'  vancouver: "{vancouver}"\n'
            if citation.get("apa"):
                apa = citation["apa"].replace('"', '\\"')
                content += f'  apa: "{apa}"\n'
            if citation.get("nature"):
                nature = citation["nature"].replace('"', '\\"')
                content += f'  nature: "{nature}"\n'
            if citation.get("in_text"):
                content += f'  inline: "{citation["in_text"]}"\n'
            content += "  number: null  # Assigned during export\n"

        # ========== 🤖 AGENT SECTION (AI-generated, can be updated by AI) ==========
        content += "\n# 🤖 AGENT DATA (AI-generated, AI can update)\n"
        content += f'agent_notes: "{agent_notes.replace("\"", "\\\"")}"\n'
        content += 'agent_summary: ""\n'  # Can be filled by AI summarization
        content += "agent_relevance: null\n"  # 1-5 relevance score

        # ========== ✏️ USER SECTION (Human-only, never touched by AI) ==========
        content += "\n# ✏️ USER DATA (human-only, AI should never modify)\n"
        content += f'user_notes: "{user_notes.replace("\"", "\\\"")}"\n'
        if user_tags:
            content += "user_tags:\n"
            for tag in user_tags:
                content += f'  - "{tag}"\n'
        else:
            content += "user_tags: []\n"
        content += "user_rating: null  # 1-5 personal rating\n"
        content += "user_read_status: unread  # unread, reading, read\n"

        # Metadata
        saved_at = article.get("saved_at") or __import__('datetime').datetime.now().isoformat()
        content += f'\nsaved_at: "{saved_at}"\n'
        content += "---\n\n"

        content += f"# {title}\n\n"

        # Authors
        authors = article.get("authors", [])
        content += f"**Authors**: {', '.join(authors)}\n\n"

        # Journal info
        journal = article.get("journal", "Unknown Journal")
        year = article.get("year", "")
        volume = article.get("volume", "")
        issue = article.get("issue", "")
        pages = article.get("pages", "")

        journal_info = f"{journal}"
        if year:
            journal_info += f" ({year})"
        if volume:
            journal_info += f"; {volume}"
            if issue:
                journal_info += f"({issue})"
            if pages:
                journal_info += f": {pages}"
        content += f"**Journal**: {journal_info}\n\n"

        # IDs
        content += f"**Reference ID**: {unique_id}\n"
        content += f"**PMID**: {pmid}\n"
        if article.get("doi"):
            content += f"**DOI**: [{article['doi']}](https://doi.org/{article['doi']})\n"
        if article.get("pmc_id"):
            content += f"**PMC**: {article['pmc_id']}\n"
        if article.get("content_hash"):
            content += f"**Content Hash**: {article['content_hash']}\n"
        content += "\n"

        graph_context = self._build_reference_graph_context(article)
        if graph_context:
            content += "## Graph Context\n\n"
            content += graph_context
            content += "\n\n"

        # Abstract FIRST - most useful for Foam hover preview!
        abstract = article.get("abstract", "")
        if abstract:
            content += "## Abstract\n\n"
            content += abstract
            content += "\n\n"

        key_findings = (
            article.get("analysis_summary")
            or abstract
            or self._build_markdown_summary(article.get("extracted_markdown", ""), max_chars=320)
        ).strip()
        if key_findings:
            content += "## Key Findings\n\n"
            content += key_findings.replace("\n", " ")
            content += "\n\n"
            content += self._key_findings_anchor() + "\n\n"

        evidence_blocks = self._build_evidence_block_specs(article)
        if evidence_blocks:
            content += "## Evidence Blocks\n\n"
            for block in evidence_blocks:
                content += f"### {block['title']}\n\n"
                if block["content"]:
                    content += block["content"] + "\n\n"
                else:
                    content += "Section indexed from extracted fulltext.\n\n"
                content += self._evidence_anchor(block["title"]) + "\n\n"

        # Keywords
        keywords = article.get("keywords", [])
        if keywords:
            content += f"**Keywords**: {', '.join(keywords)}\n\n"

        # MeSH terms
        mesh_terms = article.get("mesh_terms", [])
        if mesh_terms:
            content += f"**MeSH Terms**: {', '.join(mesh_terms[:10])}"
            if len(mesh_terms) > 10:
                content += f" (+{len(mesh_terms) - 10} more)"
            content += "\n\n"

        # Citation formats (moved to bottom - less useful in hover)
        citation = article.get("citation", {})
        if citation:
            preferred_style = self._get_preferred_citation_style()
            content += "## 📋 Citation Formats\n\n"

            # Style order: preferred first, then others
            style_order = ["vancouver", "apa", "nature"]
            if preferred_style and preferred_style in style_order:
                style_order.remove(preferred_style)
                style_order.insert(0, preferred_style)

            style_labels = {
                "vancouver": "Vancouver",
                "apa": "APA",
                "nature": "Nature",
                "harvard": "Harvard",
                "ama": "AMA",
            }

            for style in style_order:
                if citation.get(style):
                    label = style_labels.get(style, style.title())
                    if style == preferred_style:
                        content += f"**⭐ {label}**: {citation[style]}\n\n"
                    else:
                        content += f"**{label}**: {citation[style]}\n\n"

            if citation.get("in_text"):
                content += f"**In-text**: ({citation['in_text']})\n\n"

        return content

    def list_references(self) -> List[str]:
        """
        List all saved references.

        Returns:
            List of PMIDs.
        """
        if not os.path.exists(self.base_dir):
            return []
        return [
            d for d in os.listdir(self.base_dir) if os.path.isdir(os.path.join(self.base_dir, d))
        ]

    def get_metadata(self, pmid: str) -> Dict[str, Any]:
        """
        Get metadata for a locally saved reference.

        Args:
            pmid: PubMed ID.

        Returns:
            Dictionary containing metadata, or empty dict if not found locally.
        """
        ref_dir = os.path.join(self.base_dir, pmid)
        metadata_path = os.path.join(ref_dir, "metadata.json")

        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading metadata for {pmid}: {e}")
                return {}

        # Reference not found locally
        return {}

    def get_reference_details(self, pmid: str) -> Dict[str, Any]:
        """
        Get local reference details for downstream analysis workflows.

        Args:
            pmid: PubMed ID.

        Returns:
            Dict with metadata, reference directory, and optional analysis data.
            Returns empty dict if the reference does not exist locally.
        """
        metadata = self.get_metadata(pmid)
        if not metadata:
            return {}

        ref_dir = os.path.join(self.base_dir, pmid)
        detail: Dict[str, Any] = {
            "pmid": pmid,
            "metadata": metadata,
            "ref_dir": ref_dir,
            "has_fulltext_pdf": self.has_fulltext(pmid),
        }

        analysis_path = os.path.join(ref_dir, "analysis.json")
        if os.path.exists(analysis_path):
            try:
                with open(analysis_path, "r", encoding="utf-8") as f:
                    detail["analysis"] = json.load(f)
            except Exception as e:
                detail["analysis_error"] = str(e)

        return detail

    def search_local(self, query: str) -> List[Dict[str, Any]]:
        """
        Search within saved local references by keyword.

        Args:
            query: Keyword to search in titles and abstracts.

        Returns:
            List of matching metadata dictionaries.
        """
        results = []
        query = query.lower()

        for pmid in self.list_references():
            meta = self.get_metadata(pmid)
            if not meta:
                continue

            title = meta.get("title", "").lower()
            abstract = meta.get("abstract", "").lower()

            if query in title or query in abstract:
                results.append(meta)

        return results

    def check_reference_exists(self, pmid: str) -> bool:
        """
        Check if a reference is already saved locally.

        Args:
            pmid: PubMed ID.

        Returns:
            True if reference exists locally.
        """
        ref_dir = os.path.join(self.base_dir, pmid)
        return os.path.exists(ref_dir)

    def has_fulltext(self, pmid: str) -> bool:
        """
        Check if a reference has a downloaded PDF fulltext.

        Args:
            pmid: PubMed ID.

        Returns:
            True if fulltext PDF exists.
        """
        metadata = self.get_metadata(pmid)
        if metadata.get("fulltext_ingested"):
            return True

        pdf_path = os.path.join(self.base_dir, pmid, "fulltext.pdf")
        return os.path.exists(pdf_path)

    def get_fulltext_path(self, pmid: str) -> Optional[str]:
        """
        Get the path to the fulltext PDF if it exists.

        Args:
            pmid: PubMed ID.

        Returns:
            Path to PDF file, or None if not available.
        """
        pdf_path = os.path.join(self.base_dir, pmid, "fulltext.pdf")
        if os.path.exists(pdf_path):
            return pdf_path
        return None

    def read_fulltext(self, pmid: str) -> Optional[str]:
        """
        Read and extract text from fulltext PDF.

        Args:
            pmid: PubMed ID.

        Returns:
            Extracted text from PDF, or None if not available.
        """
        pdf_path = self.get_fulltext_path(pmid)
        if not pdf_path:
            return None

        try:
            import pypdf

            reader = pypdf.PdfReader(pdf_path)
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text())

            return "\n\n".join(text_parts)
        except ImportError:
            return "Error: pypdf library not installed. Install with: uv add pypdf"
        except Exception as e:
            return f"Error reading PDF: {str(e)}"

    def get_reference_summary(self, pmid: str) -> Dict[str, Any]:
        """
        Get a comprehensive summary of a reference including availability info.

        Args:
            pmid: PubMed ID.

        Returns:
            Dictionary with metadata and availability information.
        """
        meta = self.get_metadata(pmid)
        if not meta:
            return {"error": f"Reference {pmid} not found"}

        summary = {
            "pmid": pmid,
            "citation_key": meta.get("citation_key", pmid),
            "title": meta.get("title", ""),
            "authors": meta.get("authors", []),
            "journal": meta.get("journal", ""),
            "year": meta.get("year", ""),
            "doi": meta.get("doi", ""),
            "has_abstract": bool(meta.get("abstract")),
            "has_fulltext_pdf": self.has_fulltext(pmid),
            "citation": meta.get("citation", {}),
            "trust_level": meta.get("trust_level", ""),
            "note_materialized": meta.get("note_materialized", False),
        }

        return summary

    def save_pdf(self, pmid: str, pdf_content: bytes) -> str:
        """
        Save PDF content for a reference.

        Args:
            pmid: PubMed ID.
            pdf_content: PDF file content as bytes.

        Returns:
            Status message.
        """
        ref_dir = os.path.join(self.base_dir, pmid)
        if not os.path.exists(ref_dir):
            return f"Reference {pmid} not found. Save metadata first."

        pdf_path = os.path.join(ref_dir, "fulltext.pdf")
        if os.path.exists(pdf_path):
            return f"PDF already exists for {pmid}."

        try:
            with open(pdf_path, "wb") as f:
                f.write(pdf_content)
            self._update_reference_metadata(pmid, {"has_pdf": True}, log_event="save_pdf")
            return f"Successfully saved PDF for {pmid}."
        except Exception as e:
            return f"Error saving PDF for {pmid}: {str(e)}"

    def delete_reference(self, pmid: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete a saved reference and all associated files.

        Args:
            pmid: PubMed ID of the reference to delete.
            confirm: Must be True to actually delete.

        Returns:
            Dict with success status and deleted files info.
        """
        import shutil

        ref_dir = os.path.join(self.base_dir, pmid)

        if not os.path.exists(ref_dir):
            return {
                "success": False,
                "error": f"Reference {pmid} not found in local library.",
            }

        # Get reference info before deletion for confirmation
        summary = self.get_reference_summary(pmid)
        title = summary.get("title", "Unknown title")
        citation_key = summary.get("citation_key", f"pmid_{pmid}")

        if not confirm:
            # Return preview without deleting
            files_to_delete = []
            for root, dirs, files in os.walk(ref_dir):
                for f in files:
                    rel_path = os.path.relpath(os.path.join(root, f), ref_dir)
                    files_to_delete.append(rel_path)

            return {
                "success": False,
                "requires_confirmation": True,
                "pmid": pmid,
                "title": title,
                "citation_key": citation_key,
                "files_to_delete": files_to_delete,
                "message": f"⚠️ 即將刪除 PMID {pmid}。請確認後使用 confirm=True 執行刪除。",
            }

        # Actually delete
        try:
            deleted_files = []
            for root, dirs, files in os.walk(ref_dir):
                for f in files:
                    rel_path = os.path.relpath(os.path.join(root, f), ref_dir)
                    deleted_files.append(rel_path)

            metadata = self.get_metadata(pmid)
            self._remove_identity_registry_entries(pmid, metadata)
            shutil.rmtree(ref_dir)
            self._rebuild_index()
            if metadata:
                self._append_log("delete_reference", metadata)

            return {
                "success": True,
                "pmid": pmid,
                "title": title,
                "citation_key": citation_key,
                "deleted_files": deleted_files,
                "message": f"✅ 已刪除 PMID {pmid}: {title}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"刪除失敗: {str(e)}",
                "pmid": pmid,
            }
