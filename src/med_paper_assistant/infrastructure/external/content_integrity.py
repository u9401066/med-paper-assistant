"""Optional provenance and conservative visible-watermark adapters."""

from __future__ import annotations

import importlib
import re
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

from med_paper_assistant.domain.value_objects.content_integrity import (
    ProvenanceAssessment,
    ProvenanceStatus,
    VisibleWatermarkAssessment,
    VisibleWatermarkStatus,
)


class C2paProvenanceAdapter:
    """Read and validate C2PA metadata when the optional SDK is installed.

    The adapter disables remote-manifest fetching, never signs or rewrites an
    asset, and stores only a bounded validation summary in the audit receipt.
    """

    _SUPPORTED_PREFIXES = ("image/", "video/", "audio/")
    _SUPPORTED_EXACT = {"application/pdf"}
    _TRUST_ONLY_CODES = {
        "claimsignature.untrusted",
        "signingcredential.untrusted",
        "timestamp.untrusted",
        "timestampcredential.untrusted",
    }

    def __init__(self, module_loader: Callable[[], ModuleType] | None = None) -> None:
        self._module_loader = module_loader or (lambda: importlib.import_module("c2pa"))

    @classmethod
    def _is_supported_media_type(cls, mime_type: str) -> bool:
        return mime_type.startswith(cls._SUPPORTED_PREFIXES) or mime_type in cls._SUPPORTED_EXACT

    @staticmethod
    def _failure_codes(validation_results: Any) -> tuple[str, ...]:
        codes: set[str] = set()

        def walk(value: Any, *, in_failure: bool = False) -> None:
            if isinstance(value, dict):
                code = value.get("code")
                if in_failure and isinstance(code, str) and code:
                    codes.add(code[:160])
                for key, child in value.items():
                    walk(child, in_failure=in_failure or str(key).lower() == "failure")
            elif isinstance(value, list):
                for child in value:
                    walk(child, in_failure=in_failure)

        walk(validation_results)
        return tuple(sorted(codes))

    @classmethod
    def _only_trust_failures(cls, failure_codes: tuple[str, ...]) -> bool:
        if not failure_codes:
            return False
        return all(
            code.lower() in cls._TRUST_ONLY_CODES or code.lower().endswith(".untrusted")
            for code in failure_codes
        )

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        text = re.sub(r"\s+", " ", str(exc)).strip()
        return (text or type(exc).__name__)[:240]

    def inspect(self, path: Path, mime_type: str) -> ProvenanceAssessment:
        if not self._is_supported_media_type(mime_type):
            return ProvenanceAssessment(
                status=ProvenanceStatus.UNSUPPORTED,
                provider="c2pa-python",
                summary=f"C2PA inspection is not applicable to MIME type {mime_type}.",
            )

        try:
            c2pa = self._module_loader()
        except ModuleNotFoundError:
            return ProvenanceAssessment(
                status=ProvenanceStatus.UNSUPPORTED,
                provider="c2pa-python",
                summary="Optional c2pa-python dependency is not installed.",
            )

        try:
            settings = c2pa.Settings.from_dict(
                {
                    "verify": {
                        "verify_after_reading": True,
                        "remote_manifest_fetch": False,
                    }
                }
            )
            with c2pa.Context(settings) as context:
                reader = c2pa.Reader.try_create(path, context=context)
                if reader is None:
                    return ProvenanceAssessment(
                        status=ProvenanceStatus.ABSENT,
                        provider="c2pa-python",
                        summary="No C2PA manifest was found; absence does not establish origin.",
                    )

                with reader:
                    state = reader.get_validation_state()
                    failure_codes = self._failure_codes(reader.get_validation_results())
                    embedded = reader.is_embedded()

            normalized_state = str(state or "").strip().lower()
            if normalized_state == "trusted":
                status = ProvenanceStatus.PRESENT_VALID_TRUSTED
                summary = "C2PA manifest is valid and its active signature is trusted."
            elif normalized_state == "valid" or (
                normalized_state == "invalid" and self._only_trust_failures(failure_codes)
            ):
                status = ProvenanceStatus.PRESENT_VALID_UNTRUSTED
                summary = "C2PA manifest is valid, but signer trust is not established locally."
            elif normalized_state == "invalid":
                status = ProvenanceStatus.PRESENT_INVALID
                summary = "C2PA manifest is present but validation reported failures."
            else:
                status = ProvenanceStatus.ERROR
                summary = "C2PA manifest was found but returned no recognized validation state."

            return ProvenanceAssessment(
                status=status,
                provider="c2pa-python",
                summary=summary,
                validation_state=str(state) if state is not None else None,
                failure_codes=failure_codes,
                manifest_embedded=embedded,
            )
        except Exception as exc:
            error = self._safe_error(exc)
            lowered = error.lower()
            if "unsupported" in lowered and ("format" in lowered or "mime" in lowered):
                status = ProvenanceStatus.UNSUPPORTED
            elif "manifestnotfound" in lowered or "no jumbf data" in lowered:
                status = ProvenanceStatus.ABSENT
            else:
                status = ProvenanceStatus.ERROR
            return ProvenanceAssessment(
                status=status,
                provider="c2pa-python",
                summary=f"C2PA inspection did not complete: {error}",
            )


class ConservativeVisibleWatermarkHeuristic:
    """Screen for review signals without ever asserting that an image is clean."""

    _MAX_TEXT_BYTES = 1024 * 1024
    _SIGNAL_TERMS = (
        "watermark",
        "watermarked",
        "stock-photo",
        "stock_image",
        "shutterstock",
        "gettyimages",
        "adobe stock",
        "preview only",
    )

    def inspect(self, path: Path, mime_type: str) -> VisibleWatermarkAssessment:
        if not mime_type.startswith("image/"):
            return VisibleWatermarkAssessment(
                status=VisibleWatermarkStatus.UNCERTAIN,
                summary="Visible-watermark screening is not applicable to this non-image asset.",
                applicable=False,
            )

        searchable_parts = [path.name.lower().replace(" ", "-")]
        if mime_type == "image/svg+xml" or path.suffix.lower() == ".svg":
            with path.open("rb") as stream:
                searchable_parts.append(
                    stream.read(self._MAX_TEXT_BYTES).decode("utf-8", "ignore").lower()
                )

        haystack = "\n".join(searchable_parts)
        signals = tuple(sorted({term for term in self._SIGNAL_TERMS if term in haystack}))
        if signals:
            return VisibleWatermarkAssessment(
                status=VisibleWatermarkStatus.HUMAN_REVIEW,
                summary="Possible visible-watermark indicators were found; visual review is required.",
                signals=signals,
            )

        return VisibleWatermarkAssessment(
            status=VisibleWatermarkStatus.UNCERTAIN,
            summary=(
                "No filename/SVG-text signal was found, but automated screening cannot prove "
                "that a visible watermark is absent."
            ),
        )
