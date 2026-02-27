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
from typing import Any, Literal

import structlog
import yaml

logger = structlog.get_logger()

ArtifactType = Literal["figure", "table", "statistics", "descriptive"]


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

    def _load(self) -> dict[str, Any]:
        """Load or initialize tracking data."""
        if self._data is not None:
            return self._data

        if self._data_path.is_file():
            try:
                loaded = yaml.safe_load(self._data_path.read_text(encoding="utf-8"))
                if loaded is None:
                    loaded = {}
                self._data = loaded
                return loaded
            except (yaml.YAMLError, OSError) as e:
                logger.warning("Failed to load data artifact tracker: %s", e)

        self._data = {
            "version": 1,
            "artifacts": [],
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
            "output_path": output_path,
            "provenance_code": provenance_code,
            "result_summary": result_summary,
            "timestamp": datetime.now().isoformat(),
        }
        data["artifacts"].append(entry)
        self._save()
        logger.info("Recorded data artifact: %s (%s via %s)", entry["id"], artifact_type, tool_name)
        return entry

    def get_artifacts(self, artifact_type: str | None = None) -> list[dict[str, Any]]:
        """Get all artifacts, optionally filtered by type."""
        data = self._load()
        artifacts = data.get("artifacts", [])
        if artifact_type:
            artifacts = [a for a in artifacts if a.get("artifact_type") == artifact_type]
        return artifacts

    def get_artifact_by_output(self, output_path: str) -> dict[str, Any] | None:
        """Find artifact by output path."""
        for a in self.get_artifacts():
            if a.get("output_path") == output_path:
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

        report_text = "\n".join(lines)

        # Save report
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._report_path.write_text(report_text, encoding="utf-8")

        return report_text

    def _load_manifest(self) -> dict[str, Any]:
        """Load manifest.json from results/."""
        manifest_path = self._project_dir / "results" / "manifest.json"
        if manifest_path.is_file():
            try:
                return json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"figures": [], "tables": []}
