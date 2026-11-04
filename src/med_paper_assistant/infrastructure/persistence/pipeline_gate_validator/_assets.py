"""Planned-asset and manifest helpers for the Phase 5 asset gates."""

from __future__ import annotations

from typing import Any

from med_paper_assistant.infrastructure.persistence.state_io import load_json_object

from ._base import GateBase
from ._io import load_yaml_mapping

_TABLE_ASSET_TYPES = frozenset(
    {
        "table",
        "table_one",
        "literature_summary_table",
        "comparison_table",
        "characteristics_table",
        "summary_table",
    }
)
_FIGURE_ASSET_TYPES = frozenset(
    {
        "plot",
        "flow_diagram",
        "custom_figure",
        "forest_plot",
        "funnel_plot",
        "prisma_diagram",
        "concept_diagram",
        "figure",
    }
)


def _normalized_asset(asset: Any, section_hint: str | None) -> dict[str, Any] | None:
    if not isinstance(asset, dict):
        return None

    asset_type = str(asset.get("type", "")).strip()
    section = str(asset.get("section") or section_hint or "").strip()
    if not asset_type or not section:
        return None

    required = asset.get("required")
    optional = asset.get("optional")
    is_required = not (required is False or optional is True)
    return {
        "id": str(asset.get("id") or f"{section}-{asset_type}"),
        "type": asset_type,
        "section": section,
        "caption": str(asset.get("caption") or "").strip(),
        "required": is_required,
    }


def _manifest_entry(kind: str, entry: dict[str, Any], number: Any) -> dict[str, Any]:
    return {
        "kind": kind,
        "number": str(number).strip(),
        "filename": str(entry.get("filename", "")).strip(),
        "caption": str(entry.get("caption", "")).strip(),
    }


class AssetPlanMixin(GateBase):
    """Planned-asset declarations and the results manifest they are matched against."""

    def _load_manuscript_plan(self) -> dict[str, Any]:
        """Load manuscript-plan.yaml when available."""
        return load_yaml_mapping(self._project_dir / "manuscript-plan.yaml")

    def _normalize_planned_assets(self, plan: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize manuscript-plan asset declarations into a flat list."""
        raw_assets = plan.get("asset_plan")
        if not raw_assets:
            return []

        normalized: list[dict[str, Any]] = []

        def _append_asset(asset: Any, section_hint: str | None = None) -> None:
            item = _normalized_asset(asset, section_hint)
            if item is not None:
                normalized.append(item)

        if isinstance(raw_assets, list):
            for asset in raw_assets:
                _append_asset(asset)
        elif isinstance(raw_assets, dict):
            for section_name, assets in raw_assets.items():
                if isinstance(assets, list):
                    for asset in assets:
                        _append_asset(asset, str(section_name))
                elif isinstance(assets, dict):
                    _append_asset(assets, str(section_name))

        return normalized

    def _asset_kind(self, asset_type: str) -> str | None:
        """Map asset types to figure/table kinds that need hard validation."""
        normalized = asset_type.strip().lower()
        if normalized in _TABLE_ASSET_TYPES:
            return "table"
        if normalized in _FIGURE_ASSET_TYPES:
            return "figure"
        return None

    def _load_manifest_entries(self) -> list[dict[str, Any]]:
        """Normalize manifest.json across legacy and current schemas."""
        manifest_path = self._project_dir / "results" / "manifest.json"
        if not manifest_path.is_file():
            return []

        manifest = load_json_object(manifest_path) or {}

        entries: list[dict[str, Any]] = []
        for entry in manifest.get("figures") or []:
            if isinstance(entry, dict):
                entries.append(_manifest_entry("figure", entry, entry.get("number", "")))
        for entry in manifest.get("tables") or []:
            if isinstance(entry, dict):
                entries.append(_manifest_entry("table", entry, entry.get("number", "")))
        for entry in manifest.get("assets") or []:
            if isinstance(entry, dict) and entry.get("type") in {"figure", "table"}:
                number = entry.get("number", entry.get("id", ""))
                entries.append(_manifest_entry(str(entry.get("type", "")), entry, number))
        return entries

    def _match_manifest_asset(
        self,
        planned_asset: dict[str, Any],
        manifest_entries: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Find the manifest entry that most likely satisfies a planned asset."""
        kind = self._asset_kind(planned_asset["type"])
        if kind is None:
            return None

        same_kind = [entry for entry in manifest_entries if entry.get("kind") == kind]
        if not same_kind:
            return None

        caption = planned_asset.get("caption", "").strip().lower()
        if caption:
            for entry in same_kind:
                entry_caption = entry.get("caption", "").strip().lower()
                if entry_caption and (caption in entry_caption or entry_caption in caption):
                    return entry

        asset_id = str(planned_asset.get("id", ""))
        numeric_parts = [part for part in asset_id.replace("_", "-").split("-") if part.isdigit()]
        if numeric_parts:
            target_number = numeric_parts[-1]
            for entry in same_kind:
                if entry.get("number") == target_number:
                    return entry

        return same_kind[0] if len(same_kind) == 1 else None

    def _has_exportable_figure(self, filename: str) -> bool:
        """Return True when a figure has a rendered asset suitable for export."""
        if not filename:
            return False

        figure_path = self._project_dir / "results" / "figures" / filename
        if figure_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".tiff"}:
            return figure_path.is_file()

        for extension in [".png", ".svg", ".jpg", ".jpeg", ".tiff"]:
            if (figure_path.parent / f"{figure_path.stem}{extension}").is_file():
                return True

        return False
