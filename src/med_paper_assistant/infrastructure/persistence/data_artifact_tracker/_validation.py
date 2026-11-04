"""Data Artifact Tracker — cross-reference validation mixin."""

from __future__ import annotations

from typing import Any

from ._anchors import _AnchorMixin
from ._review import _ReviewMixin
from ._validation_checks import (
    check_asset_reviews,
    check_disk_assets,
    check_manifest_files,
    check_provenance_code,
)
from ._validation_draft import build_validation_result, check_draft_references


class _ValidationMixin(_AnchorMixin, _ReviewMixin):
    """Cross-validate artifacts against the manifest, disk, and draft text."""

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

        issues.extend(
            check_disk_assets(
                self._project_dir, artifact_outputs, manifest_figures, manifest_tables
            )
        )
        issues.extend(check_manifest_files(self._project_dir, manifest_figures, manifest_tables))
        issues.extend(check_provenance_code(artifacts))
        issues.extend(check_asset_reviews(self, artifacts))

        if draft_content:
            issues.extend(check_draft_references(self, draft_content, manifest, artifacts))

        return build_validation_result(
            issues, artifacts, data_anchors, manifest_figures, manifest_tables
        )
