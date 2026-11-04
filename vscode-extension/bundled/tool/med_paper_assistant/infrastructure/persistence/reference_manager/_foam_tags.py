"""Foam tag and note-type derivation."""

from typing import Any, Dict, List, Optional


class FoamTagMixin:
    """Foam tag and note-type derivation."""

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
        candidates = self._reference_identity_tag_candidates(payload)
        candidates.extend(self._reference_topic_tag_candidates(payload))

        deduped: List[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = self._normalize_foam_tag(candidate)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)

        return deduped

    def _reference_identity_tag_candidates(self, payload: Dict[str, Any]) -> List[str]:
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
        return candidates

    def _reference_topic_tag_candidates(self, payload: Dict[str, Any]) -> List[str]:
        candidates: List[str] = []
        for usage_section in self._dedupe_strings(payload.get("usage_sections", []))[:6]:
            candidates.append(f"usage/{usage_section}")

        for fulltext_section in self._dedupe_strings(payload.get("fulltext_sections", []))[:6]:
            candidates.append(f"section/{fulltext_section}")

        for keyword in self._dedupe_strings(payload.get("keywords", []))[:8]:
            candidates.append(f"topic/{keyword}")

        for mesh_term in self._dedupe_strings(payload.get("mesh_terms", []))[:8]:
            candidates.append(f"mesh/{mesh_term}")

        publication_types = (
            payload.get("publication_types") or payload.get("publication_type") or []
        )
        for publication_type in self._dedupe_strings(publication_types)[:4]:
            candidates.append(f"study/{publication_type}")

        candidates.extend(self._dedupe_strings(payload.get("tags", [])))
        candidates.extend(self._dedupe_strings(payload.get("user_tags", [])))
        return candidates

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
