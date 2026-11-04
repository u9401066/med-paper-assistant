"""Normalise reference metadata so metadata.json and the Foam note stay in sync."""

from typing import Any, Dict

from med_paper_assistant.domain.entities.reference import has_verified_pubmed_provenance


class PayloadNormalizerMixin:
    """Normalise reference payloads before they are persisted."""

    def _normalize_reference_payload(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize metadata so metadata.json and Foam note stay in sync."""
        payload = dict(article)
        self._normalize_citation_fields(payload)
        verified = self._normalize_verification_fields(payload)
        self._normalize_note_and_fulltext_fields(payload)
        self._normalize_identifier_fields(payload)
        self._assign_trust_level(payload, verified)
        self._assign_foam_fields(payload)
        return payload

    def _normalize_citation_fields(self, payload: Dict[str, Any]) -> None:
        citation = payload.get("citation") or payload.get("citations")
        if not citation:
            citation = self._format_citation(payload)
        payload["citation"] = citation

        payload["provenance"] = self._dedupe_provenance(payload.get("provenance", []))
        payload["data_source"] = (
            payload.get("data_source")
            or payload.get("_data_source")
            or payload.get("source", "agent")
        )
        payload["retrieved_at"] = str(payload.get("retrieved_at") or "")
        payload["source_url"] = str(payload.get("source_url") or "")
        payload["payload_hash"] = str(payload.get("payload_hash") or "")

    def _normalize_verification_fields(self, payload: Dict[str, Any]) -> bool:
        # Legacy ``_verified`` is read only to downgrade old data safely; it
        # cannot establish trust without the complete canonical provenance.
        payload["verified"] = payload.get(
            "verified",
            payload.get("_verified", False),
        )
        verified = has_verified_pubmed_provenance(payload)
        payload["verified"] = verified
        return verified

    def _normalize_note_and_fulltext_fields(self, payload: Dict[str, Any]) -> None:
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
        saved_at = payload.get("saved_at")
        isoformat = getattr(saved_at, "isoformat", None)
        if callable(isoformat):
            payload["saved_at"] = isoformat()

    def _normalize_identifier_fields(self, payload: Dict[str, Any]) -> None:
        if not payload.get("citation_key") and payload.get("unique_id"):
            payload["citation_key"] = self._build_citation_key(payload, payload["unique_id"])
        if payload.get("unique_id"):
            payload["unique_id"] = self._normalize_reference_id(payload["unique_id"])
        if payload.get("citation_key"):
            payload["citation_key"] = self._normalize_citation_key(payload["citation_key"])

    def _assign_trust_level(self, payload: Dict[str, Any], verified: bool) -> None:
        if verified:
            payload["trust_level"] = "verified"
        elif payload.get("trust_level") in {None, "", "verified"}:
            if payload.get("asset_aware_doc_id") or payload.get("fulltext_sections"):
                payload["trust_level"] = "extracted"
            elif payload.get("source") in {"manual", "local", "web", "markdown"}:
                payload["trust_level"] = "user"
            else:
                payload["trust_level"] = "agent"

    def _assign_foam_fields(self, payload: Dict[str, Any]) -> None:
        payload["foam_type"] = payload.get("foam_type") or "reference"
        payload["note_class"] = payload.get("note_class") or payload["foam_type"]
        payload["note_domain"] = payload.get("note_domain") or "literature"
        payload["project"] = payload.get("project") or self._current_project_slug()
        payload["first_author"] = payload.get("first_author") or self._extract_first_author_slug(
            payload
        )
        payload["journal_slug"] = payload.get("journal_slug") or self._slugify(
            payload.get("journal") or payload.get("journal_abbrev") or "", fallback=""
        )
        payload["analysis_state"] = "completed" if payload.get("analysis_completed") else "pending"
        payload["fulltext_state"] = "ingested" if payload.get("fulltext_ingested") else "missing"
        payload["review_state"] = payload.get("review_state") or "n/a"
        payload["tags"] = self._build_reference_tags(payload)
