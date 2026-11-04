"""Data Artifact Tracker — gate, identity, and live-reinspection checks for receipts."""

from __future__ import annotations

import mimetypes
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from med_paper_assistant.domain.value_objects.content_integrity import (
    REMOVAL_PACKAGE_VERSION,
    RemovalPackageStatus,
    VisibleWatermarkStatus,
    decide_integrity_gate,
    detect_raster_mime_signature,
)

from ._receipt_parse import (
    FileIdentity,
    ParsedReceipt,
    ReceiptRejected,
    check_file_identity,
    check_receipt_envelope,
    parse_provenance,
    parse_removal_package,
    parse_visible_watermark,
)

_RASTER_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _is_raster(parsed: ParsedReceipt) -> bool:
    return parsed.file.mime_type.lower() in _RASTER_MIME_TYPES


def _visible_review_required(parsed: ParsedReceipt) -> bool:
    visible = parsed.visible
    return visible.status is VisibleWatermarkStatus.HUMAN_REVIEW or (
        visible.status is VisibleWatermarkStatus.UNCERTAIN
        and (_is_raster(parsed) or visible.applicable)
    )


def _check_removal_inspection(parsed: ParsedReceipt) -> None:
    """Reject raster receipts whose removal-package inspection is unpinned or incomplete."""
    removal = parsed.removal
    raster = _is_raster(parsed)
    if raster and removal.status in {
        RemovalPackageStatus.DETECTED,
        RemovalPackageStatus.NOT_DETECTED,
    }:
        if removal.provider_version != REMOVAL_PACKAGE_VERSION:
            raise ReceiptRejected(
                "content-integrity receipt has an unpinned removal-package version"
            )
    if raster and removal.status in {
        RemovalPackageStatus.UNSUPPORTED,
        RemovalPackageStatus.ERROR,
    }:
        raise ReceiptRejected("required removal-package inspection did not complete")


def _check_recomputed_gate(
    receipt: dict[str, Any], parsed: ParsedReceipt, gate_status: str
) -> None:
    """Recompute the gate decision from the typed assessments and compare."""
    recomputed_gate, _recomputed_reasons = decide_integrity_gate(
        parsed.provenance,
        parsed.visible,
        parsed.removal,
        original_preserved=receipt.get("original_preserved") is True,
        mime_type=parsed.file.mime_type,
        mime_type_mismatch=parsed.file.mime_type_mismatch,
    )
    if recomputed_gate.value == "BLOCK":
        raise ReceiptRejected("content-integrity receipt recomputes to a blocked gate")
    if recomputed_gate.value == "HUMAN_REVIEW" and gate_status != "HUMAN_REVIEW":
        raise ReceiptRejected(
            "content-integrity receipt gate is weaker than the recomputed decision"
        )


def _check_review_requirements(
    receipt: dict[str, Any],
    review: dict[str, Any],
    parsed: ParsedReceipt,
    gate_status: str,
) -> None:
    """Require human review wherever the stored assessments call for it."""
    review_required = _visible_review_required(parsed)
    if review_required and gate_status != "HUMAN_REVIEW":
        raise ReceiptRejected(
            "content-integrity receipt inconsistently passes an uncertain "
            "visible-watermark assessment"
        )
    if parsed.removal.status is RemovalPackageStatus.DETECTED and gate_status != "HUMAN_REVIEW":
        raise ReceiptRejected("removal-package detection did not trigger human review")
    if (review_required or gate_status == "HUMAN_REVIEW") and not str(
        review.get("visible_watermark_review") or ""
    ).strip():
        raise ReceiptRejected("visible-watermark human review is not documented")
    if receipt.get("automated_removal_performed") is not False:
        raise ReceiptRejected("receipt does not affirm that automated removal was disabled")
    if receipt.get("original_preserved") is not True:
        raise ReceiptRejected("receipt does not affirm that original bytes were preserved")


def _check_hash_identity(file_info: dict[str, Any]) -> str:
    """Return the stored SHA-256 after verifying the two inspection-time values agree."""
    expected_hash = file_info.get("sha256")
    if not isinstance(expected_hash, str) or not expected_hash:
        raise ReceiptRejected("content-integrity receipt has no SHA-256 identity")
    if file_info.get("sha256_after_inspection") != expected_hash:
        raise ReceiptRejected("inspection-time SHA-256 values do not match")
    return expected_hash


