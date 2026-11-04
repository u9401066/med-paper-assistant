"""Citation keys, identity registries and payload normalisation."""

import os
from typing import Any, Dict, Optional

from med_paper_assistant.shared.path_guard import (
    PathGuardError,
)


class IdentityMixin:
    """Citation keys, identity registries and payload normalisation."""

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

    def check_reference_exists(self, pmid: str) -> bool:
        """
        Check if a reference is already saved locally.

        Args:
            pmid: PubMed ID.

        Returns:
            True if reference exists locally.
        """
        try:
            ref_dir = self._reference_dir(pmid)
        except (PathGuardError, ValueError):
            return False
        return os.path.exists(ref_dir)
