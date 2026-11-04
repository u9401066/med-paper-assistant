"""Read, write, update and delete reference metadata on disk."""

import json
import os
from typing import Any, Dict, List, Optional

import structlog

from med_paper_assistant.infrastructure.persistence.reference_dirs import list_reference_ids
from med_paper_assistant.shared.path_guard import (
    PathGuardError,
)

logger = structlog.get_logger()


class MetadataStoreMixin:
    """Read, write, update and delete reference metadata on disk."""

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

    def _persist_reference_payload(
        self,
        payload: Dict[str, Any],
        log_event: str,
        *,
        rebuild_index: bool = True,
    ) -> str:
        self._ensure_workspace_scaffolding()
        payload = self._normalize_reference_payload(payload)
        ref_dir = self._reference_dir(payload["unique_id"])
        os.makedirs(ref_dir, exist_ok=True)

        # Extraction persistence can add a receipt hash to metadata, so it must
        # run before metadata.json is serialized.
        self._persist_extracted_artifacts(ref_dir, payload)
        self._write_json_file(os.path.join(ref_dir, "metadata.json"), payload)
        if payload.get("provenance"):
            self._write_json_file(os.path.join(ref_dir, "provenance.json"), payload["provenance"])

        content = self._generate_content_md(payload)
        md_filename = self._citation_note_filename(payload["citation_key"])
        with open(os.path.join(ref_dir, md_filename), "w", encoding="utf-8") as handle:
            handle.write(content)

        self._upsert_identity_registry(payload)
        if rebuild_index:
            self._rebuild_index()
        self._append_log(log_event, payload)
        return str(ref_dir)

    def _update_reference_metadata(
        self, reference_id: str, updates: Dict[str, Any], log_event: str
    ) -> str:
        metadata = self.get_metadata(reference_id)
        if not metadata:
            return f"Reference {reference_id} not found."

        # Older workspaces may predate the multi-source ``unique_id`` field.
        # The update path already knows the canonical directory identifier, so
        # migrate it before the centralized persistence pipeline requires it.
        metadata["unique_id"] = metadata.get("unique_id") or reference_id
        metadata.update(updates)
        if not metadata.get("saved_at"):
            metadata["saved_at"] = __import__("datetime").datetime.now().isoformat()

        self._persist_reference_payload(metadata, log_event=log_event)
        return f"Updated {reference_id}."

    def list_references(self) -> List[str]:
        """
        List all saved references.

        Returns:
            List of PMIDs.
        """
        return list_reference_ids(str(self.base_dir))

    def get_metadata(self, pmid: str) -> Dict[str, Any]:
        """
        Get metadata for a locally saved reference.

        Args:
            pmid: PubMed ID.

        Returns:
            Dictionary containing metadata, or empty dict if not found locally.
        """
        try:
            ref_dir = self._reference_dir(pmid)
        except (PathGuardError, ValueError):
            return {}
        metadata_path = os.path.join(ref_dir, "metadata.json")

        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("reference_metadata_unreadable", pmid=pmid, error=str(e))
                return {}

        # Reference not found locally
        return {}

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
        analysis_receipt: Optional[Dict[str, str]] = None,
    ) -> str:
        """Centralized write path for analysis status metadata."""
        updates = {
            "analysis_completed": analysis_completed,
            "analysis_summary": analysis_summary,
            "usage_sections": usage_sections or [],
        }
        for key in (
            "analysis_artifact_sha256",
            "analysis_source_tool",
            "analysis_completed_at",
            "analysis_source_revision_sha256",
        ):
            value = (analysis_receipt or {}).get(key, "")
            if value:
                updates[key] = value
        return self._update_reference_metadata(reference_id, updates, log_event="analysis_status")
