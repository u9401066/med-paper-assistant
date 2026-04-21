import json
import os
import hashlib
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
        ]
        if query:
            candidates.append("query-backed")
        if focus:
            candidates.append("focus-driven")

        deduped: List[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = self._normalize_foam_tag(candidate)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)

        return deduped

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

    def _rebuild_index(self) -> None:
        index_path = os.path.join(self._notes_dir(), "index.md")
        lines = ["# Knowledge Base Index", "", "## References", ""]

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

        with open(index_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

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
        artifact_dir = os.path.join(ref_dir, "artifacts", "asset-aware")

        if extracted_markdown or manifest:
            os.makedirs(artifact_dir, exist_ok=True)

        if extracted_markdown:
            with open(os.path.join(artifact_dir, "sections.md"), "w", encoding="utf-8") as handle:
                handle.write(extracted_markdown)

        if manifest:
            self._write_json_file(os.path.join(artifact_dir, "manifest.json"), manifest)

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
