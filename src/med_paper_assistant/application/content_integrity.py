"""Application service for read-only content-integrity inspection."""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from med_paper_assistant.domain.value_objects.content_integrity import (
    ContentIntegrityReceipt,
    ProvenanceAssessment,
    ProvenanceStatus,
    VisibleWatermarkAssessment,
    VisibleWatermarkStatus,
    decide_integrity_gate,
)


class ProvenanceInspectorPort(Protocol):
    """Port implemented by a scheme-specific provenance adapter."""

    def inspect(self, path: Path, mime_type: str) -> ProvenanceAssessment: ...


class VisibleWatermarkInspectorPort(Protocol):
    """Port implemented by a conservative visible-watermark heuristic."""

    def inspect(self, path: Path, mime_type: str) -> VisibleWatermarkAssessment: ...


class ContentIntegrityInspector:
    """Hash an asset, inspect it without mutation, and issue a structured receipt."""

    _HASH_CHUNK_SIZE = 1024 * 1024

    def __init__(
        self,
        provenance_inspector: ProvenanceInspectorPort,
        visible_watermark_inspector: VisibleWatermarkInspectorPort,
    ) -> None:
        self._provenance_inspector = provenance_inspector
        self._visible_watermark_inspector = visible_watermark_inspector

    @classmethod
    def _sha256(cls, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(cls._HASH_CHUNK_SIZE), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def inspect(
        self, path: str | Path, *, asset_path: str | None = None
    ) -> ContentIntegrityReceipt:
        """Inspect an existing file and verify that inspection did not alter it."""
        candidate = Path(path)
        if not candidate.is_file():
            raise ValueError(f"Asset is not a readable file: {candidate}")

        mime_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        before_hash = self._sha256(candidate)
        size_bytes = candidate.stat().st_size

        try:
            provenance = self._provenance_inspector.inspect(candidate, mime_type)
        except Exception as exc:  # pragma: no cover - defensive adapter boundary
            provenance = ProvenanceAssessment(
                status=ProvenanceStatus.ERROR,
                provider="unknown",
                summary=f"Provenance adapter failed: {type(exc).__name__}",
            )

        try:
            visible_watermark = self._visible_watermark_inspector.inspect(candidate, mime_type)
        except Exception as exc:  # pragma: no cover - defensive adapter boundary
            visible_watermark = VisibleWatermarkAssessment(
                status=VisibleWatermarkStatus.HUMAN_REVIEW,
                summary=f"Visible-watermark heuristic failed: {type(exc).__name__}",
                signals=("heuristic_error",),
                applicable=mime_type.startswith("image/"),
            )

        after_hash = self._sha256(candidate)
        original_preserved = before_hash == after_hash
        gate_status, gate_reasons = decide_integrity_gate(
            provenance,
            visible_watermark,
            original_preserved=original_preserved,
            mime_type=mime_type,
        )

        return ContentIntegrityReceipt(
            asset_path=asset_path or candidate.as_posix(),
            inspected_at=datetime.now(timezone.utc).isoformat(),
            sha256=before_hash,
            sha256_after_inspection=after_hash,
            mime_type=mime_type,
            size_bytes=size_bytes,
            provenance=provenance,
            visible_watermark=visible_watermark,
            gate_status=gate_status,
            gate_reasons=gate_reasons,
            original_preserved=original_preserved,
        )
