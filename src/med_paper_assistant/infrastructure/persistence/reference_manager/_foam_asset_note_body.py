"""Markdown body builders for figure and table notes."""

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ._foam_asset_types import AssetEntryContext


class FoamAssetNoteBodyMixin:
    """Markdown body builders for figure and table notes."""

    def _build_asset_note_body(self, ctx: AssetEntryContext) -> Tuple[List[str], List[str]]:
        asset_path = ctx.asset_path
        fragment_anchors: List[str] = []
        summary_anchor = self._asset_anchor("asset-summary")
        fragment_anchors.append(summary_anchor)
        body_lines = [
            "## Asset Summary",
            "",
            f"Caption: {ctx.caption}",
            f"Source asset: {ctx.relative_asset_path}",
            f"Review state: {ctx.review_state}",
            "",
            summary_anchor,
        ]

        if ctx.asset_type == "figure" and asset_path.exists():
            self._append_figure_preview(
                body_lines, fragment_anchors, ctx.title, asset_path, ctx.note_path
            )

        preview = self._read_text_preview(str(asset_path)) if asset_path.exists() else ""
        if preview:
            self._append_data_preview(body_lines, fragment_anchors, ctx.asset_type, preview)
        if ctx.review:
            self._append_review_sections(body_lines, fragment_anchors, ctx.review)
        if ctx.source_fragment:
            self._append_source_fragment_sections(body_lines, fragment_anchors, ctx.source_fragment)
        return body_lines, fragment_anchors

    def _append_figure_preview(
        self,
        body_lines: List[str],
        fragment_anchors: List[str],
        title: str,
        asset_path: Path,
        note_path: str,
    ) -> None:
        relative_embed = os.path.relpath(asset_path, Path(note_path).parent).replace("\\", "/")
        preview_anchor = self._asset_anchor("asset-preview")
        fragment_anchors.append(preview_anchor)
        body_lines.extend(
            [
                "",
                "## Figure Preview",
                "",
                f"![{title}]({relative_embed})",
                "",
                preview_anchor,
            ]
        )

    def _append_data_preview(
        self,
        body_lines: List[str],
        fragment_anchors: List[str],
        asset_type: str,
        preview: str,
    ) -> None:
        preview_anchor = self._asset_anchor("data-preview")
        fragment_anchors.append(preview_anchor)
        body_lines.extend(["", "## Data Preview", "", preview, "", preview_anchor])

        if asset_type != "table":
            return
        table_fragments = self._build_table_preview_fragments(preview)
        if not table_fragments:
            return
        body_lines.extend(["", "## Table Fragments", ""])
        for fragment in table_fragments:
            fragment_anchors.append(fragment["anchor"])
            body_lines.extend(
                [
                    f"### {fragment['title']}",
                    "",
                    fragment["content"],
                    "",
                    fragment["anchor"],
                    "",
                ]
            )

    def _append_review_sections(
        self,
        body_lines: List[str],
        fragment_anchors: List[str],
        review: Dict[str, Any],
    ) -> None:
        observations = [str(item) for item in review.get("observations", [])]
        if observations:
            body_lines.extend(["", "## Review Observations", ""])
            for index, item in enumerate(observations, start=1):
                anchor = f"^review-observation-{index}"
                fragment_anchors.append(anchor)
                body_lines.extend([f"### Observation {index}", "", item, "", anchor, ""])
        evidence_excerpt = str(review.get("evidence_excerpt", "")).strip()
        if evidence_excerpt:
            excerpt_anchor = self._asset_anchor("evidence-excerpt")
            fragment_anchors.append(excerpt_anchor)
            body_lines.extend(["", "## Evidence Excerpt", "", evidence_excerpt, "", excerpt_anchor])

    def _append_source_fragment_sections(
        self,
        body_lines: List[str],
        fragment_anchors: List[str],
        source_fragment: Dict[str, Any],
    ) -> None:
        source_fragment_anchor = self._asset_anchor("source-fragment")
        source_bbox_anchor = self._asset_anchor("source-bbox")
        source_snippet_anchor = self._asset_anchor("source-snippet")
        fragment_anchors.extend([source_fragment_anchor, source_bbox_anchor, source_snippet_anchor])
        body_lines.extend(
            [
                "",
                "## Source Fragment",
                "",
                f"- Reference: [[{source_fragment['citation_key']}]]",
                f"- Doc ID: {source_fragment['doc_id'] or 'unknown'}",
                f"- Asset ID: {source_fragment['asset_id'] or 'unknown'}",
                f"- Source Block: {source_fragment['source_block_id'] or 'unknown'}",
                f"- Page: {source_fragment['page'] or 'unknown'}",
            ]
        )
        if source_fragment.get("line_range"):
            body_lines.append(f"- Lines: {source_fragment['line_range']}")
        if source_fragment.get("section_path"):
            body_lines.append(f"- Section: {' > '.join(source_fragment['section_path'])}")
        body_lines.extend(["", source_fragment_anchor, ""])

        if source_fragment.get("bbox"):
            body_lines.extend(
                [
                    "### Source Bounding Box",
                    "",
                    f"{source_fragment['bbox']}",
                    "",
                    source_bbox_anchor,
                    "",
                ]
            )
        if source_fragment.get("snippet"):
            body_lines.extend(
                [
                    "### Source Snippet",
                    "",
                    source_fragment["snippet"],
                    "",
                    source_snippet_anchor,
                    "",
                ]
            )
