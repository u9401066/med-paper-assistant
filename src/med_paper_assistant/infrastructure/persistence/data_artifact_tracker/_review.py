"""Data Artifact Tracker — asset review caption and content-integrity validation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ._receipt_gate import (
    check_asset_identity,
    check_live_receipt,
    validate_stored_receipt,
)
from ._receipt_parse import ReceiptRejected
from ._records import _RecordMixin


class _ReviewMixin(_RecordMixin):
    """Validate asset reviews against captions and current asset bytes."""

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

        integrity_ok, integrity_detail = self._integrity_receipt_satisfies_review(review)
        if not integrity_ok:
            return False, integrity_detail

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

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _inspect_current_content_integrity(
        self,
        candidate: Path,
        asset_path: str,
    ) -> dict[str, Any]:
        """Re-run the read-only adapters instead of trusting a mutable YAML receipt.

        The audit file is intentionally human-readable and can be edited by the
        same local actor that invokes a tool.  Reinspection makes the insertion
        gate depend on the current bytes and adapter results, while the persisted
        receipt remains useful as an audit/history record.
        """
        return self._content_integrity_reinspector(
            candidate,
            asset_path=asset_path,
        ).to_dict()

    def _integrity_receipt_satisfies_review(
        self,
        review: dict[str, Any],
    ) -> tuple[bool, str]:
        """Validate receipt linkage, gate decision, and current asset identity."""
        receipt_id = str(review.get("content_integrity_receipt_id") or "").strip()
        if not receipt_id:
            return False, "content-integrity receipt missing; review the asset again"

        asset_path = str(review.get("asset_path") or "")
        receipt = self.get_content_integrity_receipt(
            asset_path,
            receipt_id=receipt_id,
            asset_type=str(review.get("asset_type") or "") or None,
        )
        if receipt is None:
            return False, f"content-integrity receipt {receipt_id} not found"

        try:
            parsed, expected_hash = validate_stored_receipt(receipt, receipt_id, review)
            candidate = check_asset_identity(
                self._project_dir, asset_path, parsed.file, expected_hash, self._sha256
            )
        except ReceiptRejected as exc:
            return False, str(exc)

        try:
            live_receipt = self._inspect_current_content_integrity(candidate, asset_path)
        except Exception as exc:
            return False, f"live content-integrity reinspection failed: {type(exc).__name__}"

        try:
            check_live_receipt(receipt, review, expected_hash, live_receipt)
        except ReceiptRejected as exc:
            return False, str(exc)

        return True, receipt_id
