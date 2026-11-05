"""Application service for read-only content-integrity inspection."""

from __future__ import annotations

from pathlib import Path

from med_paper_assistant.domain.services.content_integrity_inspection import (
    ProvenanceInspectorPort,
    RemovalPackageInspectorPort,
    VisibleWatermarkInspectorPort,
    inspect_content_integrity,
)
from med_paper_assistant.domain.value_objects.content_integrity import ContentIntegrityReceipt

__all__ = [
    "ContentIntegrityInspector",
    "ProvenanceInspectorPort",
    "RemovalPackageInspectorPort",
    "VisibleWatermarkInspectorPort",
]


class ContentIntegrityInspector:
    """Hash an asset, inspect it without mutation, and issue a structured receipt."""

    def __init__(
        self,
        provenance_inspector: ProvenanceInspectorPort,
        visible_watermark_inspector: VisibleWatermarkInspectorPort,
        removal_package_inspector: RemovalPackageInspectorPort,
    ) -> None:
        self._provenance_inspector = provenance_inspector
        self._visible_watermark_inspector = visible_watermark_inspector
        self._removal_package_inspector = removal_package_inspector

    def inspect(
        self, path: str | Path, *, asset_path: str | None = None
    ) -> ContentIntegrityReceipt:
        """Inspect an existing file and verify that inspection did not alter it."""
        return inspect_content_integrity(
            path,
            provenance_inspector=self._provenance_inspector,
            visible_watermark_inspector=self._visible_watermark_inspector,
            removal_package_inspector=self._removal_package_inspector,
            asset_path=asset_path,
        )
