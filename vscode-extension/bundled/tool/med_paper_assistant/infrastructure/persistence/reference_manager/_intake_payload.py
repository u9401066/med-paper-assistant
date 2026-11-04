"""Payload builders shared by the local-file and text-source intake paths."""

import os
from pathlib import Path
from typing import Any, Dict, Optional


class IntakePayloadMixin:
    """Build reference payloads for locally imported sources."""

    def _already_imported_message(self, content_hash: str, label: str) -> Optional[str]:
        existing_ref_id = self._read_json_file(self._hash_registry_path(), {}).get(content_hash)
        if existing_ref_id and self.check_reference_exists(existing_ref_id):
            existing = self.get_metadata(existing_ref_id)
            citation_key = existing.get("citation_key", existing_ref_id)
            return f"{label} source already imported as {existing_ref_id}. Foam link: [[{citation_key}]]"
        return None

    def _source_payload_base(
        self,
        source_metadata: Dict[str, Any],
        *,
        unique_id: str,
        citation_key: Optional[str],
        source: str,
        title: str,
        abstract: str,
    ) -> Dict[str, Any]:
        return {
            "unique_id": unique_id,
            "citation_key": citation_key,
            "source": source,
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

    def _build_local_import_payload(
        self, file_path: str, source_metadata: Dict[str, Any], content_hash: str
    ) -> Dict[str, Any]:
        try:
            standardized = self._converter.convert(source_metadata)
            payload = standardized.to_dict()
        except ValueError:
            unique_id = f"local_{content_hash[:12]}"
            payload = self._source_payload_base(
                source_metadata,
                unique_id=unique_id,
                citation_key=self._build_citation_key(source_metadata, unique_id),
                source=source_metadata.get("source", "manual"),
                title=source_metadata.get("title", Path(file_path).stem),
                abstract=source_metadata.get("abstract", ""),
            )

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
        return payload

    def _build_text_source_payload(
        self,
        *,
        source_kind: str,
        locator: str,
        content: str,
        content_hash: str,
        source_metadata: Dict[str, Any],
        log_event: str,
    ) -> Dict[str, Any]:
        fallback_title = (
            Path(locator).stem
            if locator and source_kind == "markdown"
            else f"{source_kind.title()} source"
        )
        title = source_metadata.get("title") or self._infer_markdown_title(content, fallback_title)
        headings = source_metadata.get("fulltext_sections") or self._extract_markdown_headings(
            content
        )
        abstract = source_metadata.get("abstract") or self._build_markdown_summary(content)

        payload = self._source_payload_base(
            source_metadata,
            unique_id=source_metadata.get("unique_id") or f"{source_kind}_{content_hash[:12]}",
            citation_key=source_metadata.get("citation_key"),
            source=source_metadata.get("source", source_kind),
            title=title,
            abstract=abstract,
        )

        payload.update(source_metadata)
        payload.setdefault("citation_key", self._build_citation_key(payload, payload["unique_id"]))
        payload["content_hash"] = content_hash
        payload["saved_at"] = (
            payload.get("saved_at") or __import__("datetime").datetime.now().isoformat()
        )
        payload["data_source"] = payload.get("data_source") or f"{source_kind}_intake"
        payload["fulltext_sections"] = headings
        payload["fulltext_ingested"] = True
        payload["extracted_markdown"] = content
        payload["trust_level"] = payload.get("trust_level", "user")
        payload["provenance"] = list(payload.get("provenance", [])) + [
            {
                "event": log_event,
                "source_locator": locator,
                "content_hash": content_hash,
                "data_source": payload["data_source"],
            }
        ]
        return payload
