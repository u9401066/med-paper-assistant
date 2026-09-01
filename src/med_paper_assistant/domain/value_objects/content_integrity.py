"""Pure value objects for content provenance and integrity review receipts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

REMOVAL_PACKAGE_PROVIDER = "remove-ai-watermarks"
REMOVAL_PACKAGE_VERSION = "0.36.0"
REMOVAL_PACKAGE_INSPECTION_MODE = "strict_registered_visible_open_dwt_v1"
REMOVAL_PACKAGE_REQUIRED_CHECKS = ("registered_visible", "open_dwt_dct")


def detect_raster_mime_signature(header: bytes) -> str | None:
    """Identify raster formats that require the pixel-backed integrity gate."""
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


class ProvenanceStatus(StrEnum):
    """Outcome of a scheme-specific provenance inspection."""

    PRESENT_VALID_TRUSTED = "PRESENT_VALID_TRUSTED"
    PRESENT_VALID_UNTRUSTED = "PRESENT_VALID_UNTRUSTED"
    PRESENT_INVALID = "PRESENT_INVALID"
    ABSENT = "ABSENT"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


class VisibleWatermarkStatus(StrEnum):
    """Conservative visible-watermark outcomes.

    The implementation intentionally has no automated ``CLEAN`` outcome: a
    heuristic cannot prove that a visible watermark is absent.
    """

    HUMAN_REVIEW = "HUMAN_REVIEW"
    UNCERTAIN = "UNCERTAIN"


class RemovalPackageStatus(StrEnum):
    """Outcome of the independently pinned watermark-removal package check."""

    DETECTED = "DETECTED"
    NOT_DETECTED = "NOT_DETECTED"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


class IntegrityGateStatus(StrEnum):
    """Decision produced by the integrity inspection gate."""

    PASS = "PASS"  # nosec B105 - integrity status, not a credential
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class ProvenanceAssessment:
    """Scheme-specific provenance result without raw manifest payloads."""

    status: ProvenanceStatus
    provider: str
    summary: str
    validation_state: str | None = None
    failure_codes: tuple[str, ...] = ()
    manifest_embedded: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "provider": self.provider,
            "summary": self.summary,
            "validation_state": self.validation_state,
            "failure_codes": list(self.failure_codes),
            "manifest_embedded": self.manifest_embedded,
        }


@dataclass(frozen=True, slots=True)
class VisibleWatermarkAssessment:
    """Conservative screening result requiring visual confirmation."""

    status: VisibleWatermarkStatus
    summary: str
    signals: tuple[str, ...] = ()
    applicable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "summary": self.summary,
            "signals": list(self.signals),
            "applicable": self.applicable,
        }


@dataclass(frozen=True, slots=True)
class RemovalPackageAssessment:
    """Detection-only result from a package that can also remove known marks.

    The application deliberately uses only the package's identification API.
    It never writes a cleaned derivative and never strips provenance metadata.
    """

    status: RemovalPackageStatus
    provider: str
    summary: str
    provider_version: str | None = None
    watermarks: tuple[str, ...] = ()
    signal_names: tuple[str, ...] = ()
    platform: str | None = None
    confidence: str | None = None
    ai_generated: bool | None = None
    integrity_clashes: tuple[str, ...] = ()
    checks_requested: tuple[str, ...] = REMOVAL_PACKAGE_REQUIRED_CHECKS
    checks_completed: tuple[str, ...] = ()
    applicable: bool = True

    @property
    def inspection_mode(self) -> str:
        return REMOVAL_PACKAGE_INSPECTION_MODE

    @property
    def automated_removal_performed(self) -> bool:
        return False

    @property
    def derivative_written(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "provider": self.provider,
            "provider_version": self.provider_version,
            "summary": self.summary,
            "watermarks": list(self.watermarks),
            "signal_names": list(self.signal_names),
            "platform": self.platform,
            "confidence": self.confidence,
            "ai_generated": self.ai_generated,
            "integrity_clashes": list(self.integrity_clashes),
            "checks_requested": list(self.checks_requested),
            "checks_completed": list(self.checks_completed),
            "applicable": self.applicable,
            "inspection_mode": self.inspection_mode,
            "automated_removal_performed": self.automated_removal_performed,
            "derivative_written": self.derivative_written,
        }


@dataclass(frozen=True, slots=True)
class ContentIntegrityReceipt:
    """Evidence-preserving receipt for one read-only asset inspection."""

    asset_path: str
    inspected_at: str
    sha256: str
    sha256_after_inspection: str
    mime_type: str
    size_bytes: int
    declared_mime_type: str
    content_mime_type: str | None
    mime_type_mismatch: bool
    provenance: ProvenanceAssessment
    visible_watermark: VisibleWatermarkAssessment
    removal_package_check: RemovalPackageAssessment
    gate_status: IntegrityGateStatus
    gate_reasons: tuple[str, ...]
    original_preserved: bool

    @property
    def automated_removal_performed(self) -> bool:
        """Removal is intentionally outside this inspection contract."""
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.2",
            "asset_path": self.asset_path,
            "inspected_at": self.inspected_at,
            "file": {
                "sha256": self.sha256,
                "sha256_after_inspection": self.sha256_after_inspection,
                "mime_type": self.mime_type,
                "declared_mime_type": self.declared_mime_type,
                "content_mime_type": self.content_mime_type,
                "mime_type_mismatch": self.mime_type_mismatch,
                "size_bytes": self.size_bytes,
            },
            "provenance": self.provenance.to_dict(),
            "visible_watermark": self.visible_watermark.to_dict(),
            "removal_package_check": self.removal_package_check.to_dict(),
            "gate_status": self.gate_status.value,
            "gate_reasons": list(self.gate_reasons),
            "original_preserved": self.original_preserved,
            "automated_removal_performed": self.automated_removal_performed,
        }


def decide_integrity_gate(
    provenance: ProvenanceAssessment,
    visible_watermark: VisibleWatermarkAssessment,
    removal_package_check: RemovalPackageAssessment | None = None,
    *,
    original_preserved: bool,
    mime_type: str | None = None,
    mime_type_mismatch: bool = False,
) -> tuple[IntegrityGateStatus, tuple[str, ...]]:
    """Apply a deterministic, evidence-preserving integrity policy."""
    reasons: list[str] = []

    if not original_preserved:
        reasons.append("Asset bytes changed during read-only inspection.")

    if mime_type_mismatch:
        reasons.append("Asset content signature does not match its filename MIME type.")

    if provenance.status is ProvenanceStatus.PRESENT_INVALID:
        reasons.append("C2PA manifest is present but cryptographic validation failed.")
    elif provenance.status is ProvenanceStatus.ERROR:
        reasons.append("C2PA inspection failed unexpectedly for this asset.")

    raster_mime_type = (mime_type or "").lower() in {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
    if raster_mime_type and removal_package_check is None:
        reasons.append("Required watermark-removal package check was not configured.")
    elif raster_mime_type and removal_package_check is not None:
        if removal_package_check.status is RemovalPackageStatus.UNSUPPORTED:
            reasons.append("Required watermark-removal package check is unavailable.")
        elif removal_package_check.status is RemovalPackageStatus.ERROR:
            reasons.append("Required watermark-removal package check failed.")

    if reasons:
        return IntegrityGateStatus.BLOCK, tuple(reasons)

    review_reasons: list[str] = []

    if removal_package_check is not None:
        if removal_package_check.status is RemovalPackageStatus.DETECTED:
            review_reasons.append(
                "The pinned watermark-removal package identified watermark or origin signals."
            )
        if removal_package_check.integrity_clashes:
            review_reasons.append(
                "The watermark-removal package reported conflicting provenance signals."
            )

    if visible_watermark.status is VisibleWatermarkStatus.HUMAN_REVIEW:
        review_reasons.append("Visible-watermark signals require documented human review.")

    if visible_watermark.status is VisibleWatermarkStatus.UNCERTAIN and (
        raster_mime_type or visible_watermark.applicable
    ):
        review_reasons.append(
            "Visible-watermark screening is inconclusive for this image; "
            "documented human review is required."
        )

    if review_reasons:
        return IntegrityGateStatus.HUMAN_REVIEW, tuple(review_reasons)

    return IntegrityGateStatus.PASS, (
        "No blocking integrity condition was detected for this non-image asset; "
        "provenance absence is not proof of origin.",
    )
