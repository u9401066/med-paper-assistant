"""Data Artifact Tracker — structural parsing of stored content-integrity receipts."""

from __future__ import annotations

from typing import Any, NamedTuple

from med_paper_assistant.domain.value_objects.content_integrity import (
    REMOVAL_PACKAGE_INSPECTION_MODE,
    REMOVAL_PACKAGE_PROVIDER,
    REMOVAL_PACKAGE_REQUIRED_CHECKS,
    ProvenanceAssessment,
    ProvenanceStatus,
    RemovalPackageAssessment,
    RemovalPackageStatus,
    VisibleWatermarkAssessment,
    VisibleWatermarkStatus,
)


class ReceiptRejected(Exception):
    """A content-integrity receipt failed validation; ``str(exc)`` is the reason."""


class FileIdentity(NamedTuple):
    """Validated ``file`` block of a receipt."""

    info: dict[str, Any]
    mime_type: str
    declared_mime_type: str
    content_mime_type: str | None
    mime_type_mismatch: bool


class ParsedReceipt(NamedTuple):
    """Typed assessments recovered from a stored receipt."""

    file: FileIdentity
    provenance: ProvenanceAssessment
    visible: VisibleWatermarkAssessment
    removal: RemovalPackageAssessment


def check_receipt_envelope(receipt: dict[str, Any], receipt_id: str) -> str:
    """Validate schema version and gate status; return the stored gate status."""
    if receipt.get("schema_version") != "1.2":
        raise ReceiptRejected("content-integrity receipt schema is stale; review the asset again")

    gate_status = receipt.get("gate_status")
    if gate_status == "BLOCK":
        raise ReceiptRejected(f"content-integrity receipt {receipt_id} is blocked")
    if gate_status not in {"PASS", "HUMAN_REVIEW"}:
        raise ReceiptRejected(f"content-integrity receipt {receipt_id} has an unknown gate status")
    return gate_status


def check_file_identity(receipt: dict[str, Any]) -> FileIdentity:
    """Validate the MIME identity fields of the receipt's ``file`` block."""
    file_info = receipt.get("file")
    if not isinstance(file_info, dict):
        raise ReceiptRejected("content-integrity receipt has no file identity")
    mime_type = file_info.get("mime_type")
    if not isinstance(mime_type, str) or not mime_type:
        raise ReceiptRejected("content-integrity receipt has no MIME identity")
    declared_mime_type = file_info.get("declared_mime_type")
    content_mime_type = file_info.get("content_mime_type")
    mime_type_mismatch = file_info.get("mime_type_mismatch")
    if not isinstance(declared_mime_type, str) or not declared_mime_type:
        raise ReceiptRejected("content-integrity receipt has no declared MIME identity")
    if content_mime_type is not None and not isinstance(content_mime_type, str):
        raise ReceiptRejected("content-integrity receipt has an invalid content MIME identity")
    if not isinstance(mime_type_mismatch, bool):
        raise ReceiptRejected("content-integrity receipt has no MIME mismatch decision")
    if mime_type != (content_mime_type or declared_mime_type):
        raise ReceiptRejected("content-integrity receipt has inconsistent MIME identities")
    if mime_type_mismatch != (
        content_mime_type is not None and content_mime_type != declared_mime_type
    ):
        raise ReceiptRejected("content-integrity receipt has an inconsistent MIME mismatch flag")
    return FileIdentity(
        info=file_info,
        mime_type=mime_type,
        declared_mime_type=declared_mime_type,
        content_mime_type=content_mime_type,
        mime_type_mismatch=mime_type_mismatch,
    )


def parse_provenance(receipt: dict[str, Any]) -> ProvenanceAssessment:
    """Rebuild the provenance assessment from the receipt."""
    provenance = receipt.get("provenance")
    if not isinstance(provenance, dict):
        raise ReceiptRejected("content-integrity receipt has no provenance assessment")
    status_value = provenance.get("status")
    if not isinstance(status_value, str):
        raise ReceiptRejected("content-integrity receipt has an unknown provenance status")
    try:
        status = ProvenanceStatus(status_value)
    except ValueError:
        raise ReceiptRejected("content-integrity receipt has an unknown provenance status")
    failure_codes = provenance.get("failure_codes")
    if not isinstance(failure_codes, list) or any(
        not isinstance(item, str) for item in failure_codes
    ):
        raise ReceiptRejected("content-integrity receipt has invalid provenance failure codes")
    return ProvenanceAssessment(
        status=status,
        provider=str(provenance.get("provider") or ""),
        summary=str(provenance.get("summary") or ""),
        validation_state=(
            provenance.get("validation_state")
            if isinstance(provenance.get("validation_state"), str)
            else None
        ),
        failure_codes=tuple(failure_codes),
        manifest_embedded=(
            provenance.get("manifest_embedded")
            if isinstance(provenance.get("manifest_embedded"), bool)
            else None
        ),
    )


