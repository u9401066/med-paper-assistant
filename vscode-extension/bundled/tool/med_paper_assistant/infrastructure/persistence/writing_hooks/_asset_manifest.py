"""Writing Hooks — manifest.json / manuscript-plan.yaml loading for asset hooks (C7a/C7b/C7d)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ._models import HookIssue

_TABLE_TYPES = {
    "table",
    "table_one",
    "literature_summary_table",
    "comparison_table",
    "characteristics_table",
    "summary_table",
}
_FIGURE_TYPES = {
    "plot",
    "flow_diagram",
    "custom_figure",
    "forest_plot",
    "funnel_plot",
    "prisma_diagram",
    "concept_diagram",
    "figure",
}


def _asset_kind(asset_type: str) -> str | None:
    normalized = asset_type.strip().lower()
    if normalized in _TABLE_TYPES:
        return "table"
    if normalized in _FIGURE_TYPES:
        return "figure"
    return None


def _manifest_entry(kind: str, entry: dict[str, Any], number: Any) -> dict[str, str]:
    return {
        "kind": kind,
        "number": str(number).strip(),
        "filename": str(entry.get("filename", "")).strip(),
        "caption": str(entry.get("caption", "")).strip(),
    }


def normalize_manifest(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Normalize legacy (figures/tables) and current (assets) manifest schemas."""
    entries: list[dict[str, str]] = []
    for key, kind in (("figures", "figure"), ("tables", "table")):
        for entry in manifest.get(key, []):
            if isinstance(entry, dict):
                entries.append(_manifest_entry(kind, entry, entry.get("number", "")))
    for entry in manifest.get("assets", []):
        if isinstance(entry, dict) and entry.get("type") in {"figure", "table"}:
            number = entry.get("number", entry.get("id", ""))
            entries.append(_manifest_entry(str(entry.get("type", "")).strip(), entry, number))
    return entries


def _planned_asset(asset: Any, section_hint: str | None) -> dict[str, str] | None:
    if not isinstance(asset, dict):
        return None

    kind = _asset_kind(str(asset.get("type", "")))
    section = str(asset.get("section") or section_hint or "").strip()
    if kind is None or not section:
        return None
    if asset.get("required") is False or asset.get("optional") is True:
        return None

    return {
        "id": str(asset.get("id") or f"{section}-{kind}"),
        "kind": kind,
        "section": section,
        "caption": str(asset.get("caption") or "").strip(),
        "type": str(asset.get("type") or "").strip(),
    }


def normalize_asset_plan(raw_assets: Any) -> list[dict[str, str]]:
    """Normalize the ``asset_plan`` list/dict into required figure/table obligations."""
    pairs: list[tuple[Any, str | None]] = []
    if isinstance(raw_assets, list):
        pairs = [(asset, None) for asset in raw_assets]
    elif isinstance(raw_assets, dict):
        for section_name, assets in raw_assets.items():
            if isinstance(assets, list):
                pairs.extend((asset, str(section_name)) for asset in assets)
            elif isinstance(assets, dict):
                pairs.append((assets, str(section_name)))

    planned = (_planned_asset(asset, hint) for asset, hint in pairs)
    return [p for p in planned if p is not None]


def manifest_numbers(entries: list[dict[str, str]], kind: str) -> set[str]:
    return {a.get("number", "") for a in entries if a.get("kind") == kind}


def cross_reference_issues(
    label: str, refs: set[str], manifest: set[str]
) -> tuple[list[HookIssue], list[HookIssue]]:
    """Return (phantom, orphan) issues for one asset kind ('Figure' or 'Table')."""
    phantom = [
        HookIssue(
            hook_id="C7d",
            severity="CRITICAL",
            section="manuscript",
            message=f"Phantom: {label} {num} referenced in text but not in manifest",
            suggestion=f"Add {label} {num} to manifest or remove from text",
        )
        for num in sorted(refs - manifest)
    ]
    orphan = [
        HookIssue(
            hook_id="C7d",
            severity="WARNING",
            section="manifest",
            message=f"Orphan: {label} {num} in manifest but not referenced in text",
            suggestion=f"Add {label} {num} reference to text or remove from manifest",
        )
        for num in sorted(manifest - refs)
    ]
    return phantom, orphan


