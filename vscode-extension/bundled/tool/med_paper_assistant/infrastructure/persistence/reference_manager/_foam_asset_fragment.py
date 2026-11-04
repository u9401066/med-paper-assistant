"""Build the source fragment record that links an asset to its extracted source."""

from typing import Any, Dict, List, Optional, Tuple


class FoamAssetFragmentMixin:
    """Build the source fragment record that links an asset to its extracted source."""

    def _build_asset_source_match(
        self, context: Dict[str, Any], source_asset: Dict[str, Any]
    ) -> Dict[str, Any]:
        source_block_id = str(source_asset.get("source_block_id") or "")
        block = self._find_asset_source_block(context.get("blocks", []), source_block_id)
        segment = self._find_segmentation_segment(context.get("segmentation", {}), source_asset)

        line_start, line_end = self._asset_line_bounds(block, segment, source_asset)
        section_path = self._asset_section_path(block, segment, source_asset)

        bbox = block.get("bbox") if isinstance(block.get("bbox"), list) else []
        if not bbox:
            bbox = self._segment_bbox(segment)

        return {
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
            "snippet": self._asset_snippet(block, segment, source_asset),
        }

    def _asset_line_bounds(
        self,
        block: Dict[str, Any],
        segment: Dict[str, Any],
        source_asset: Dict[str, Any],
    ) -> Tuple[Optional[int], Optional[int]]:
        block_metadata = block.get("metadata") or {}
        line_start = self._first_int_field("line_start", block_metadata, segment, source_asset)
        line_end = self._first_int_field("line_end", block_metadata, segment, source_asset)
        return line_start, line_end

    def _first_int_field(self, key: str, *sources: Dict[str, Any]) -> Optional[int]:
        for source in sources:
            if isinstance(source.get(key), int):
                return int(source[key])
        return None

    def _asset_section_path(
        self,
        block: Dict[str, Any],
        segment: Dict[str, Any],
        source_asset: Dict[str, Any],
    ) -> List[str]:
        section_path = self._section_path_from_hierarchy(block.get("section_hierarchy"))
        if not section_path:
            section_path = self._section_path_from_hierarchy(segment.get("section_hierarchy"))
        if not section_path and source_asset.get("section_title"):
            section_path = [str(source_asset.get("section_title"))]
        return section_path

    def _asset_snippet(
        self,
        block: Dict[str, Any],
        segment: Dict[str, Any],
        source_asset: Dict[str, Any],
    ) -> str:
        snippet = str(block.get("text") or "").strip()
        if not snippet:
            snippet = str(segment.get("text") or "").strip()
        if not snippet:
            snippet = str(
                source_asset.get("markdown")
                or source_asset.get("preview")
                or source_asset.get("caption")
                or ""
            ).strip()
        return snippet