def validate_stored_receipt(
    receipt: dict[str, Any],
    receipt_id: str,
    review: dict[str, Any],
) -> tuple[ParsedReceipt, str]:
    """Validate a stored receipt's structure and gate; return it with its SHA-256."""
    gate_status = check_receipt_envelope(receipt, receipt_id)
    file_identity = check_file_identity(receipt)
    parsed = ParsedReceipt(
        file=file_identity,
        provenance=parse_provenance(receipt),
        visible=parse_visible_watermark(receipt),
        removal=parse_removal_package(receipt),
    )
    _check_removal_inspection(parsed)
    _check_recomputed_gate(receipt, parsed, gate_status)
    _check_review_requirements(receipt, review, parsed, gate_status)
    return parsed, _check_hash_identity(file_identity.info)


def check_asset_identity(
    project_dir: Path,
    asset_path: str,
    file_identity: FileIdentity,
    expected_hash: str,
    sha256: Callable[[Path], str],
) -> Path:
    """Verify the reviewed asset still has the reviewed bytes and MIME identity."""
    project_root = project_dir.resolve()
    candidate = (project_root / asset_path).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError:
        raise ReceiptRejected("reviewed asset path escapes the project root")
    if not candidate.is_file():
        raise ReceiptRejected("reviewed asset no longer exists")
    if sha256(candidate) != expected_hash:
        raise ReceiptRejected("asset SHA-256 changed after content-integrity review")
    with candidate.open("rb") as stream:
        actual_content_mime = detect_raster_mime_signature(stream.read(16))
    actual_declared_mime = (
        {".webp": "image/webp"}.get(candidate.suffix.lower())
        or mimetypes.guess_type(candidate.name)[0]
        or "application/octet-stream"
    )
    if actual_content_mime != file_identity.content_mime_type:
        raise ReceiptRejected("asset content MIME signature changed after integrity review")
    if actual_declared_mime != file_identity.declared_mime_type:
        raise ReceiptRejected("asset filename MIME changed after integrity review")
    return candidate


def _live_blocks(live_receipt: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return the live file/provenance/visible-watermark/removal blocks, or reject."""
    blocks = tuple(
        live_receipt.get(key)
        for key in ("file", "provenance", "visible_watermark", "removal_package_check")
    )
    if not all(isinstance(item, dict) for item in blocks):
        raise ReceiptRejected("live content-integrity reinspection returned an invalid receipt")
    return cast(tuple[dict[str, Any], ...], blocks)


def _stored_vs_live(
    receipt: dict[str, Any],
    live_receipt: dict[str, Any],
    live_provenance: dict[str, Any],
    live_visible: dict[str, Any],
    live_removal: dict[str, Any],
) -> tuple[tuple[str, Any, Any], ...]:
    provenance = cast(dict[str, Any], receipt.get("provenance"))
    visible_watermark = cast(dict[str, Any], receipt.get("visible_watermark"))
    removal_check = cast(dict[str, Any], receipt.get("removal_package_check"))
    return (
        ("provenance status", provenance.get("status"), live_provenance.get("status")),
        (
            "visible-watermark status",
            visible_watermark.get("status"),
            live_visible.get("status"),
        ),
        (
            "visible-watermark applicability",
            visible_watermark.get("applicable"),
            live_visible.get("applicable"),
        ),
        ("removal-package status", removal_check.get("status"), live_removal.get("status")),
        (
            "removal-package applicability",
            removal_check.get("applicable"),
            live_removal.get("applicable"),
        ),
        (
            "removal-package completed checks",
            removal_check.get("checks_completed"),
            live_removal.get("checks_completed"),
        ),
        ("gate status", receipt.get("gate_status"), live_receipt.get("gate_status")),
    )


def check_live_receipt(
    receipt: dict[str, Any],
    review: dict[str, Any],
    expected_hash: str,
    live_receipt: dict[str, Any],
) -> None:
    """Compare the stored receipt against the freshly reinspected asset."""
    live_file, live_provenance, live_visible, live_removal = _live_blocks(live_receipt)
    if live_file.get("sha256") != expected_hash:
        raise ReceiptRejected("live content-integrity reinspection used different asset bytes")
    if live_receipt.get("original_preserved") is not True:
        raise ReceiptRejected("live content-integrity reinspection did not preserve the original")
    if live_receipt.get("gate_status") == "BLOCK":
        raise ReceiptRejected("live content-integrity reinspection blocks this asset")

    for label, stored_value, live_value in _stored_vs_live(
        receipt, live_receipt, live_provenance, live_visible, live_removal
    ):
        if stored_value != live_value:
            raise ReceiptRejected(
                f"content-integrity receipt {label} differs from live reinspection"
            )

    if (
        live_receipt.get("gate_status") == "HUMAN_REVIEW"
        and not str(review.get("visible_watermark_review") or "").strip()
    ):
        raise ReceiptRejected(
            "live content-integrity reinspection requires documented human review"
        )
