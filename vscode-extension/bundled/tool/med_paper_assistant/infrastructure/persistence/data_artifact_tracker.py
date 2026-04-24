"""
Data Artifact Tracker — Track data analysis outputs with provenance.

Records every data analysis tool call (create_plot, run_statistical_test,
generate_table_one, analyze_dataset) with full parameters, output paths,
and reproducibility code. Cross-validates against manifest.json and draft text.

Architecture:
  Infrastructure layer service. Called after each data analysis tool call.
  Persists to `.audit/data-artifacts.yaml` and generates `.md` reports.
  Consumed by validate_data_artifacts MCP tool and Phase 5/6 gate validators.

Design rationale (CONSTITUTION §22):
  - Auditable: Every data artifact has a provenance trail
  - Reproducible: Parameters + code saved for each output
  - Self-validating: Cross-reference checks between artifacts ↔ manifest ↔ draft
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

import structlog
import yaml

logger = structlog.get_logger()

ArtifactType = Literal["figure", "table", "statistics", "descriptive"]
_TRUSTED_DATA_SUFFIXES = {".csv", ".tsv", ".xlsx", ".xls", ".json", ".yaml", ".yml", ".sav", ".dta"}
_UNTRUSTED_ANCHOR_SOURCE_HINTS = {
    "agent",
    "assumption",
    "concept",
    "draft",
    "estimated",
    "generated",
    "inferred",
    "llm",
    "summary",
}


class DataArtifactTracker:
    """
    Track data analysis artifacts with provenance and reproducibility code.

    Usage:
        tracker = DataArtifactTracker(audit_dir, project_dir)
        tracker.record_artifact(
            tool_name="create_plot",
            artifact_type="figure",
            parameters={"filename": "data.csv", "plot_type": "boxplot", ...},
            output_path="results/figures/boxplot_age.png",
            data_source="data.csv",
            provenance_code="...",
        )
        report = tracker.generate_report()
        validation = tracker.validate_cross_references(draft_content)
    """

    DATA_FILE = "data-artifacts.yaml"
    REPORT_FILE = "data-artifacts.md"

    def __init__(self, audit_dir: str | Path, project_dir: str | Path) -> None:
        self._audit_dir = Path(audit_dir)
        self._project_dir = Path(project_dir)
        self._data_path = self._audit_dir / self.DATA_FILE
        self._report_path = self._audit_dir / self.REPORT_FILE
        self._data: dict[str, Any] | None = None

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
            "result_summary": entry.get("result_summary") or entry.get("caption") or entry.get("summary"),
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
            "created_at": datetime.now().isoformat(),
        }
        return self._data

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

    def _source_material_lookup(self) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
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
        ingestion = material.get("ingestion") if isinstance(material.get("ingestion"), dict) else {}
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
        artifact_ids = {str(a.get("id")) for a in artifacts if a.get("id")}
        artifact_outputs = {str(a.get("output_path")) for a in artifacts if a.get("output_path")}

        for anchor in anchors:
            name = str(
                anchor.get("name")
                or anchor.get("id")
                or anchor.get("key")
                or anchor.get("label")
                or "unnamed"
            )

            explicit_source = self._anchor_field(
                anchor,
                "source",
                "source_type",
                "data_source",
                "source_file",
                "source_path",
            )
            if explicit_source and any(
                hint in str(explicit_source).lower() for hint in _UNTRUSTED_ANCHOR_SOURCE_HINTS
            ):
                issues.append(
                    {
                        "severity": "CRITICAL",
                        "category": "data_anchor_untrusted_source",
                        "message": (
                            f"Data anchor '{name}' cites an agent/generated source "
                            f"('{explicit_source}'); anchors must cite primary data, source-material, "
                            "asset-aware, or tracked analysis provenance"
                        ),
                    }
                )
                continue

            asset_doc = self._anchor_field(
                anchor,
                "asset_aware_doc_id",
                "assetAwareDocId",
                "asset_doc_id",
                "doc_id",
            )
            if asset_doc:
                continue

            artifact_ref = self._anchor_field(
                anchor,
                "data_artifact_id",
                "artifact_id",
                "artifact",
                "analysis_artifact_id",
            )
            if artifact_ref and str(artifact_ref) in artifact_ids:
                continue

            output_ref = self._anchor_field(anchor, "output_path", "artifact_output_path")
            if output_ref and str(output_ref) in artifact_outputs:
                continue

            source_material_id = self._anchor_field(
                anchor,
                "source_material_id",
                "sourceMaterialId",
                "material_id",
            )
            if source_material_id:
                material = source_by_id.get(str(source_material_id))
                if material:
                    ready, detail = self._material_ready_for_anchor(material)
                    if ready:
                        continue
                    issues.append(
                        {
                            "severity": "CRITICAL",
                            "category": "data_anchor_uningested_source",
                            "message": f"Data anchor '{name}' cites {detail}",
                        }
                    )
                    continue

            source_ref = self._anchor_field(
                anchor,
                "source_material_path",
                "source_file",
                "source_path",
                "data_source",
                "file",
            )
            if source_ref:
                material = source_by_ref.get(str(source_ref)) or source_by_ref.get(Path(str(source_ref)).name)
                if material:
                    ready, detail = self._material_ready_for_anchor(material)
                    if ready:
                        continue
                    issues.append(
                        {
                            "severity": "CRITICAL",
                            "category": "data_anchor_uningested_source",
                            "message": f"Data anchor '{name}' cites {detail}",
                        }
                    )
                    continue
                if self._path_is_trusted_data_source(str(source_ref)):
                    continue

            issues.append(
                {
                    "severity": "CRITICAL",
                    "category": "data_anchor_unverified",
                    "message": (
                        f"Data anchor '{name}' lacks primary-source provenance; include "
                        "source_material_id for an ingested/ready source material, "
                        "asset_aware_doc_id, data_artifact_id, or a trusted data_source file"
                    ),
                }
            )

        return issues

    def _save(self) -> None:
        """Persist tracking data to disk."""
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        data = self._load()
        data["updated_at"] = datetime.now().isoformat()
        self._data_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def record_artifact(
        self,
        tool_name: str,
        artifact_type: ArtifactType,
        parameters: dict[str, Any],
        output_path: str | None = None,
        data_source: str | None = None,
        provenance_code: str | None = None,
        result_summary: str | None = None,
    ) -> dict[str, Any]:
        """
        Record a data analysis artifact.

        Args:
            tool_name: MCP tool that produced it (e.g., "create_plot")
            artifact_type: "figure", "table", "statistics", or "descriptive"
            parameters: Full parameters passed to the tool
            output_path: Path to output file (relative to project dir), if any
            data_source: Source data filename
            provenance_code: Python code to reproduce the output
            result_summary: Brief summary of the result (for ephemeral outputs like stats)

        Returns:
            The recorded artifact entry dict.
        """
        data = self._load()
        entry = {
            "id": f"DA-{len(data['artifacts']) + 1:03d}",
            "tool_name": tool_name,
            "artifact_type": artifact_type,
            "parameters": parameters,
            "data_source": data_source,
            "output_path": self._normalize_path(output_path),
            "provenance_code": provenance_code,
            "result_summary": result_summary,
            "timestamp": datetime.now().isoformat(),
        }
        data["artifacts"].append(entry)
        self._save()
        logger.info("Recorded data artifact: %s (%s via %s)", entry["id"], artifact_type, tool_name)
        return entry

    def record_asset_review(
        self,
        asset_type: Literal["figure", "table"],
        asset_path: str,
        observations: list[str],
        rationale: str,
        proposed_caption: str,
        evidence_excerpt: str | None = None,
    ) -> dict[str, Any]:
        """Record an auditable asset review receipt before insertion/caption writing.

        This is the closest code-enforced proxy for "agent truly looked at it":
        the agent must produce structured observations tied to a specific asset
        before insert_figure/insert_table can proceed.
        """
        data = self._load()
        normalized_path = self._normalize_path(asset_path)
        reviews: list[dict[str, Any]] = data.setdefault("asset_reviews", [])

        entry = {
            "id": f"AR-{len(reviews) + 1:03d}",
            "asset_type": asset_type,
            "asset_path": normalized_path,
            "observations": [o.strip() for o in observations if o and o.strip()],
            "rationale": rationale.strip(),
            "proposed_caption": proposed_caption.strip(),
            "evidence_excerpt": (evidence_excerpt or "").strip(),
            "timestamp": datetime.now().isoformat(),
        }
        reviews.append(entry)
        self._save()
        logger.info("Recorded asset review: %s (%s %s)", entry["id"], asset_type, normalized_path)
        return entry

    def get_asset_review(
        self,
        asset_path: str,
        asset_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Return the latest review receipt for a given asset path."""
        normalized_path = self._normalize_path(asset_path)
        data = self._load()
        reviews = data.get("asset_reviews", [])
        matches = [
            r
            for r in reviews
            if r.get("asset_path") == normalized_path
            and (asset_type is None or r.get("asset_type") == asset_type)
        ]
        if not matches:
            return None
        return sorted(matches, key=lambda r: r.get("timestamp", ""))[-1]

    @staticmethod
    def _normalize_caption(text: str) -> str:
        """Normalize caption for comparison: lowercase, strip punctuation/whitespace."""
        import string

        return text.strip().rstrip(string.punctuation).strip().lower()

    def review_satisfies_caption(
        self,
        asset_path: str,
        proposed_caption: str,
        asset_type: str,
    ) -> tuple[bool, str]:
        """Validate that an asset has a review receipt aligned with the caption."""
        review = self.get_asset_review(asset_path, asset_type=asset_type)
        if review is None:
            return False, "no asset review receipt found"

        observations = review.get("observations", [])
        if len(observations) < 2:
            return False, "asset review must contain at least 2 observations"

        if not review.get("rationale"):
            return False, "asset review rationale missing"

        reviewed_caption = str(review.get("proposed_caption", "")).strip()
        if reviewed_caption and (
            self._normalize_caption(reviewed_caption) != self._normalize_caption(proposed_caption)
        ):
            return False, "caption differs from reviewed proposed_caption"

        return True, review.get("id", "asset review receipt")

    def get_artifacts(self, artifact_type: str | None = None) -> list[dict[str, Any]]:
        """Get all artifacts, optionally filtered by type."""
        data = self._load()
        artifacts = data.get("artifacts", [])
        if artifact_type:
            artifacts = [a for a in artifacts if a.get("artifact_type") == artifact_type]
        return artifacts

    def get_artifact_by_output(self, output_path: str) -> dict[str, Any] | None:
        """Find artifact by output path."""
        normalized_output = self._normalize_path(output_path)
        for a in self.get_artifacts():
            if self._normalize_path(a.get("output_path")) == normalized_output:
                return a
        return None

    def validate_cross_references(self, draft_content: str | None = None) -> dict[str, Any]:
        """
        Validate cross-references between data artifacts, manifest, and draft.

        Checks:
        1. Every file in results/figures/ has a provenance entry (data-artifacts.yaml)
        2. Every file in results/figures/ has a manifest entry (manifest.json)
        3. Every Figure N / Table N in draft text maps to a manifest entry
        4. Every manifest entry has a corresponding file on disk
        5. Every figure/table artifact has provenance_code
        6. Statistical results referenced in text are backed by artifact entries

        Returns:
            Dict with "passed", "issues" (list of dicts with severity/category/message),
            and summary counts.
        """
        issues: list[dict[str, str]] = []

        # Load manifest
        manifest = self._load_manifest()
        manifest_figures = {e.get("filename"): e for e in manifest.get("figures", [])}
        manifest_tables = {e.get("filename"): e for e in manifest.get("tables", [])}

        # Get tracked artifacts
        artifacts = self.get_artifacts()
        artifact_outputs = {a.get("output_path") for a in artifacts if a.get("output_path")}
        data_anchors = self._coerce_data_anchor_entries(self._load())
        issues.extend(
            self._validate_data_anchor_provenance(anchors=data_anchors, artifacts=artifacts)
        )

        # Check 1: Files in results/figures/ have provenance
        figures_dir = self._project_dir / "results" / "figures"
        if figures_dir.is_dir():
            for f in figures_dir.iterdir():
                if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".tiff"}:
                    rel_path = f"results/figures/{f.name}"
                    if rel_path not in artifact_outputs:
                        issues.append(
                            {
                                "severity": "WARNING",
                                "category": "provenance_missing",
                                "message": f"Figure '{f.name}' has no provenance in data-artifacts.yaml",
                            }
                        )
                    if f.name not in manifest_figures:
                        issues.append(
                            {
                                "severity": "CRITICAL",
                                "category": "manifest_missing",
                                "message": f"Figure '{f.name}' exists on disk but not in manifest.json",
                            }
                        )

        # Check 2: Files in results/tables/ have provenance
        tables_dir = self._project_dir / "results" / "tables"
        if tables_dir.is_dir():
            for f in tables_dir.iterdir():
                if f.is_file() and f.suffix.lower() in {".md", ".csv", ".xlsx", ".html"}:
                    rel_path = f"results/tables/{f.name}"
                    if rel_path not in artifact_outputs:
                        issues.append(
                            {
                                "severity": "WARNING",
                                "category": "provenance_missing",
                                "message": f"Table '{f.name}' has no provenance in data-artifacts.yaml",
                            }
                        )
                    if f.name not in manifest_tables:
                        issues.append(
                            {
                                "severity": "WARNING",
                                "category": "manifest_missing",
                                "message": f"Table '{f.name}' exists on disk but not in manifest.json",
                            }
                        )

        # Check 3: Manifest entries have corresponding files
        for fname, entry in manifest_figures.items():
            fpath = (
                figures_dir / fname
                if figures_dir.is_dir()
                else self._project_dir / "results" / "figures" / fname
            )
            if not fpath.is_file():
                issues.append(
                    {
                        "severity": "CRITICAL",
                        "category": "phantom_file",
                        "message": f"Manifest lists Figure {entry.get('number')} ('{fname}') but file does not exist",
                    }
                )

        for fname, entry in manifest_tables.items():
            fpath = (
                tables_dir / fname
                if tables_dir.is_dir()
                else self._project_dir / "results" / "tables" / fname
            )
            if not fpath.is_file():
                issues.append(
                    {
                        "severity": "CRITICAL",
                        "category": "phantom_file",
                        "message": f"Manifest lists Table {entry.get('number')} ('{fname}') but file does not exist",
                    }
                )

        # Check 4: Figure/Table artifacts have provenance code
        for a in artifacts:
            if a.get("artifact_type") in ("figure", "table") and not a.get("provenance_code"):
                issues.append(
                    {
                        "severity": "WARNING",
                        "category": "no_provenance_code",
                        "message": f"Artifact {a.get('id')} ({a.get('tool_name')}) has no reproducibility code",
                    }
                )

        # Check 4b: Figure/Table artifacts have review receipts before insertion/captioning
        for a in artifacts:
            if a.get("artifact_type") in ("figure", "table") and a.get("output_path"):
                review = self.get_asset_review(
                    str(a.get("output_path")),
                    asset_type=str(a.get("artifact_type")),
                )
                if not review:
                    issues.append(
                        {
                            "severity": "CRITICAL",
                            "category": "asset_review_missing",
                            "message": (
                                f"{str(a.get('artifact_type')).title()} artifact {a.get('output_path')} has no asset review receipt; "
                                "call review_asset_for_insertion() before inserting or captioning"
                            ),
                        }
                    )
                elif len(review.get("observations", [])) < 2 or not review.get("rationale"):
                    issues.append(
                        {
                            "severity": "CRITICAL",
                            "category": "asset_review_incomplete",
                            "message": (
                                f"Asset review for {a.get('output_path')} is incomplete; "
                                "need >=2 observations and a rationale"
                            ),
                        }
                    )

        # Check 5: Draft cross-references (if draft content provided)
        if draft_content:
            # Find Figure N and Table N references in text
            fig_refs = set(re.findall(r"Figure\s+(\d+)", draft_content, re.IGNORECASE))
            tbl_refs = set(re.findall(r"Table\s+(\d+)", draft_content, re.IGNORECASE))

            manifest_fig_nums = {str(e.get("number")) for e in manifest.get("figures", [])}
            manifest_tbl_nums = {str(e.get("number")) for e in manifest.get("tables", [])}

            # Phantom references (in text but not in manifest)
            for ref in fig_refs - manifest_fig_nums:
                issues.append(
                    {
                        "severity": "CRITICAL",
                        "category": "phantom_reference",
                        "message": f"Draft references 'Figure {ref}' but no such entry in manifest",
                    }
                )

            # Manifest entries also need review receipts for caption trustworthiness
            for entry in manifest.get("figures", []):
                fname = entry.get("filename")
                if not fname:
                    continue
                asset_path = f"results/figures/{fname}"
                ok, detail = self.review_satisfies_caption(
                    asset_path,
                    str(entry.get("caption", "")),
                    asset_type="figure",
                )
                if not ok:
                    issues.append(
                        {
                            "severity": "CRITICAL",
                            "category": "caption_unreviewed",
                            "message": f"Figure {entry.get('number')} caption is not backed by a matching review receipt: {detail}",
                        }
                    )

            for entry in manifest.get("tables", []):
                fname = entry.get("filename")
                if not fname:
                    continue
                asset_path = f"results/tables/{fname}"
                ok, detail = self.review_satisfies_caption(
                    asset_path,
                    str(entry.get("caption", "")),
                    asset_type="table",
                )
                if not ok:
                    issues.append(
                        {
                            "severity": "CRITICAL",
                            "category": "caption_unreviewed",
                            "message": f"Table {entry.get('number')} caption is not backed by a matching review receipt: {detail}",
                        }
                    )

            for ref in tbl_refs - manifest_tbl_nums:
                issues.append(
                    {
                        "severity": "CRITICAL",
                        "category": "phantom_reference",
                        "message": f"Draft references 'Table {ref}' but no such entry in manifest",
                    }
                )

            # Orphan assets (in manifest but not referenced in text)
            for num in manifest_fig_nums - fig_refs:
                issues.append(
                    {
                        "severity": "WARNING",
                        "category": "orphan_asset",
                        "message": f"Figure {num} is in manifest but never referenced in draft",
                    }
                )

            for num in manifest_tbl_nums - tbl_refs:
                issues.append(
                    {
                        "severity": "WARNING",
                        "category": "orphan_asset",
                        "message": f"Table {num} is in manifest but never referenced in draft",
                    }
                )

            # Check statistical claims have backing artifacts
            stat_patterns = [
                r"p\s*[<>=]\s*0\.\d+",
                r"p\s*-\s*value",
                r"statistically\s+significant",
                r"CI\s*[:\s]*\d+",
                r"odds\s+ratio",
                r"hazard\s+ratio",
                r"relative\s+risk",
            ]
            has_stat_claims = any(
                re.search(pat, draft_content, re.IGNORECASE) for pat in stat_patterns
            )
            stat_artifacts = [a for a in artifacts if a.get("artifact_type") == "statistics"]
            if has_stat_claims and not stat_artifacts:
                issues.append(
                    {
                        "severity": "CRITICAL",
                        "category": "unverified_stats",
                        "message": "Draft contains statistical claims but no statistical test artifacts recorded",
                    }
                )

        # Summary
        critical_count = sum(1 for i in issues if i["severity"] == "CRITICAL")
        warning_count = sum(1 for i in issues if i["severity"] == "WARNING")

        return {
            "passed": critical_count == 0,
            "issues": issues,
            "summary": {
                "total_artifacts": len(artifacts),
                "figures_tracked": len([a for a in artifacts if a["artifact_type"] == "figure"]),
                "tables_tracked": len([a for a in artifacts if a["artifact_type"] == "table"]),
                "stats_tracked": len([a for a in artifacts if a["artifact_type"] == "statistics"]),
                "data_anchors": len(data_anchors),
                "critical_issues": critical_count,
                "warning_issues": warning_count,
                "manifest_figures": len(manifest_figures),
                "manifest_tables": len(manifest_tables),
            },
        }

    def generate_report(self) -> str:
        """Generate a markdown report of all tracked artifacts."""
        data = self._load()
        artifacts = data.get("artifacts", [])

        lines = [
            "# Data Artifact Provenance Report",
            "",
            f"**Generated**: {datetime.now().isoformat()}",
            f"**Total Artifacts**: {len(artifacts)}",
            "",
        ]

        # Group by type
        by_type: dict[str, list[dict[str, Any]]] = {}
        for a in artifacts:
            t = a.get("artifact_type", "unknown")
            by_type.setdefault(t, []).append(a)

        for atype, items in by_type.items():
            lines.append(f"## {atype.capitalize()}s ({len(items)})")
            lines.append("")
            for item in items:
                lines.append(f"### {item.get('id')} — {item.get('tool_name')}")
                lines.append(f"- **Data Source**: {item.get('data_source', 'N/A')}")
                lines.append(f"- **Output**: {item.get('output_path', 'ephemeral')}")
                lines.append(f"- **Timestamp**: {item.get('timestamp')}")
                if item.get("parameters"):
                    lines.append(
                        f"- **Parameters**: `{json.dumps(item['parameters'], ensure_ascii=False)}`"
                    )
                if item.get("result_summary"):
                    lines.append(f"- **Result**: {item['result_summary']}")
                if item.get("provenance_code"):
                    lines.append("- **Reproducibility Code**:")
                    lines.append("```python")
                    lines.append(item["provenance_code"])
                    lines.append("```")
                lines.append("")

        reviews = data.get("asset_reviews", [])
        if reviews:
            lines.append(f"## Asset Reviews ({len(reviews)})")
            lines.append("")
            for review in reviews:
                lines.append(
                    f"### {review.get('id')} — {review.get('asset_type')} {review.get('asset_path')}"
                )
                lines.append(f"- **Timestamp**: {review.get('timestamp')}")
                lines.append(f"- **Proposed Caption**: {review.get('proposed_caption', '')}")
                lines.append(f"- **Rationale**: {review.get('rationale', '')}")
                if review.get("evidence_excerpt"):
                    lines.append(f"- **Evidence Excerpt**: {review.get('evidence_excerpt')}")
                observations = review.get("observations", [])
                if observations:
                    lines.append("- **Observations**:")
                    for observation in observations:
                        lines.append(f"  - {observation}")
                lines.append("")

        report_text = "\n".join(lines)

        # Save report
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._report_path.write_text(report_text, encoding="utf-8")

        return report_text

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
