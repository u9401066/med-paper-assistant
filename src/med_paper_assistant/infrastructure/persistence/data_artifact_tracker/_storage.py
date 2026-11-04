"""Data Artifact Tracker — persistence layer (load/save/normalise) mixin."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import yaml

from ._models import ArtifactType, ContentIntegrityReinspector, logger

if TYPE_CHECKING:

    class _TrackerState:
        """Instance attributes shared by every mixin (declared for type checkers only)."""

        _audit_dir: Path
        _project_dir: Path
        _data_path: Path
        _report_path: Path
        _data: dict[str, Any] | None
        _content_integrity_reinspector: ContentIntegrityReinspector

else:
    # A runtime base class with annotations would add ``__annotations__`` to
    # ``dir(DataArtifactTracker)``; the declarations above are for mypy only.
    _TrackerState = object


class _StorageMixin(_TrackerState):
    """Path normalisation, schema coercion, and YAML/manifest I/O."""

    def _normalize_path(self, path: str | None) -> str | None:
        """Normalize project-relative paths for stable audit matching."""
        if not path:
            return None
        candidate = Path(path)
        if candidate.is_absolute():
            try:
                candidate = candidate.relative_to(self._project_dir)
            except ValueError:
                return candidate.as_posix()
        return candidate.as_posix()

    def _candidate_data_paths(self) -> list[Path]:
        """Return supported data-artifact manifest locations in priority order."""
        return [
            self._data_path,
            self._project_dir / "data-artifacts.yaml",
            self._project_dir / "data-artifacts.yml",
            self._project_dir / "data-artifacts" / "manifest.yaml",
            self._project_dir / "data-artifacts" / "manifest.yml",
        ]

    def _coerce_asset_entry(
        self,
        entry: dict[str, Any],
        artifact_type: ArtifactType,
    ) -> dict[str, Any]:
        """Coerce figure/table/statistics manifest entries into artifact entries."""
        folder = "figures" if artifact_type == "figure" else "tables"
        filename = (
            entry.get("filename")
            or entry.get("file")
            or entry.get("name")
            or entry.get("path")
            or entry.get("asset_path")
            or entry.get("output_path")
        )
        output_path = entry.get("output_path") or entry.get("path") or entry.get("asset_path")
        if not output_path and filename and artifact_type in ("figure", "table"):
            output_path = f"results/{folder}/{Path(str(filename)).name}"

        return {
            "id": str(entry.get("id") or ""),
            "tool_name": entry.get("tool_name") or entry.get("tool") or "manual_manifest",
            "artifact_type": artifact_type,
            "parameters": entry.get("parameters") or {},
            "data_source": entry.get("data_source") or entry.get("source") or entry.get("filename"),
            "output_path": self._normalize_path(str(output_path)) if output_path else None,
            "provenance_code": entry.get("provenance_code") or entry.get("code"),
            "result_summary": entry.get("result_summary")
            or entry.get("caption")
            or entry.get("summary"),
            "timestamp": entry.get("timestamp") or datetime.now().isoformat(),
        }

    def _coerce_loaded_data(self, loaded: dict[str, Any]) -> dict[str, Any]:
        """Normalize legacy/user-authored schemas to the canonical tracker schema."""
        data = dict(loaded)
        artifacts = data.get("artifacts")
        if not isinstance(artifacts, list):
            artifacts = []

        for key, artifact_type in (
            ("figures", "figure"),
            ("tables", "table"),
            ("statistics", "statistics"),
            ("stats", "statistics"),
            ("descriptives", "descriptive"),
        ):
            entries = data.get(key, [])
            if isinstance(entries, dict):
                entries = entries.get("items", [])
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        artifacts.append(
                            self._coerce_asset_entry(entry, cast(ArtifactType, artifact_type))
                        )

        for idx, artifact in enumerate(artifacts, 1):
            artifact.setdefault("id", f"DA-{idx:03d}")
            if artifact.get("output_path"):
                artifact["output_path"] = self._normalize_path(str(artifact["output_path"]))

        data["version"] = data.get("version", 1)
        data["artifacts"] = artifacts
        data["asset_reviews"] = data.get("asset_reviews") or data.get("reviews") or []
        data["content_integrity_receipts"] = data.get("content_integrity_receipts") or []
        data.setdefault("created_at", datetime.now().isoformat())
        return data

    def _load(self) -> dict[str, Any]:
        """Load or initialize tracking data."""
        if self._data is not None:
            return self._data

        for data_path in self._candidate_data_paths():
            if not data_path.is_file():
                continue
            try:
                loaded = yaml.safe_load(data_path.read_text(encoding="utf-8"))
                if loaded is None:
                    loaded = {}
                if not isinstance(loaded, dict):
                    loaded = {}
                self._data = self._coerce_loaded_data(loaded)
                return self._data
            except (yaml.YAMLError, OSError) as e:
                logger.warning("Failed to load data artifact tracker: %s", e)

        self._data = {
            "version": 1,
            "artifacts": [],
            "asset_reviews": [],
            "content_integrity_receipts": [],
            "created_at": datetime.now().isoformat(),
        }
        return self._data

    def _save(self) -> None:
        """Persist tracking data to disk."""
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        data = self._load()
        data["updated_at"] = datetime.now().isoformat()
        self._data_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def _load_manifest(self) -> dict[str, Any]:
        """Load figure/table manifest from supported project locations."""
        manifest_paths = [
            self._project_dir / "results" / "manifest.json",
            self._project_dir / "results" / "manifest.yaml",
            self._project_dir / "results" / "manifest.yml",
            self._project_dir / "data-artifacts" / "manifest.yaml",
            self._project_dir / "data-artifacts" / "manifest.yml",
        ]
        for manifest_path in manifest_paths:
            if not manifest_path.is_file():
                continue
            try:
                text = manifest_path.read_text(encoding="utf-8")
                if manifest_path.suffix.lower() == ".json":
                    loaded = json.loads(text)
                else:
                    loaded = yaml.safe_load(text) or {}
                if isinstance(loaded, dict):
                    return {
                        "figures": loaded.get("figures", []),
                        "tables": loaded.get("tables", []),
                    }
            except (json.JSONDecodeError, yaml.YAMLError, OSError):
                continue

        data = self._load()
        if data.get("figures") or data.get("tables"):
            return {
                "figures": data.get("figures", []),
                "tables": data.get("tables", []),
            }
        return {"figures": [], "tables": []}
