"""Read-only lookups over saved references."""

import json
import os
from typing import Any, Dict, List

from med_paper_assistant.shared.path_guard import (
    PathGuardError,
)


class ReferenceQueryMixin:
    """Read-only lookups over saved references."""

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

        try:
            ref_dir = self._reference_dir(pmid)
        except (PathGuardError, ValueError):
            return {}
        detail: Dict[str, Any] = {
            "pmid": pmid,
            "metadata": metadata,
            "ref_dir": str(ref_dir),
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

    def _load_reference_analysis(self, reference_id: str) -> Dict[str, Any]:
        try:
            analysis_path = self._reference_dir(reference_id) / "analysis.json"
        except (PathGuardError, ValueError):
            return {}
        if not analysis_path.is_file():
            return {}

        try:
            return json.loads(analysis_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