def parse_visible_watermark(receipt: dict[str, Any]) -> VisibleWatermarkAssessment:
    """Rebuild the visible-watermark assessment from the receipt."""
    visible_watermark = receipt.get("visible_watermark")
    if not isinstance(visible_watermark, dict):
        raise ReceiptRejected("content-integrity receipt has no visible-watermark assessment")
    status_value = visible_watermark.get("status")
    if not isinstance(status_value, str):
        raise ReceiptRejected("content-integrity receipt has an unknown visible-watermark status")
    try:
        status = VisibleWatermarkStatus(status_value)
    except ValueError:
        raise ReceiptRejected("content-integrity receipt has an unknown visible-watermark status")
    signals = visible_watermark.get("signals")
    applicable = visible_watermark.get("applicable")
    if not isinstance(signals, list) or any(not isinstance(item, str) for item in signals):
        raise ReceiptRejected("content-integrity receipt has invalid visible-watermark signals")
    if not isinstance(applicable, bool):
        raise ReceiptRejected("content-integrity receipt has no visible-watermark applicability")
    return VisibleWatermarkAssessment(
        status=status,
        summary=str(visible_watermark.get("summary") or ""),
        signals=tuple(signals),
        applicable=applicable,
    )


def _check_removal_affirmations(
    removal_check: dict[str, Any], status: RemovalPackageStatus
) -> None:
    """Validate provider identity and the detection-only guarantees of a removal check."""
    if removal_check.get("provider") != REMOVAL_PACKAGE_PROVIDER:
        raise ReceiptRejected(
            "content-integrity receipt has an unexpected removal-package provider"
        )
    if removal_check.get("inspection_mode") != REMOVAL_PACKAGE_INSPECTION_MODE:
        raise ReceiptRejected(
            "removal-package assessment did not use the pixel-only inspection mode"
        )
    if removal_check.get("automated_removal_performed") is not False:
        raise ReceiptRejected("removal-package assessment does not affirm removal was disabled")
    if removal_check.get("derivative_written") is not False:
        raise ReceiptRejected(
            "removal-package assessment does not affirm no derivative was written"
        )
    required_checks = list(REMOVAL_PACKAGE_REQUIRED_CHECKS)
    completed = removal_check.get("checks_completed")
    if removal_check.get("checks_requested") != required_checks:
        raise ReceiptRejected(
            "removal-package assessment did not request every required pixel check"
        )
    if status in {RemovalPackageStatus.DETECTED, RemovalPackageStatus.NOT_DETECTED}:
        if completed != required_checks:
            raise ReceiptRejected(
                "removal-package assessment did not complete every required pixel check"
            )
    elif completed not in ([], None):
        raise ReceiptRejected("incomplete removal-package assessment claims completed pixel checks")


def parse_removal_package(receipt: dict[str, Any]) -> RemovalPackageAssessment:
    """Rebuild the removal-package assessment from the receipt."""
    removal_check = receipt.get("removal_package_check")
    if not isinstance(removal_check, dict):
        raise ReceiptRejected("content-integrity receipt has no removal-package assessment")
    status_value = removal_check.get("status")
    if not isinstance(status_value, str):
        raise ReceiptRejected("content-integrity receipt has an unknown removal-package status")
    try:
        status = RemovalPackageStatus(status_value)
    except ValueError:
        raise ReceiptRejected("content-integrity receipt has an unknown removal-package status")
    _check_removal_affirmations(removal_check, status)
    clashes = removal_check.get("integrity_clashes")
    applicable = removal_check.get("applicable")
    if not isinstance(clashes, list) or any(not isinstance(item, str) for item in clashes):
        raise ReceiptRejected("content-integrity receipt has invalid removal-package clashes")
    if not isinstance(applicable, bool):
        raise ReceiptRejected("content-integrity receipt has no removal-package applicability")
    return RemovalPackageAssessment(
        status=status,
        provider=REMOVAL_PACKAGE_PROVIDER,
        provider_version=(
            removal_check.get("provider_version")
            if isinstance(removal_check.get("provider_version"), str)
            else None
        ),
        summary=str(removal_check.get("summary") or ""),
        integrity_clashes=tuple(clashes),
        checks_requested=tuple(removal_check.get("checks_requested") or ()),
        checks_completed=tuple(removal_check.get("checks_completed") or ()),
        applicable=applicable,
    )
