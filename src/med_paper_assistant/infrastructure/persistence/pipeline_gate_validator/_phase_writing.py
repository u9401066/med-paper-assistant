"""Phase 5 gate: manuscript draft, data provenance, planned assets and section approval."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from med_paper_assistant.infrastructure.persistence.data_artifact_tracker import DataArtifactTracker

from ._assets import AssetPlanMixin
from ._io import UNREADABLE, read_json_value
from ._types import GateCheck, GateResult

_REQUIRED_SECTIONS = ["Abstract", "Introduction", "Methods", "Results", "Discussion"]
_APPROVAL_DESCRIPTION = "All required sections must have a recorded approval"


def _section_checks(content: str) -> list[GateCheck]:
    checks = []
    for section in _REQUIRED_SECTIONS:
        found = f"## {section}" in content or f"# {section}" in content
        checks.append(
            GateCheck(
                name=f"section:{section}",
                description=f"{section} section present",
                passed=found,
                details="found" if found else "MISSING",
            )
        )
    return checks


def _provenance_checks(content: str, tracker: DataArtifactTracker) -> list[GateCheck]:
    # If manuscript references Figure N or Table N, data-artifacts.yaml must exist
    has_fig_refs = bool(re.search(r"Figure\s+\d+", content, re.IGNORECASE))
    has_tbl_refs = bool(re.search(r"Table\s+\d+", content, re.IGNORECASE))
    has_stat_claims = bool(
        re.search(r"p\s*[<>=]\s*0\.\d+|statistically\s+significant", content, re.IGNORECASE)
    )
    if not (has_fig_refs or has_tbl_refs or has_stat_claims):
        return []

    artifacts = tracker.get_artifacts()
    artifact_count = len(artifacts)
    da_has_data = artifact_count > 0
    return [
        GateCheck(
            name="data-artifacts:provenance",
            description="Data artifacts tracked with provenance (validate_data_artifacts required)",
            passed=da_has_data,
            details=(
                f"{artifact_count} artifacts tracked"
                if da_has_data
                else "MISSING data artifact tracking records — analysis tools must be used with provenance tracking"
            ),
        )
    ]


def _approval_check(passed: bool, details: str) -> GateCheck:
    return GateCheck(
        name="section_approval",
        description=_APPROVAL_DESCRIPTION,
        passed=passed,
        details=details,
    )


def _evaluate_section_progress(ckpt: Any, present: list[str]) -> GateCheck:
    section_progress = ckpt.get("section_progress", {})

    missing_entries = [name for name in present if name not in section_progress]
    unapproved = [
        name
        for name in present
        if section_progress.get(name, {}).get("approval_status", "pending") != "approved"
    ]

    if missing_entries:
        return _approval_check(False, f"missing approval entries: {', '.join(missing_entries)}")
    if unapproved:
        return _approval_check(False, f"unapproved: {', '.join(unapproved)}")
    return _approval_check(True, "all required sections approved")


def _section_approval_check(checkpoint_path: Path, present: list[str]) -> GateCheck:
    # Hard gate: autopilot and manual review must both leave an approve_section() trail.
    if not checkpoint_path.is_file():
        return _approval_check(
            False, "MISSING checkpoint.json — call approve_section() for each required section"
        )

    ckpt = read_json_value(checkpoint_path)
    if ckpt is UNREADABLE:
        return _approval_check(
            False,
            "checkpoint.json unreadable — call approve_section() again to rebuild approval state",
        )
    return _evaluate_section_progress(ckpt, present)


def _asset_registered_check(
    asset: dict[str, Any], kind: str, manifest_entry: dict[str, Any] | None
) -> GateCheck:
    return GateCheck(
        name=f"asset-plan:{asset['id']}:registered",
        description=(
            f"Required planned {kind} for {asset['section']} is registered in results/manifest.json"
        ),
        passed=manifest_entry is not None,
        details=(
            f"matched {kind} {manifest_entry.get('number')} ({manifest_entry.get('filename')})"
            if manifest_entry is not None
            else "MISSING — run insert_figure/insert_table for this planned asset"
        ),
    )


def _asset_placed_check(
    asset: dict[str, Any],
    kind: str,
    manifest_entry: dict[str, Any],
    section_content: str,
) -> GateCheck:
    ref_label = f"{kind.title()} {manifest_entry.get('number')}".strip()
    placed = bool(section_content) and (
        ref_label.lower() in section_content.lower()
        or manifest_entry.get("filename", "").lower() in section_content.lower()
        or manifest_entry.get("caption", "").lower() in section_content.lower()
    )
    return GateCheck(
        name=f"asset-plan:{asset['id']}:placed",
        description=f"Required planned {kind} is referenced or embedded inside {asset['section']}",
        passed=placed,
        details=(
            f"found {ref_label or manifest_entry.get('filename') or manifest_entry.get('caption')} in {asset['section']}"
            if placed
            else f"MISSING from {asset['section']} section"
        ),
    )


class WritingPhaseMixin(AssetPlanMixin):
    """Validation of Phase 5 (writing)."""

    def _validate_phase_5(self) -> GateResult:
        """Phase 5: manuscript.md exists with all required sections + data artifact provenance."""
        checks = []

        ms = self._drafts_dir / "manuscript.md"
        checks.append(
            GateCheck(
                name="manuscript.md",
                description="Manuscript draft exists",
                passed=ms.is_file(),
                details="exists" if ms.is_file() else "MISSING",
            )
        )

        if ms.is_file():
            content = ms.read_text(encoding="utf-8")
            tracker = DataArtifactTracker(self._audit_dir, self._project_dir)
            checks.extend(_section_checks(content))
            checks.extend(_provenance_checks(content, tracker))
            checks.extend(self._planned_asset_checks(content, tracker))

        checkpoint_path = self._audit_dir / "checkpoint.json"
        required_sections_present = []
        if ms.is_file():
            content = ms.read_text(encoding="utf-8")
            required_sections_present = [
                section
                for section in _REQUIRED_SECTIONS
                if f"## {section}" in content or f"# {section}" in content
            ]

        if required_sections_present:
            checks.append(_section_approval_check(checkpoint_path, required_sections_present))

        return GateResult(phase=5, phase_name="Writing", checks=checks, passed=False)

    def _planned_asset_checks(self, content: str, tracker: DataArtifactTracker) -> list[GateCheck]:
        plan = self._load_manuscript_plan()
        planned_assets = [
            asset
            for asset in self._normalize_planned_assets(plan)
            if asset.get("required") and self._asset_kind(asset.get("type", "")) is not None
        ]
        manifest_entries = self._load_manifest_entries()

        checks: list[GateCheck] = []
        for asset in planned_assets:
            kind = self._asset_kind(asset["type"])
            if kind is None:
                continue
            checks.extend(
                self._single_asset_checks(asset, kind, content, manifest_entries, tracker)
            )
        return checks

    def _single_asset_checks(
        self,
        asset: dict[str, Any],
        kind: str,
        content: str,
        manifest_entries: list[dict[str, Any]],
        tracker: DataArtifactTracker,
    ) -> list[GateCheck]:
        asset_id = asset["id"]
        manifest_entry = self._match_manifest_asset(asset, manifest_entries)

        checks = [_asset_registered_check(asset, kind, manifest_entry)]
        if manifest_entry is None:
            return checks

        section_content = self._get_section_content(content, asset["section"])
        checks.append(_asset_placed_check(asset, kind, manifest_entry, section_content))

        if kind == "figure":
            exportable = self._has_exportable_figure(manifest_entry.get("filename", ""))
            checks.append(
                GateCheck(
                    name=f"asset-plan:{asset_id}:exportable",
                    description="Figure has a renderable PNG/SVG/JPG/TIFF asset for export",
                    passed=exportable,
                    details=(
                        "renderable asset found"
                        if exportable
                        else "MISSING rendered companion asset for DOCX/PDF export"
                    ),
                )
            )

        checks.append(self._asset_review_check(asset_id, kind, manifest_entry, tracker))
        return checks

    @staticmethod
    def _asset_review_check(
        asset_id: str,
        kind: str,
        manifest_entry: dict[str, Any],
        tracker: DataArtifactTracker,
    ) -> GateCheck:
        asset_folder = "figures" if kind == "figure" else "tables"
        asset_rel_path = f"results/{asset_folder}/{manifest_entry.get('filename', '')}"
        review_ok, review_detail = tracker.review_satisfies_caption(
            asset_rel_path,
            str(manifest_entry.get("caption", "")),
            asset_type=kind,
        )
        return GateCheck(
            name=f"asset-plan:{asset_id}:reviewed",
            description=f"Required planned {kind} caption is backed by an asset review receipt",
            passed=review_ok,
            details=review_detail,
        )
