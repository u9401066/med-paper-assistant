"""Figure and table notes materialized from asset manifests."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from med_paper_assistant.shared.path_guard import (
    PathGuardError,
    normalize_relative_filename,
)

from ._foam_asset_types import AssetEntryContext, AssetNoteRun

logger = structlog.get_logger()


class FoamAssetNotesMixin:
    """Figure and table notes materialized from asset manifests."""

    def _materialize_asset_graph_notes(self) -> Dict[str, Any]:
        manifest = self._load_asset_manifest()
        project_root = Path(self._project_root_dir())
        project_slug = self._current_project_slug()
        reference_asset_contexts = self._load_reference_asset_contexts()
        figures: List[Dict[str, Any]] = []
        tables: List[Dict[str, Any]] = []

        from med_paper_assistant.infrastructure.persistence.data_artifact_tracker import (
            DataArtifactTracker,
        )

        tracker = DataArtifactTracker(project_root / ".audit", project_root)
        run = AssetNoteRun(
            project_root=project_root,
            project_slug=project_slug,
            tracker=tracker,
            contexts=reference_asset_contexts,
            aliases={"figure": {}, "table": {}},
            expected_paths={"figure": [], "table": []},
        )

        for asset_type, entries, notes_dir, folder in [
            ("figure", manifest.get("figures", []), self._figure_notes_dir(), "figures"),
            ("table", manifest.get("tables", []), self._table_notes_dir(), "tables"),
        ]:
            target_collection = figures if asset_type == "figure" else tables
            for entry in entries:
                item = self._materialize_asset_entry(asset_type, entry, notes_dir, folder, run)
                if item is not None:
                    target_collection.append(item)

        self._prune_stale_graph_notes(self._figure_notes_dir(), run.expected_paths["figure"])
        self._prune_stale_graph_notes(self._table_notes_dir(), run.expected_paths["table"])
        return {"figures": figures, "tables": tables, "aliases": run.aliases}

    def _manifest_asset_filename(self, asset_type: str, raw_filename: str) -> Optional[str]:
        try:
            return normalize_relative_filename(
                raw_filename,
                field_name=f"{asset_type} filename",
            )
        except PathGuardError as exc:
            logger.warning(
                "invalid_asset_manifest_filename",
                asset_type=asset_type,
                filename=raw_filename,
                error=str(exc),
            )
            return None

    def _prepare_asset_entry(
        self,
        asset_type: str,
        entry: Dict[str, Any],
        notes_dir: str,
        folder: str,
        run: AssetNoteRun,
    ) -> Optional[AssetEntryContext]:
        number = int(entry.get("number", 0) or 0)
        raw_filename = str(entry.get("filename", "")).strip()
        if number <= 0 or not raw_filename:
            return None
        filename = self._manifest_asset_filename(asset_type, raw_filename)
        if filename is None:
            return None

        slug = self._slugify(f"{asset_type}-{number}-{Path(filename).stem}")
        alias = f"{asset_type}-{number}"
        run.aliases[asset_type][str(number)] = alias
        note_path = os.path.join(notes_dir, f"{slug}.md")
        run.expected_paths[asset_type].append(note_path)

        relative_asset_path = f"results/{folder}/{filename}"
        review = run.tracker.get_asset_review(relative_asset_path, asset_type=asset_type)
        caption = entry.get("caption", filename)
        return AssetEntryContext(
            asset_type=asset_type,
            number=number,
            filename=filename,
            slug=slug,
            alias=alias,
            note_path=note_path,
            relative_asset_path=relative_asset_path,
            asset_path=run.project_root / relative_asset_path,
            review=review,
            review_state="reviewed" if review else "pending",
            caption=caption,
            title=f"{'Figure' if asset_type == 'figure' else 'Table'} {number}: {caption}",
            source_fragment=self._resolve_asset_source_fragment(
                asset_type, filename, str(caption), run.contexts
            ),
        )

    def _materialize_asset_entry(
        self,
        asset_type: str,
        entry: Dict[str, Any],
        notes_dir: str,
        folder: str,
        run: AssetNoteRun,
    ) -> Optional[Dict[str, Any]]:
        ctx = self._prepare_asset_entry(asset_type, entry, notes_dir, folder, run)
        if ctx is None:
            return None

        body_lines, fragment_anchors = self._build_asset_note_body(ctx)
        self._write_graph_note(
            ctx.note_path,
            title=ctx.title,
            note_type=f"{asset_type}-note",
            aliases=[ctx.alias, ctx.slug],
            tags=self._build_graph_note_tags(
                f"{asset_type}-note", "asset", self._asset_note_extra_tags(ctx)
            ),
            extra_fields={
                "note_class": f"{asset_type}-note",
                "note_domain": "asset",
                "project": run.project_slug,
                "asset_type": asset_type,
                "asset_number": ctx.number,
                "asset_filename": ctx.filename,
                "source_path": ctx.relative_asset_path,
                "review_state": ctx.review_state,
                "fragment_anchors": fragment_anchors,
                **self._asset_source_fragment_fields(ctx.source_fragment),
            },
            body="\n".join(body_lines),
        )
        return {"alias": ctx.alias, "title": ctx.title, "filename": ctx.filename}

    def _asset_note_extra_tags(self, ctx: AssetEntryContext) -> List[str]:
        return [
            f"asset/{ctx.asset_type}",
            f"review/{ctx.review_state}",
            f"number/{ctx.number}",
            f"format/{Path(ctx.filename).suffix.lstrip('.').lower() or 'unknown'}",
        ]

    def _asset_source_fragment_fields(self, source_fragment: Dict[str, Any]) -> Dict[str, Any]:
        keys = [
            ("source_doc_id", "doc_id"),
            ("source_asset_id", "asset_id"),
            ("source_block_id", "source_block_id"),
            ("source_reference", "citation_key"),
            ("source_page", "page"),
            ("source_bbox", "bbox"),
            ("source_line_range", "line_range"),
            ("source_section_path", "section_path"),
        ]
        return {field: source_fragment.get(key) if source_fragment else None for field, key in keys}
