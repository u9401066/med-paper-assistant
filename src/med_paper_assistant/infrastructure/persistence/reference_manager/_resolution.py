"""Upgrade local/extracted references into canonical verified identities."""

import os
import shutil
from typing import Any, Dict, List, Optional, Tuple

from med_paper_assistant.shared.path_guard import PathGuardError


class IdentityResolutionMixin:
    """Resolve a local reference into its canonical verified identity."""

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

        target_id, error = self._save_canonical_identity(verified_article, pmid, agent_notes)
        if error:
            return error

        canonical_metadata = self.get_metadata(target_id)
        if not canonical_metadata:
            return f"Failed to load canonical reference {target_id} after resolution."

        try:
            source_ref_dir = self._reference_dir(reference_id)
            target_ref_dir = self._reference_dir(target_id)
        except (PathGuardError, ValueError) as exc:
            return f"Invalid reference id during resolution: {exc}"
        merge_conflicts = self._merge_reference_artifacts(source_ref_dir, target_ref_dir)

        merged = self._persist_merged_identity(
            canonical_metadata,
            local_metadata,
            reference_id=reference_id,
            target_id=target_id,
            resolved_via="verified_metadata" if verified_article is not None else "pmid",
            merge_conflicts=merge_conflicts,
        )

        self._finish_identity_resolution(
            reference_id, local_metadata, source_ref_dir, target_ref_dir
        )

        citation_key = merged.get("citation_key", target_id)
        return f"Resolved {reference_id} -> {target_id}. Foam link: [[{citation_key}]]"

    def _persist_merged_identity(
        self,
        canonical_metadata: Dict[str, Any],
        local_metadata: Dict[str, Any],
        *,
        reference_id: str,
        target_id: str,
        resolved_via: str,
        merge_conflicts: List[Any],
    ) -> Dict[str, Any]:
        merged = self._merge_identity_metadata(
            canonical_metadata,
            local_metadata,
            reference_id=reference_id,
            target_id=target_id,
            resolved_via=resolved_via,
            merge_conflicts=merge_conflicts,
        )
        self._persist_reference_payload(
            merged,
            log_event="identity_resolution",
            rebuild_index=False,
        )
        return merged

    def _finish_identity_resolution(
        self,
        reference_id: str,
        local_metadata: Dict[str, Any],
        source_ref_dir: Any,
        target_ref_dir: Any,
    ) -> None:
        if source_ref_dir != target_ref_dir and os.path.exists(source_ref_dir):
            self._remove_identity_registry_entries(reference_id, local_metadata)
            shutil.rmtree(source_ref_dir)

        self._rebuild_index()

    def _save_canonical_identity(
        self,
        verified_article: Optional[Dict[str, Any]],
        pmid: Optional[str],
        agent_notes: str,
    ) -> Tuple[str, str]:
        """Save the canonical reference; returns ``(target_id, error_message)``."""
        target_id: str
        if verified_article is not None:
            article = dict(verified_article)
            if agent_notes and not article.get("agent_notes"):
                article["agent_notes"] = agent_notes

            try:
                standardized = self._converter.convert(article)
            except ValueError as exc:
                return "", f"Error: {exc}"

            target_id = standardized.unique_id
            save_result = self.save_reference(article)
            if save_result.startswith("Error:"):
                return target_id, save_result
        else:
            target_id = str(pmid)
            save_result = self.save_reference_mcp(target_id, agent_notes=agent_notes)
            if save_result.startswith("❌") or save_result.startswith("⚠️"):
                return target_id, save_result
        return target_id, ""

    def _merge_identity_metadata(
        self,
        canonical_metadata: Dict[str, Any],
        local_metadata: Dict[str, Any],
        *,
        reference_id: str,
        target_id: str,
        resolved_via: str,
        merge_conflicts: List[Any],
    ) -> Dict[str, Any]:
        merged_provenance = list(canonical_metadata.get("provenance", []))
        merged_provenance.extend(local_metadata.get("provenance", []))
        resolution_event = {
            "event": "identity_resolved",
            "from_reference_id": reference_id,
            "to_reference_id": target_id,
            "resolved_via": resolved_via,
            "content_hash": local_metadata.get("content_hash", ""),
        }
        if merge_conflicts:
            resolution_event["artifact_conflicts"] = merge_conflicts
        merged_provenance.append(resolution_event)

        merged = dict(canonical_metadata)
        merged["provenance"] = self._dedupe_provenance(merged_provenance)
        self._merge_local_identity_fields(merged, local_metadata)
        self._merge_legacy_aliases(
            merged,
            canonical_metadata,
            local_metadata,
            reference_id=reference_id,
            target_id=target_id,
        )

        if local_metadata.get("analysis_summary") and not merged.get("analysis_summary"):
            merged["analysis_summary"] = local_metadata["analysis_summary"]
        return merged

    def _merge_local_identity_fields(
        self, merged: Dict[str, Any], local_metadata: Dict[str, Any]
    ) -> None:
        for field_name in (
            "content_hash",
            "imported_from",
            "asset_aware_doc_id",
            "fulltext_receipt_sha256",
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

    def _merge_legacy_aliases(
        self,
        merged: Dict[str, Any],
        canonical_metadata: Dict[str, Any],
        local_metadata: Dict[str, Any],
        *,
        reference_id: str,
        target_id: str,
    ) -> None:
        legacy_aliases = list(canonical_metadata.get("legacy_aliases", []))
        legacy_aliases.extend(local_metadata.get("legacy_aliases", []))
        legacy_aliases.extend([local_metadata.get("citation_key", ""), reference_id])
        merged["legacy_aliases"] = [
            alias
            for alias in self._dedupe_strings(legacy_aliases)
            if alias not in {merged.get("citation_key", ""), target_id}
        ]
