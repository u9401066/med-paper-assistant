"""Data Artifact Tracker — data-anchor provenance validation mixin."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

import yaml

from ._models import _TRUSTED_DATA_SUFFIXES, _UNTRUSTED_ANCHOR_SOURCE_HINTS
from ._storage import _StorageMixin


class _AnchorEvidence(NamedTuple):
    """Primary-evidence lookups shared by every anchor in one validation pass."""

    source_by_id: dict[str, dict[str, Any]]
    source_by_ref: dict[str, dict[str, Any]]
    artifact_ids: set[str]
    artifact_outputs: set[str]


def _anchor_name(anchor: dict[str, Any]) -> str:
    return str(
        anchor.get("name")
        or anchor.get("id")
        or anchor.get("key")
        or anchor.get("label")
        or "unnamed"
    )


def _untrusted_source_issue(
    tracker: _AnchorMixin, anchor: dict[str, Any], name: str
) -> dict[str, str] | None:
    explicit_source = tracker._anchor_field(
        anchor,
        "source",
        "source_type",
        "data_source",
        "source_file",
        "source_path",
    )
    if not explicit_source or not any(
        hint in str(explicit_source).lower() for hint in _UNTRUSTED_ANCHOR_SOURCE_HINTS
    ):
        return None
    return {
        "severity": "CRITICAL",
        "category": "data_anchor_untrusted_source",
        "message": (
            f"Data anchor '{name}' cites an agent/generated source "
            f"('{explicit_source}'); anchors must cite primary data, source-material, "
            "asset-aware, or tracked analysis provenance"
        ),
    }


def _cites_tracked_evidence(
    tracker: _AnchorMixin, anchor: dict[str, Any], evidence: _AnchorEvidence
) -> bool:
    asset_doc = tracker._anchor_field(
        anchor,
        "asset_aware_doc_id",
        "assetAwareDocId",
        "asset_doc_id",
        "doc_id",
    )
    if asset_doc:
        return True

    artifact_ref = tracker._anchor_field(
        anchor,
        "data_artifact_id",
        "artifact_id",
        "artifact",
        "analysis_artifact_id",
    )
    if artifact_ref and str(artifact_ref) in evidence.artifact_ids:
        return True

    output_ref = tracker._anchor_field(anchor, "output_path", "artifact_output_path")
    return bool(output_ref and str(output_ref) in evidence.artifact_outputs)


def _material_issues(
    tracker: _AnchorMixin, material: dict[str, Any], name: str
) -> list[dict[str, str]]:
    ready, detail = tracker._material_ready_for_anchor(material)
    if ready:
        return []
    return [
        {
            "severity": "CRITICAL",
            "category": "data_anchor_uningested_source",
            "message": f"Data anchor '{name}' cites {detail}",
        }
    ]


def _unverified_issue(name: str) -> dict[str, str]:
    return {
        "severity": "CRITICAL",
        "category": "data_anchor_unverified",
        "message": (
            f"Data anchor '{name}' lacks primary-source provenance; include "
            "source_material_id for an ingested/ready source material, "
            "asset_aware_doc_id, data_artifact_id, or a trusted data_source file"
        ),
    }


def _anchor_issues(
    tracker: _AnchorMixin, anchor: dict[str, Any], evidence: _AnchorEvidence
) -> list[dict[str, str]]:
    name = _anchor_name(anchor)

    untrusted = _untrusted_source_issue(tracker, anchor, name)
    if untrusted:
        return [untrusted]
    if _cites_tracked_evidence(tracker, anchor, evidence):
        return []

    source_material_id = tracker._anchor_field(
        anchor,
        "source_material_id",
        "sourceMaterialId",
        "material_id",
    )
    if source_material_id:
        material = evidence.source_by_id.get(str(source_material_id))
        if material:
            return _material_issues(tracker, material, name)

    source_ref = tracker._anchor_field(
        anchor,
        "source_material_path",
        "source_file",
        "source_path",
        "data_source",
        "file",
    )
    if source_ref:
        material = evidence.source_by_ref.get(str(source_ref)) or evidence.source_by_ref.get(
            Path(str(source_ref)).name
        )
        if material:
            return _material_issues(tracker, material, name)
        if tracker._path_is_trusted_data_source(str(source_ref)):
            return []

    return [_unverified_issue(name)]


class _AnchorMixin(_StorageMixin):
    """Phase 0 source-material lookup and data-anchor provenance validation."""

    def _load_source_materials(self) -> dict[str, Any]:
        """Load Phase 0 source-material intake manifest when available."""
        manifest_path = self._audit_dir / "source-materials.yaml"
        if not manifest_path.is_file():
            return {"materials": []}
        try:
            loaded = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, OSError):
            return {"materials": []}
        return loaded if isinstance(loaded, dict) else {"materials": []}

    def _coerce_data_anchor_entries(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize flexible data-anchor schemas into a list of entries."""
        raw = (
            data.get("data_anchors")
            or data.get("dataAnchors")
            or data.get("anchors")
            or data.get("statistical_anchors")
            or []
        )
        entries: list[dict[str, Any]] = []
        if isinstance(raw, dict):
            for name, value in raw.items():
                if isinstance(value, dict):
                    entry = dict(value)
                    entry.setdefault("name", str(name))
                else:
                    entry = {"name": str(name), "value": value}
                entries.append(entry)
        elif isinstance(raw, list):
            for index, item in enumerate(raw, start=1):
                if isinstance(item, dict):
                    entry = dict(item)
                    entry.setdefault("name", str(entry.get("id") or entry.get("key") or index))
                    entries.append(entry)
        return entries

    def _anchor_field(self, anchor: dict[str, Any], *names: str) -> Any:
        """Read an anchor field from top-level keys or a nested provenance block."""
        for name in names:
            if name in anchor and anchor[name] not in (None, ""):
                return anchor[name]
        provenance = anchor.get("provenance")
        if isinstance(provenance, dict):
            for name in names:
                if name in provenance and provenance[name] not in (None, ""):
                    return provenance[name]
        return None

    def _source_material_lookup(
        self,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        """Build source-material lookup maps by id/path/filename."""
        manifest = self._load_source_materials()
        by_id: dict[str, dict[str, Any]] = {}
        by_ref: dict[str, dict[str, Any]] = {}
        materials = manifest.get("materials", [])
        if not isinstance(materials, list):
            return by_id, by_ref

        for material in materials:
            if not isinstance(material, dict):
                continue
            material_id = str(material.get("id") or "").strip()
            if material_id:
                by_id[material_id] = material
            for key in ("path", "relative_path", "filename"):
                ref = str(material.get(key) or "").strip()
                if ref:
                    by_ref[ref] = material
                    by_ref[Path(ref).name] = material
        return by_id, by_ref

    def _material_ready_for_anchor(self, material: dict[str, Any]) -> tuple[bool, str]:
        """Return whether a source material can support numeric/statistical anchors."""
        raw_ingestion = material.get("ingestion")
        ingestion: dict[str, Any] = raw_ingestion if isinstance(raw_ingestion, dict) else {}
        status = str(ingestion.get("status") or "").strip().lower()
        required = bool(ingestion.get("required"))
        if required and status in {"", "pending", "pending_asset_aware", "not_ingested"}:
            return False, (
                f"source material '{material.get('relative_path') or material.get('filename')}' "
                "still requires asset-aware ingestion"
            )
        return True, "source material ready"

    def _path_is_trusted_data_source(self, value: str) -> bool:
        """Return whether a path points to a trusted project data source."""
        text = value.strip()
        if not text:
            return False
        lowered = text.lower()
        if any(hint in lowered for hint in _UNTRUSTED_ANCHOR_SOURCE_HINTS):
            return False

        raw = Path(text)
        candidates = [raw]
        if not raw.is_absolute():
            candidates.extend([self._project_dir / raw, self._project_dir / "data" / raw])

        for candidate in candidates:
            if candidate.suffix.lower() not in _TRUSTED_DATA_SUFFIXES:
                continue
            if candidate.is_file():
                return True
        return False

    def _validate_data_anchor_provenance(
        self,
        *,
        anchors: list[dict[str, Any]],
        artifacts: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        """Validate that numeric/statistical data anchors cite primary evidence.

        This closes the GIGO gap where an agent-generated concept value can be
        copied into data_anchors and then pass because draft and manifest agree.
        A data anchor must cite a ready source-material entry, an asset-aware doc,
        a tracked data artifact, or an existing trusted data file.
        """
        issues: list[dict[str, str]] = []
        if not anchors:
            return issues

        source_by_id, source_by_ref = self._source_material_lookup()
        evidence = _AnchorEvidence(
            source_by_id=source_by_id,
            source_by_ref=source_by_ref,
            artifact_ids={str(a.get("id")) for a in artifacts if a.get("id")},
            artifact_outputs={str(a.get("output_path")) for a in artifacts if a.get("output_path")},
        )
        for anchor in anchors:
            issues.extend(_anchor_issues(self, anchor, evidence))
        return issues
