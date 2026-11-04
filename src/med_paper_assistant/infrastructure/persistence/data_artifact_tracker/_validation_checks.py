"""Data Artifact Tracker — on-disk, manifest, and review checks for cross-reference validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._review import _ReviewMixin

_FIGURE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".tiff"}
_TABLE_SUFFIXES = {".md", ".csv", ".xlsx", ".html"}


def issue(severity: str, category: str, message: str) -> dict[str, str]:
    return {"severity": severity, "category": category, "message": message}


def _scan_asset_dir(
    directory: Path,
    rel_prefix: str,
    label: str,
    suffixes: set[str],
    artifact_outputs: set[Any],
    manifest_entries: dict[Any, Any],
    manifest_severity: str,
) -> list[dict[str, str]]:
    """Report on-disk assets lacking provenance or a manifest entry."""
    issues: list[dict[str, str]] = []
    if not directory.is_dir():
        return issues
    for f in directory.iterdir():
        if f.is_file() and f.suffix.lower() in suffixes:
            rel_path = f"{rel_prefix}/{f.name}"
            if rel_path not in artifact_outputs:
                issues.append(
                    issue(
                        "WARNING",
                        "provenance_missing",
                        f"{label} '{f.name}' has no provenance in data-artifacts.yaml",
                    )
                )
            if f.name not in manifest_entries:
                issues.append(
                    issue(
                        manifest_severity,
                        "manifest_missing",
                        f"{label} '{f.name}' exists on disk but not in manifest.json",
                    )
                )
    return issues


def check_disk_assets(
    project_dir: Path,
    artifact_outputs: set[Any],
    manifest_figures: dict[Any, Any],
    manifest_tables: dict[Any, Any],
) -> list[dict[str, str]]:
    """Check 1-2: files in results/figures/ and results/tables/ have provenance."""
    issues = _scan_asset_dir(
        project_dir / "results" / "figures",
        "results/figures",
        "Figure",
        _FIGURE_SUFFIXES,
        artifact_outputs,
        manifest_figures,
        "CRITICAL",
    )
    issues.extend(
        _scan_asset_dir(
            project_dir / "results" / "tables",
            "results/tables",
            "Table",
            _TABLE_SUFFIXES,
            artifact_outputs,
            manifest_tables,
            "WARNING",
        )
    )
    return issues


def check_manifest_files(
    project_dir: Path,
    manifest_figures: dict[Any, Any],
    manifest_tables: dict[Any, Any],
) -> list[dict[str, str]]:
    """Check 3: manifest entries have corresponding files."""
    issues: list[dict[str, str]] = []
    for folder, label, entries in (
        ("figures", "Figure", manifest_figures),
        ("tables", "Table", manifest_tables),
    ):
        directory = project_dir / "results" / folder
        for fname, entry in entries.items():
            if not (directory / fname).is_file():
                issues.append(
                    issue(
                        "CRITICAL",
                        "phantom_file",
                        f"Manifest lists {label} {entry.get('number')} ('{fname}') but file does not exist",
                    )
                )
    return issues


def check_provenance_code(artifacts: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Check 4: figure/table artifacts have provenance code."""
    return [
        issue(
            "WARNING",
            "no_provenance_code",
            f"Artifact {a.get('id')} ({a.get('tool_name')}) has no reproducibility code",
        )
        for a in artifacts
        if a.get("artifact_type") in ("figure", "table") and not a.get("provenance_code")
    ]


def _asset_review_issue(tracker: _ReviewMixin, artifact: dict[str, Any]) -> dict[str, str] | None:
    review = tracker.get_asset_review(
        str(artifact.get("output_path")),
        asset_type=str(artifact.get("artifact_type")),
    )
    if not review:
        return issue(
            "CRITICAL",
            "asset_review_missing",
            (
                f"{str(artifact.get('artifact_type')).title()} artifact {artifact.get('output_path')} has no asset review receipt; "
                "call review_asset_for_insertion() before inserting or captioning"
            ),
        )
    if len(review.get("observations", [])) < 2 or not review.get("rationale"):
        return issue(
            "CRITICAL",
            "asset_review_incomplete",
            (
                f"Asset review for {artifact.get('output_path')} is incomplete; "
                "need >=2 observations and a rationale"
            ),
        )
    integrity_ok, integrity_detail = tracker._integrity_receipt_satisfies_review(review)
    if not integrity_ok:
        return issue(
            "CRITICAL",
            "content_integrity_gate",
            (
                f"Content integrity gate failed for {artifact.get('output_path')}: "
                f"{integrity_detail}"
            ),
        )
    return None


def check_asset_reviews(
    tracker: _ReviewMixin, artifacts: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """Check 4b: figure/table artifacts have review receipts before insertion/captioning."""
    issues: list[dict[str, str]] = []
    for a in artifacts:
        if a.get("artifact_type") in ("figure", "table") and a.get("output_path"):
            found = _asset_review_issue(tracker, a)
            if found is not None:
                issues.append(found)
    return issues
