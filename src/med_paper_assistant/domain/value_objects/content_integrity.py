"""Pure value objects for content provenance and integrity review receipts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


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
class ContentIntegrityReceipt:
    """Evidence-preserving receipt for one read-only asset inspection."""

    asset_path: str
    inspected_at: str
    sha256: str
    sha256_after_inspection: str
    mime_type: str
    size_bytes: int
    provenance: ProvenanceAssessment
    visible_watermark: VisibleWatermarkAssessment
    gate_status: IntegrityGateStatus
    gate_reasons: tuple[str, ...]
    original_preserved: bool

    @property
    def automated_removal_performed(self) -> bool:
        """Removal is intentionally outside this inspection contract."""
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "asset_path": self.asset_path,
            "inspected_at": self.inspected_at,
            "file": {
                "sha256": self.sha256,
                "sha256_after_inspection": self.sha256_after_inspection,
                "mime_type": self.mime_type,
                "size_bytes": self.size_bytes,
            },
            "provenance": self.provenance.to_dict(),
            "visible_watermark": self.visible_watermark.to_dict(),
            "gate_status": self.gate_status.value,
            "gate_reasons": list(self.gate_reasons),
            "original_preserved": self.original_preserved,
            "automated_removal_performed": self.automated_removal_performed,
        }


def decide_integrity_gate(
    provenance: ProvenanceAssessment,
    visible_watermark: VisibleWatermarkAssessment,
    *,
    original_preserved: bool,
    mime_type: str | None = None,
) -> tuple[IntegrityGateStatus, tuple[str, ...]]:
    """Apply a deterministic, evidence-preserving integrity policy."""
    reasons: list[str] = []

    if not original_preserved:
        reasons.append("Asset bytes changed during read-only inspection.")

    if provenance.status is ProvenanceStatus.PRESENT_INVALID:
        reasons.append("C2PA manifest is present but cryptographic validation failed.")
    elif provenance.status is ProvenanceStatus.ERROR:
        reasons.append("C2PA inspection failed unexpectedly for this asset.")

    if reasons:
        return IntegrityGateStatus.BLOCK, tuple(reasons)

    if visible_watermark.status is VisibleWatermarkStatus.HUMAN_REVIEW:
        return (
            IntegrityGateStatus.HUMAN_REVIEW,
            ("Visible-watermark signals require documented human review.",),
        )

    raster_mime_type = (mime_type or "").lower() in {"image/jpeg", "image/png"}
    if visible_watermark.status is VisibleWatermarkStatus.UNCERTAIN and (
        raster_mime_type or visible_watermark.applicable
    ):
        return (
            IntegrityGateStatus.HUMAN_REVIEW,
            (
                "Visible-watermark screening is inconclusive for this image; "
                "documented human review is required.",
            ),
        )

    return IntegrityGateStatus.PASS, (
        "No blocking integrity condition was detected for this non-image asset; "
        "provenance absence is not proof of origin.",
    )
