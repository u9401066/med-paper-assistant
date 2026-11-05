"""Read-only content-integrity inspection orchestration.

The Application service and the Infrastructure reinspection entry point both
delegate here, so the fail-closed adapter boundary and the before/after hash
check have a single implementation that every layer may depend on.
"""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from med_paper_assistant.domain.value_objects.content_integrity import (
    REMOVAL_PACKAGE_PROVIDER,
    ContentIntegrityReceipt,
    ProvenanceAssessment,
    ProvenanceStatus,
    RemovalPackageAssessment,
    RemovalPackageStatus,
    VisibleWatermarkAssessment,
    VisibleWatermarkStatus,
    decide_integrity_gate,
    detect_raster_mime_signature,
)

_HASH_CHUNK_SIZE = 1024 * 1024
_SIGNATURE_BYTES = 16
_PIXEL_INSPECTED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


class ProvenanceInspectorPort(Protocol):
    """Port implemented by a scheme-specific provenance adapter."""

    def inspect(self, path: Path, mime_type: str) -> ProvenanceAssessment: ...


class VisibleWatermarkInspectorPort(Protocol):
    """Port implemented by a conservative visible-watermark heuristic."""

    def inspect(self, path: Path, mime_type: str) -> VisibleWatermarkAssessment: ...


class RemovalPackageInspectorPort(Protocol):
    """Port for a detection-only call into a pinned watermark-removal package."""

    def inspect(self, path: Path, mime_type: str) -> RemovalPackageAssessment: ...


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _declared_mime_type(path: Path) -> str:
    return (
        {".webp": "image/webp"}.get(path.suffix.lower())
        or mimetypes.guess_type(path.name)[0]
        or "application/octet-stream"
    )


def _signature_mime_type(path: Path) -> str | None:
    """Recognize the raster formats whose detector gate is mandatory.

    Filename MIME remains a useful hint for other formats, but a renamed
    PNG/JPEG/WebP must not be able to bypass the pixel-backed inspection.
    """
    with path.open("rb") as stream:
        return detect_raster_mime_signature(stream.read(_SIGNATURE_BYTES))


def _resolve_mime_types(path: Path) -> tuple[str, str | None, str, bool]:
    """Return declared, content-signature, effective MIME and a mismatch flag."""
    declared = _declared_mime_type(path)
    content = _signature_mime_type(path)
    return declared, content, content or declared, content is not None and content != declared


def _safe_provenance(
    inspector: ProvenanceInspectorPort, path: Path, mime_type: str
) -> ProvenanceAssessment:
    try:
        return inspector.inspect(path, mime_type)
    except Exception as exc:  # pragma: no cover - defensive adapter boundary
        return ProvenanceAssessment(
            status=ProvenanceStatus.ERROR,
            provider="unknown",
            summary=f"Provenance adapter failed: {type(exc).__name__}",
        )


def _safe_visible_watermark(
    inspector: VisibleWatermarkInspectorPort, path: Path, mime_type: str
) -> VisibleWatermarkAssessment:
    try:
        return inspector.inspect(path, mime_type)
    except Exception as exc:  # pragma: no cover - defensive adapter boundary
        return VisibleWatermarkAssessment(
            status=VisibleWatermarkStatus.HUMAN_REVIEW,
            summary=f"Visible-watermark heuristic failed: {type(exc).__name__}",
            signals=("heuristic_error",),
            applicable=mime_type.startswith("image/"),
        )


def _safe_removal_package(
    inspector: RemovalPackageInspectorPort, path: Path, mime_type: str
) -> RemovalPackageAssessment:
    try:
        return inspector.inspect(path, mime_type)
    except Exception as exc:  # pragma: no cover - defensive adapter boundary
        return RemovalPackageAssessment(
            status=RemovalPackageStatus.ERROR,
            provider=REMOVAL_PACKAGE_PROVIDER,
            summary=f"Watermark-removal package check failed: {type(exc).__name__}",
            applicable=mime_type.lower() in _PIXEL_INSPECTED_MIME_TYPES,
        )


def inspect_content_integrity(
    path: str | Path,
    *,
    provenance_inspector: ProvenanceInspectorPort,
    visible_watermark_inspector: VisibleWatermarkInspectorPort,
    removal_package_inspector: RemovalPackageInspectorPort,
    asset_path: str | None = None,
) -> ContentIntegrityReceipt:
    """Inspect an existing file (fail-closed adapters, before/after hash check)."""
    candidate = Path(path)
    if not candidate.is_file():
        raise ValueError(f"Asset is not a readable file: {candidate}")

    declared_mime, content_mime, mime_type, mime_mismatch = _resolve_mime_types(candidate)
    before_hash = sha256_file(candidate)
    size_bytes = candidate.stat().st_size

    provenance = _safe_provenance(provenance_inspector, candidate, mime_type)
    visible_watermark = _safe_visible_watermark(visible_watermark_inspector, candidate, mime_type)
    removal_package_check = _safe_removal_package(removal_package_inspector, candidate, mime_type)

    after_hash = sha256_file(candidate)
    original_preserved = before_hash == after_hash
    gate_status, gate_reasons = decide_integrity_gate(
        provenance,
        visible_watermark,
        removal_package_check,
        original_preserved=original_preserved,
        mime_type=mime_type,
        mime_type_mismatch=mime_mismatch,
    )

    return ContentIntegrityReceipt(
        asset_path=asset_path or candidate.as_posix(),
        inspected_at=datetime.now(timezone.utc).isoformat(),
        sha256=before_hash,
        sha256_after_inspection=after_hash,
        mime_type=mime_type,
        size_bytes=size_bytes,
        declared_mime_type=declared_mime,
        content_mime_type=content_mime,
        mime_type_mismatch=mime_mismatch,
        provenance=provenance,
        visible_watermark=visible_watermark,
        removal_package_check=removal_package_check,
        gate_status=gate_status,
        gate_reasons=gate_reasons,
        original_preserved=original_preserved,
    )
