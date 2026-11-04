"""Asset-aware ingestion receipts for ``.audit/source-materials.yaml``."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _refresh_source_materials_summary(manifest: dict[str, Any]) -> None:
    """Refresh summary and next-step fields after ingestion receipt updates."""
    materials = manifest.get("materials", [])
    if not isinstance(materials, list):
        materials = []
        manifest["materials"] = materials

    pending = [
        entry
        for entry in materials
        if isinstance(entry, dict)
        and entry.get("ingestion", {}).get("status") == "pending_asset_aware"
    ]
    manifest["summary"] = {
        "total_candidates": len(materials),
        "pending_asset_aware": len(pending),
        "ready_native": len(materials) - len(pending),
        "ingested_asset_aware": len(
            [
                entry
                for entry in materials
                if isinstance(entry, dict)
                and entry.get("ingestion", {}).get("status") == "ingested_asset_aware"
            ]
        ),
    }
    manifest["agent_next_steps"] = {
        "asset_aware_required": bool(pending),
        "asset_aware_file_paths": [
            str(entry.get("path")) for entry in pending if entry.get("path")
        ],
        "instruction": (
            "Call asset-aware ingest_documents on asset_aware_file_paths before Phase 5 "
            "and use extracted tables/sections as primary evidence."
            if pending
            else "No pending asset-aware ingestion remains."
        ),
    }


def _report_row(entry: dict[str, Any]) -> str:
    raw_ingestion = entry.get("ingestion")
    ingestion: dict[str, Any] = raw_ingestion if isinstance(raw_ingestion, dict) else {}
    return "| {id} | {file} | {kind} | {status} | {doc_id} |".format(
        id=entry.get("id", ""),
        file=entry.get("relative_path") or entry.get("filename") or "",
        kind=entry.get("kind", ""),
        status=ingestion.get("status", ""),
        doc_id=ingestion.get("asset_aware_doc_id", ""),
    )


def _write_source_materials_report_from_manifest(
    project_dir: Path, manifest: dict[str, Any]
) -> Path:
    """Write a compact markdown source-material report from the manifest."""
    report_path = project_dir / ".audit" / "source-materials.md"
    summary = manifest.get("summary", {})
    materials = manifest.get("materials", [])
    lines = [
        "# Source Materials Intake",
        "",
        f"- Schema: `{manifest.get('schema', 'mdpaper.source_materials.v1')}`",
        f"- Scan root: `{manifest.get('scan_root', '')}`",
        f"- Total candidates: {summary.get('total_candidates', 0)}",
        f"- Pending asset-aware ingestion: {summary.get('pending_asset_aware', 0)}",
        f"- Ingested asset-aware materials: {summary.get('ingested_asset_aware', 0)}",
        "",
        "| ID | File | Kind | Ingestion status | Asset-aware doc |",
        "|---|---|---|---|---|",
    ]
    if isinstance(materials, list) and materials:
        lines.extend(_report_row(entry) for entry in materials if isinstance(entry, dict))
    else:
        lines.append("| - | No source materials found | - | - | - |")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def _load_manifest(manifest_path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return None, f"invalid source-materials.yaml: {exc}"
    if not isinstance(manifest, dict):
        return None, "source-materials.yaml must be a mapping"
    return manifest, ""


def _find_material(
    materials: list[Any], source_material_id: str, source_path_text: str
) -> dict[str, Any] | None:
    for entry in materials:
        if not isinstance(entry, dict):
            continue
        refs = {
            str(entry.get("id") or ""),
            str(entry.get("path") or ""),
            str(entry.get("relative_path") or ""),
            str(entry.get("filename") or ""),
        }
        refs.add(Path(str(entry.get("path") or "")).name)
        refs.add(Path(str(entry.get("relative_path") or "")).name)
        if (source_material_id and source_material_id in refs) or (
            source_path_text and source_path_text in refs
        ):
            return entry
    return None


def _apply_receipt(
    target: dict[str, Any],
    *,
    asset_aware_doc_id: str,
    sections: list[Any],
    artifact_paths: list[Any],
    ingestion_status: str,
) -> None:
    ingestion = target.setdefault("ingestion", {})
    if not isinstance(ingestion, dict):
        ingestion = {}
        target["ingestion"] = ingestion

    status = ingestion_status.strip() or "ingested_asset_aware"
    ingestion.update(
        {
            "status": status,
            "required": False
            if status == "ingested_asset_aware"
            else ingestion.get("required", True),
            "asset_aware_doc_id": asset_aware_doc_id.strip(),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    target["asset_aware_doc_id"] = asset_aware_doc_id.strip()
    if sections:
        target["fulltext_sections"] = sections
        ingestion["sections"] = sections
    if artifact_paths:
        target["asset_aware_artifacts"] = artifact_paths
        ingestion["artifact_paths"] = artifact_paths


def _load_target_material(
    manifest_path: Path, source_material_id: str, source_path: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str]:
    manifest, load_error = _load_manifest(manifest_path)
    if manifest is None:
        return None, None, load_error

    materials = manifest.get("materials", [])
    if not isinstance(materials, list):
        return None, None, "source-materials.yaml materials must be a list"

    target = _find_material(materials, source_material_id, source_path.strip())
    if target is None:
        return (
            None,
            None,
            "source material not found; pass source_material_id or source_path from source-materials.yaml",
        )
    return manifest, target, ""


def record_asset_ingestion_receipt(
    *,
    project_dir: Path,
    source_material_id: str,
    source_path: str,
    asset_aware_doc_id: str,
    sections: list[Any],
    artifact_paths: list[Any],
    ingestion_status: str,
) -> tuple[bool, str]:
    """Record an asset-aware ingestion receipt in `.audit/source-materials.yaml`."""
    manifest_path = project_dir / ".audit" / "source-materials.yaml"
    if not manifest_path.is_file():
        return (
            False,
            'MISSING .audit/source-materials.yaml — run project_action(action="source_materials") first',
        )
    if not asset_aware_doc_id.strip():
        return False, "asset_aware_doc_id is required"

    manifest, target, load_error = _load_target_material(
        manifest_path, source_material_id, source_path
    )
    if manifest is None or target is None:
        return False, load_error

    _apply_receipt(
        target,
        asset_aware_doc_id=asset_aware_doc_id,
        sections=sections,
        artifact_paths=artifact_paths,
        ingestion_status=ingestion_status,
    )
    _refresh_source_materials_summary(manifest)
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(
        yaml.dump(manifest, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    report_path = _write_source_materials_report_from_manifest(project_dir, manifest)
    return True, (
        f"recorded ingestion for {target.get('id')} -> {asset_aware_doc_id.strip()}; "
        f"manifest={manifest_path.relative_to(project_dir).as_posix()}; "
        f"report={report_path.relative_to(project_dir).as_posix()}"
    )
