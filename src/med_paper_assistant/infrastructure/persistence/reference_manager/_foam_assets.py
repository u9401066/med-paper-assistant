"""Asset-aware manifest lookup and source fragment resolution."""

import os
from pathlib import Path
from typing import Any, Dict, List


class FoamAssetSourceMixin:
    """Asset-aware manifest lookup and source fragment resolution."""

    def _load_asset_manifest(self) -> Dict[str, Any]:
        manifest_path = os.path.join(self._project_root_dir(), "results", "manifest.json")
        return self._read_json_file(manifest_path, {"figures": [], "tables": []})

    def _asset_aware_artifact_dir(self, reference_id: str) -> Path:
        return self._reference_dir(reference_id) / "artifacts" / "asset-aware"

    def _display_line_range(self, line_start: Any, line_end: Any) -> str:
        if not isinstance(line_start, int):
            return ""
        if isinstance(line_end, int) and line_end >= line_start:
            start_display = line_start + 1
            end_display = max(start_display, line_end)
            return (
                str(start_display)
                if start_display == end_display
                else f"{start_display}-{end_display}"
            )
        return str(line_start + 1)

    def _segment_bbox(self, segment: Dict[str, Any]) -> List[float]:
        left = segment.get("left")
        top = segment.get("top")
        width = segment.get("width")
        height = segment.get("height")
        if (
            isinstance(left, (int, float))
            and isinstance(top, (int, float))
            and isinstance(width, (int, float))
            and isinstance(height, (int, float))
        ):
            left_f = float(left)
            top_f = float(top)
            width_f = float(width)
            height_f = float(height)
            return [left_f, top_f, left_f + width_f, top_f + height_f]
        return []

    def _section_path_from_hierarchy(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, dict):
            ordered_keys = sorted(
                value.keys(), key=lambda item: int(str(item)) if str(item).isdigit() else str(item)
            )
            return [str(value[key]).strip() for key in ordered_keys if str(value[key]).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _load_reference_asset_contexts(self) -> List[Dict[str, Any]]:
        contexts: List[Dict[str, Any]] = []
        for reference_id in self.list_references():
            metadata = self.get_metadata(reference_id)
            if not metadata:
                continue

            artifact_dir = self._asset_aware_artifact_dir(reference_id)
            manifest = self._read_json_file(str(artifact_dir / "manifest.json"), {})
            blocks = self._read_json_file(str(artifact_dir / "blocks.json"), [])
            segmentation = self._read_json_file(str(artifact_dir / "segmentation.json"), {})
            if not manifest and not blocks and not segmentation:
                continue

            contexts.append(
                {
                    "reference_id": reference_id,
                    "metadata": metadata,
                    "manifest": manifest,
                    "blocks": blocks if isinstance(blocks, list) else [],
                    "segmentation": segmentation if isinstance(segmentation, dict) else {},
                }
            )
        return contexts

    def _score_asset_manifest_candidate(
        self,
        *,
        filename: str,
        caption: str,
        source_asset: Dict[str, Any],
    ) -> int:
        score = 0
        registered_stem = self._normalize_match_text(Path(filename).stem)
        registered_caption = self._normalize_match_text(caption)
        source_caption = self._normalize_match_text(source_asset.get("caption", ""))
        source_id = self._normalize_match_text(source_asset.get("id", ""))
        source_path_stem = self._normalize_match_text(Path(str(source_asset.get("path", ""))).stem)
        source_preview = self._normalize_match_text(source_asset.get("preview", ""))

        if registered_caption and source_caption:
            if registered_caption == source_caption:
                score += 20
            elif registered_caption in source_caption or source_caption in registered_caption:
                score += 10

        if registered_stem and source_path_stem:
            if registered_stem == source_path_stem:
                score += 12
            elif registered_stem in source_path_stem or source_path_stem in registered_stem:
                score += 6

        if registered_stem and source_id:
            if registered_stem == source_id:
                score += 8
            elif registered_stem in source_id or source_id in registered_stem:
                score += 4

        if registered_stem and source_preview and registered_stem in source_preview:
            score += 3

        return score

    def _find_asset_source_block(
        self,
        blocks: List[Dict[str, Any]],
        source_block_id: str,
    ) -> Dict[str, Any]:
        if not source_block_id:
            return {}
        for block in blocks:
            if str(block.get("block_id") or "") == source_block_id:
                return block
        return {}

    def _find_segmentation_segment(
        self,
        segmentation: Dict[str, Any],
        source_asset: Dict[str, Any],
    ) -> Dict[str, Any]:
        segments = segmentation.get("segments", [])
        if not isinstance(segments, list):
            return {}

        source_block_id = str(source_asset.get("source_block_id") or "")
        source_asset_id = str(source_asset.get("id") or "")
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            metadata = segment.get("metadata") or {}
            if source_block_id and (
                str(segment.get("segment_id") or "") == source_block_id
                or str(metadata.get("source_block_id") or "") == source_block_id
            ):
                return segment

        for segment in segments:
            if not isinstance(segment, dict):
                continue
            if source_asset_id and str(segment.get("asset_id") or "") == source_asset_id:
                return segment

        return {}

    def _resolve_asset_source_fragment(
        self,
        asset_type: str,
        filename: str,
        caption: str,
        reference_contexts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        manifest_key = "figures" if asset_type == "figure" else "tables"
        best_match: Dict[str, Any] = {}
        best_score = 0

        for context in reference_contexts:
            manifest_assets = ((context.get("manifest") or {}).get("assets") or {}).get(
                manifest_key, []
            )
            if not isinstance(manifest_assets, list):
                continue

            for source_asset in manifest_assets:
                if not isinstance(source_asset, dict):
                    continue

                score = self._score_asset_manifest_candidate(
                    filename=filename,
                    caption=caption,
                    source_asset=source_asset,
                )
                if score <= best_score:
                    continue

                best_score = score
                best_match = self._build_asset_source_match(context, source_asset)

        return best_match if best_score >= 10 else {}

    def _asset_anchor(self, label: str, fallback: str = "fragment") -> str:
        return f"^{self._slugify(label, fallback)}"

    def _build_table_preview_fragments(self, preview: str) -> List[Dict[str, str]]:
        lines = [line.rstrip() for line in preview.splitlines() if line.strip()]
        if len(lines) < 3:
            return []

        if "|" in lines[0] and "|" in lines[1]:
            header = lines[0]
            separator = lines[1]
            rows = [line for line in lines[2:] if "|" in line]
            return [
                {
                    "title": f"Row {index}",
                    "content": "\n".join([header, separator, row]),
                    "anchor": f"^table-row-{index}",
                }
                for index, row in enumerate(rows[:5], start=1)
            ]

        if "," in lines[0]:
            header = lines[0]
            rows = lines[1:6]
            return [
                {
                    "title": f"Row {index}",
                    "content": "\n".join([header, row]),
                    "anchor": f"^table-row-{index}",
                }
                for index, row in enumerate(rows, start=1)
            ]

        return []
