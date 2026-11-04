"""Reference snapshot selection for knowledge-map and synthesis pages."""

from typing import Any, Dict, List, Optional


class FoamSnapshotMixin:
    """Reference snapshot selection for knowledge-map and synthesis pages."""

    def _resolve_reference_snapshots(
        self,
        reference_ids: Optional[List[str]] = None,
        *,
        query: str = "",
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        if reference_ids:
            selected_ids = self._explicit_snapshot_ids(reference_ids)
        elif query.strip():
            selected_ids = self._query_snapshot_ids(query, limit)
        else:
            selected_ids = self._recent_snapshot_ids(limit)

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

    def _explicit_snapshot_ids(self, reference_ids: List[str]) -> List[str]:
        selected_ids: List[str] = []
        seen_ids: set[str] = set()
        for ref_id in reference_ids:
            normalized = str(ref_id).strip()
            if not normalized or normalized in seen_ids:
                continue
            seen_ids.add(normalized)
            selected_ids.append(normalized)
        return selected_ids

    def _query_snapshot_ids(self, query: str, limit: int) -> List[str]:
        selected_ids: List[str] = []
        seen_ids: set[str] = set()
        for metadata in self.search_local(query):
            ref_id = str(metadata.get("unique_id") or metadata.get("pmid") or "").strip()
            if not ref_id or ref_id in seen_ids:
                continue
            seen_ids.add(ref_id)
            selected_ids.append(ref_id)
            if len(selected_ids) >= limit:
                break
        return selected_ids

    def _recent_snapshot_ids(self, limit: int) -> List[str]:
        all_metadata: List[Dict[str, Any]] = []
        for ref_id in self.list_references():
            metadata = self.get_metadata(ref_id)
            if not metadata:
                continue
            metadata = dict(metadata)
            metadata["unique_id"] = metadata.get("unique_id") or ref_id
            all_metadata.append(metadata)

        all_metadata.sort(key=lambda item: item.get("saved_at", ""), reverse=True)
        return [
            str(item.get("unique_id") or "").strip()
            for item in all_metadata[:limit]
            if str(item.get("unique_id") or "").strip()
        ]