def asset_issue(asset: dict[str, str], message: str, suggestion: str) -> HookIssue:
    return HookIssue(
        hook_id="C7b",
        severity="CRITICAL",
        section=asset["section"],
        message=message,
        suggestion=suggestion,
    )


def is_asset_placed(kind: str, entry: dict[str, str], section_content: str) -> bool:
    """Whether the section text cites '<kind> <number>' or embeds the filename/caption."""
    text = section_content.lower()
    if not text:
        return False
    number = entry.get("number", "")
    if number and re.search(rf"\b{re.escape(kind)}\s+{re.escape(number)}\b", text):
        return True
    needles = [n.lower() for n in (entry.get("filename", ""), entry.get("caption", "")) if n]
    return any(n in text for n in needles)


class AssetManifestMixin:
    """Loads and matches the asset manifest/plan used by the C7 hooks."""

    _project_dir: Path

    def _load_manifest_entries(self) -> list[dict[str, str]]:
        """Normalize manifest.json across legacy and current schemas."""
        return self._load_manifest_entries_checked()[0]

    def _load_manifest_entries_checked(self) -> tuple[list[dict[str, str]], str | None]:
        """Like ``_load_manifest_entries`` but also returns a parse error message, if any."""
        manifest_path = self._project_dir / "results" / "manifest.json"
        if not manifest_path.is_file():
            return [], None

        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            if not isinstance(manifest, dict):
                raise ValueError("manifest root must be a JSON object")
            return normalize_manifest(manifest), None
        except (OSError, ValueError, TypeError) as exc:
            return [], f"{type(exc).__name__}: {exc}"

    @staticmethod
    def _parse_error_issue(hook_id: str, filename: str, error: str) -> HookIssue:
        return HookIssue(
            hook_id=hook_id,
            severity="CRITICAL",
            section="manifest",
            message=f"Cannot parse {filename}: {error}",
            suggestion=f"Fix or regenerate {filename}; this check cannot run on unreadable data",
        )

    def _load_required_visual_assets(self) -> list[dict[str, str]]:
        """Read manuscript-plan.yaml and normalize required figure/table obligations."""
        return self._load_required_visual_assets_checked()[0]

    def _load_required_visual_assets_checked(self) -> tuple[list[dict[str, str]], str | None]:
        """Like ``_load_required_visual_assets`` but also returns a parse error, if any."""
        plan_path = self._project_dir / "manuscript-plan.yaml"
        if not plan_path.is_file():
            return [], None

        import yaml

        try:
            plan = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
            if not isinstance(plan, dict):
                raise ValueError("plan root must be a mapping")
        except (OSError, ValueError, yaml.YAMLError) as exc:
            return [], f"{type(exc).__name__}: {exc}"

        return normalize_asset_plan(plan.get("asset_plan")), None

    def _match_planned_asset_to_manifest(
        self,
        planned_asset: dict[str, str],
        manifest_entries: list[dict[str, str]],
    ) -> dict[str, str] | None:
        """Match a planned asset to its manifest entry using caption or numeric id."""
        same_kind = [e for e in manifest_entries if e.get("kind") == planned_asset.get("kind")]
        if not same_kind:
            return None

        caption = planned_asset.get("caption", "").strip().lower()
        if caption:
            for entry in same_kind:
                entry_caption = entry.get("caption", "").strip().lower()
                if entry_caption and (
                    entry_caption == caption or caption in entry_caption or entry_caption in caption
                ):
                    return entry

        asset_id = planned_asset.get("id", "")
        numeric_parts = [part for part in asset_id.replace("_", "-").split("-") if part.isdigit()]
        if numeric_parts:
            target_number = numeric_parts[-1]
            for entry in same_kind:
                if entry.get("number") == target_number:
                    return entry

        return same_kind[0] if len(same_kind) == 1 else None

    def _has_exportable_figure_asset(self, filename: str) -> bool:
        """Check whether a figure filename is directly exportable or has a rendered companion."""
        if not filename:
            return False

        figure_path = self._project_dir / "results" / "figures" / filename
        if figure_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".tiff"}:
            return figure_path.is_file()

        for extension in [".png", ".svg", ".jpg", ".jpeg", ".tiff"]:
            if (figure_path.parent / f"{figure_path.stem}{extension}").is_file():
                return True
        return False
