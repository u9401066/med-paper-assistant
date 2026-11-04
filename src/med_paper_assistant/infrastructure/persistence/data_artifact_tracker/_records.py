"""Data Artifact Tracker — artifact, review, and receipt recording mixin."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from ._models import ArtifactType, logger
from ._storage import _StorageMixin


class _RecordMixin(_StorageMixin):
    """Record and query artifacts, asset reviews, and content-integrity receipts."""

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
        content_integrity_receipt_id: str | None = None,
        visible_watermark_review: str | None = None,
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
            "content_integrity_receipt_id": content_integrity_receipt_id,
            "visible_watermark_review": (visible_watermark_review or "").strip(),
            "timestamp": datetime.now().isoformat(),
        }
        reviews.append(entry)
        self._save()
        logger.info("Recorded asset review: %s (%s %s)", entry["id"], asset_type, normalized_path)
        return entry

    def record_content_integrity_receipt(
        self,
        asset_type: Literal["figure", "table"],
        asset_path: str,
        receipt: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist a structured, read-only provenance/integrity inspection receipt."""
        data = self._load()
        normalized_path = self._normalize_path(asset_path)
        receipts: list[dict[str, Any]] = data.setdefault("content_integrity_receipts", [])
        receipt_id = f"CI-{len(receipts) + 1:03d}"
        entry = {
            "id": receipt_id,
            "asset_type": asset_type,
            "asset_path": normalized_path,
            **receipt,
        }
        # The tracker owns these locators even if a caller supplied aliases.
        entry["id"] = receipt_id
        entry["asset_type"] = asset_type
        entry["asset_path"] = normalized_path
        receipts.append(entry)
        self._save()
        logger.info(
            "Recorded content integrity receipt: %s (%s %s)",
            entry["id"],
            asset_type,
            normalized_path,
        )
        return entry

    def get_content_integrity_receipt(
        self,
        asset_path: str,
        *,
        receipt_id: str | None = None,
        asset_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Return a referenced receipt, or the latest receipt for an asset."""
        normalized_path = self._normalize_path(asset_path)
        receipts = self._load().get("content_integrity_receipts", [])
        matches = [
            receipt
            for receipt in receipts
            if receipt.get("asset_path") == normalized_path
            and (receipt_id is None or receipt.get("id") == receipt_id)
            and (asset_type is None or receipt.get("asset_type") == asset_type)
        ]
        if not matches:
            return None
        return sorted(matches, key=lambda receipt: receipt.get("inspected_at", ""))[-1]

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
