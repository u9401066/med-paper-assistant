"""Optional provenance and conservative visible-watermark adapters."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import mimetypes
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

from med_paper_assistant.domain.value_objects.content_integrity import (
    REMOVAL_PACKAGE_PROVIDER,
    REMOVAL_PACKAGE_REQUIRED_CHECKS,
    REMOVAL_PACKAGE_VERSION,
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


@dataclass(frozen=True, slots=True)
class _PixelInspectionCapabilities:
    image_module: ModuleType
    decode: Callable[[Path], Any]


@dataclass(frozen=True, slots=True)
class _PixelInspectionSignal:
    name: str


@dataclass(frozen=True, slots=True)
class _PixelInspectionReport:
    watermarks: tuple[str, ...]
    signals: tuple[_PixelInspectionSignal, ...]
    integrity_clashes: tuple[str, ...] = ()
    platform: str | None = None
    confidence: str | None = None
    is_ai_generated: bool | None = None


class RemoveAiWatermarksInspectionAdapter:
    """Use ``remove-ai-watermarks`` as a read-only, detection-only second opinion.

    The adapter calls the package's registered visible detectors one by one and
    its open DWT-DCT decoder explicitly.  It does not call the aggregate
    ``identify`` API because the shared ``check_invisible`` flag can also enter
    an optional TrustMark model-download path.  Any registered detector failure
    fails closed instead of being silently converted to ``NOT_DETECTED``.

    The C2PA reader, TrustMark, removal/output, GPU, and model paths are never
    imported or invoked here.
    """

    _SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
    _MAX_ASSET_BYTES = 100 * 1024 * 1024
    _MAX_IMAGE_PIXELS = 50_000_000
    _MAX_ITEMS = 20
    _MAX_TEXT = 240

    def __init__(
        self,
        pixel_inspector_loader: Callable[[], Callable[[Path, Any], Any]] | None = None,
        version_loader: Callable[[], str] | None = None,
        capabilities_loader: Callable[[], _PixelInspectionCapabilities] | None = None,
    ) -> None:
        self._pixel_inspector_loader = pixel_inspector_loader or self._load_pixel_inspector
        self._version_loader = version_loader or (
            lambda: importlib.metadata.version(REMOVAL_PACKAGE_PROVIDER)
        )
        self._capabilities_loader = capabilities_loader or self._load_capabilities

    @staticmethod
    def _load_pixel_inspector() -> Callable[[Path, Any], _PixelInspectionReport]:
        registry = importlib.import_module("remove_ai_watermarks.watermark_registry")
        known_marks = getattr(registry, "known_marks", None)
        if not callable(known_marks):
            raise ImportError("remove-ai-watermarks registered detector API is unavailable")
        invisible = importlib.import_module("remove_ai_watermarks.invisible_watermark")
        detect_invisible = getattr(invisible, "detect_invisible_watermark", None)
        if not callable(detect_invisible):
            raise ImportError("remove-ai-watermarks open DWT-DCT detector is unavailable")
        dwt_dct = importlib.import_module("remove_ai_watermarks.dwt_dct")
        decode_lengths = getattr(dwt_dct, "decode_dwt_dct_lengths", None)
        if not callable(decode_lengths):
            raise ImportError("remove-ai-watermarks DWT-DCT completion probe is unavailable")

        def inspect_pixels(path: Path, image: Any) -> _PixelInspectionReport:
            marks = tuple(known_marks())
            if not marks:
                raise RuntimeError("remove-ai-watermarks registered detector catalog is empty")
            watermarks: list[str] = []
            signals: list[_PixelInspectionSignal] = []
            platform: str | None = None
            confidence: str | None = None
            for mark in marks:
                detection = mark.detect(image, provenance=False)
                if detection.detected:
                    watermarks.append(
                        f"Visible {detection.label} (confidence {detection.confidence:.2f})"
                    )
                    signals.append(_PixelInspectionSignal(name=f"visible:{detection.key}"))
                    platform = platform or getattr(mark, "platform", None)
                    confidence = confidence or "medium"

            # The public detector historically turns a decode exception into
            # ``None``. Probe the exact required lengths first so a negative can
            # only be recorded after the open decoder actually completed.
            decoded = decode_lengths(image, (48, 136))
            if set(decoded) != {48, 136} or any(
                len(decoded[length]) != length for length in (48, 136)
            ):
                raise RuntimeError("open DWT-DCT detector returned incomplete bit lengths")
            scheme = detect_invisible(path, image=image)
            if scheme is not None:
                watermarks.append(f"Open invisible watermark: {scheme}")
                signals.append(_PixelInspectionSignal(name="invisible_watermark"))
                platform = platform or f"{scheme} (open DWT-DCT watermark)"
                confidence = "high"

            return _PixelInspectionReport(
                watermarks=tuple(watermarks),
                signals=tuple(signals),
                platform=platform,
                confidence=confidence,
                is_ai_generated=True if watermarks else None,
            )

        return inspect_pixels

    @staticmethod
    def _load_capabilities() -> _PixelInspectionCapabilities:
        # Import the real native/numeric modules. Merely finding their specs is
        # insufficient because a broken wheel can otherwise degrade to a silent
        # NOT_DETECTED result inside the upstream optional paths.
        for module_name in ("cv2", "numpy", "pywt"):
            importlib.import_module(module_name)
        image_module = importlib.import_module("PIL.Image")
        invisible = importlib.import_module("remove_ai_watermarks.invisible_watermark")
        is_available = getattr(invisible, "is_available", None)
        if not callable(is_available) or is_available() is not True:
            raise ImportError("open DWT-DCT detector dependencies are unavailable")
        image_io = importlib.import_module("remove_ai_watermarks.image_io")
        decode = getattr(image_io, "imread", None)
        if not callable(decode):
            raise ImportError("remove-ai-watermarks image decoder is unavailable")
        return _PixelInspectionCapabilities(image_module=image_module, decode=decode)

    @classmethod
    def _validate_decodable_image(
        cls,
        path: Path,
        capabilities: _PixelInspectionCapabilities,
    ) -> Any:
        with capabilities.image_module.open(path) as image:
            width, height = image.size
        if width <= 0 or height <= 0:
            raise ValueError("image dimensions must be positive")
        if width * height > cls._MAX_IMAGE_PIXELS:
            raise ValueError(f"image exceeds the {cls._MAX_IMAGE_PIXELS:,}-pixel inspection limit")
        decoded = capabilities.decode(path)
        if decoded is None:
            raise ValueError("image could not be decoded by the pixel detectors")
        shape: Any = getattr(decoded, "shape", ())
        if len(shape) < 2 or int(shape[0]) * int(shape[1]) > cls._MAX_IMAGE_PIXELS:
            raise ValueError("decoded image dimensions are invalid or exceed the limit")
        return decoded

    @classmethod
    def _bounded_text(cls, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        without_controls = "".join(
            character
            for character in value
            if unicodedata.category(character) not in {"Cc", "Cf", "Cs"}
        )
        text = re.sub(r"\s+", " ", without_controls).strip()
        return text[: cls._MAX_TEXT] or None

    @classmethod
    def _bounded_values(cls, values: Any) -> tuple[str, ...]:
        if not isinstance(values, (list, tuple, set, frozenset)):
            return ()
        bounded = {text for item in values if (text := cls._bounded_text(item)) is not None}
        return tuple(sorted(bounded)[: cls._MAX_ITEMS])

    @classmethod
    def _signal_names(cls, values: Any) -> tuple[str, ...]:
        if not isinstance(values, (list, tuple)):
            return ()
        names = set()
        for item in values:
            text = cls._bounded_text(getattr(item, "name", None))
            if text is not None and re.fullmatch(r"[a-z0-9_.:-]{1,64}", text):
                names.add(text)
        return tuple(sorted(names)[: cls._MAX_ITEMS])

    @classmethod
    def _safe_error(cls, exc: Exception) -> str:
        text = re.sub(r"\s+", " ", str(exc)).strip()
        return (text or type(exc).__name__)[: cls._MAX_TEXT]

    def inspect(self, path: Path, mime_type: str) -> RemovalPackageAssessment:
        normalized_mime = mime_type.lower()
        if normalized_mime not in self._SUPPORTED_MIME_TYPES:
            return RemovalPackageAssessment(
                status=RemovalPackageStatus.UNSUPPORTED,
                provider=REMOVAL_PACKAGE_PROVIDER,
                summary=f"Detection-only inspection is not applicable to MIME type {mime_type}.",
                applicable=False,
            )

        try:
            size_bytes = path.stat().st_size
        except OSError as exc:
            return RemovalPackageAssessment(
                status=RemovalPackageStatus.ERROR,
                provider=REMOVAL_PACKAGE_PROVIDER,
                summary=f"Cannot stat asset before package inspection: {self._safe_error(exc)}",
            )
        if size_bytes > self._MAX_ASSET_BYTES:
            return RemovalPackageAssessment(
                status=RemovalPackageStatus.ERROR,
                provider=REMOVAL_PACKAGE_PROVIDER,
                summary=(
                    "Asset exceeds the 100 MiB offline watermark-inspection limit; "
                    "create a separately reviewed bounded derivative."
                ),
            )

        try:
            provider_version = self._bounded_text(self._version_loader())
            if provider_version != REMOVAL_PACKAGE_VERSION:
                return RemovalPackageAssessment(
                    status=RemovalPackageStatus.ERROR,
                    provider=REMOVAL_PACKAGE_PROVIDER,
                    provider_version=provider_version,
                    summary=(
                        "Watermark-removal package version mismatch: expected "
                        f"{REMOVAL_PACKAGE_VERSION}."
                    ),
                )
            capabilities = self._capabilities_loader()
            decoded = self._validate_decodable_image(path, capabilities)
            inspect_pixels = self._pixel_inspector_loader()
            report = inspect_pixels(path, decoded)
        except (
            ImportError,
            ModuleNotFoundError,
            importlib.metadata.PackageNotFoundError,
        ) as exc:
            return RemovalPackageAssessment(
                status=RemovalPackageStatus.UNSUPPORTED,
                provider=REMOVAL_PACKAGE_PROVIDER,
                summary=f"Optional visible-check dependency is unavailable: {self._safe_error(exc)}",
            )
        except Exception as exc:
            return RemovalPackageAssessment(
                status=RemovalPackageStatus.ERROR,
                provider=REMOVAL_PACKAGE_PROVIDER,
                summary=f"Detection-only package inspection failed: {self._safe_error(exc)}",
            )

        watermarks = self._bounded_values(getattr(report, "watermarks", None))
        signal_names = self._signal_names(getattr(report, "signals", None))
        integrity_clashes = self._bounded_values(getattr(report, "integrity_clashes", None))
        ai_generated_value = getattr(report, "is_ai_generated", None)
        ai_generated = ai_generated_value if isinstance(ai_generated_value, bool) else None
        detected = bool(watermarks or integrity_clashes)
        if detected:
            status = RemovalPackageStatus.DETECTED
            summary = (
                "Pinned removal package identified watermark/provenance signals; "
                "documented human review is required."
            )
        else:
            status = RemovalPackageStatus.NOT_DETECTED
            summary = (
                "No supported watermark was identified by the pinned removal package; "
                "this does not prove the asset is clean."
            )

        return RemovalPackageAssessment(
            status=status,
            provider=REMOVAL_PACKAGE_PROVIDER,
            provider_version=provider_version,
            summary=summary,
            watermarks=watermarks,
            signal_names=signal_names,
            platform=self._bounded_text(getattr(report, "platform", None)),
            confidence=self._bounded_text(getattr(report, "confidence", None)),
            ai_generated=ai_generated,
            integrity_clashes=integrity_clashes,
            checks_completed=REMOVAL_PACKAGE_REQUIRED_CHECKS,
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


def reinspect_content_integrity(
    path: str | Path,
    *,
    asset_path: str | None = None,
) -> ContentIntegrityReceipt:
    """Reinspect current bytes using only infrastructure adapters.

    Persistence gates use this same-layer entry point so they do not depend on
    the Application service.  The implementation intentionally mirrors the
    Application orchestration boundary: adapter failures become explicit,
    fail-closed assessments and the source file is hashed before and after.
    """
    candidate = Path(path)
    if not candidate.is_file():
        raise ValueError(f"Asset is not a readable file: {candidate}")

    declared_mime_type = (
        {".webp": "image/webp"}.get(candidate.suffix.lower())
        or mimetypes.guess_type(candidate.name)[0]
        or "application/octet-stream"
    )
    with candidate.open("rb") as stream:
        content_mime_type = detect_raster_mime_signature(stream.read(16))
    mime_type = content_mime_type or declared_mime_type
    mime_type_mismatch = content_mime_type is not None and content_mime_type != declared_mime_type

    def sha256() -> str:
        digest = hashlib.sha256()
        with candidate.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    before_hash = sha256()
    size_bytes = candidate.stat().st_size
    try:
        provenance = C2paProvenanceAdapter().inspect(candidate, mime_type)
    except Exception as exc:  # pragma: no cover - defensive adapter boundary
        provenance = ProvenanceAssessment(
            status=ProvenanceStatus.ERROR,
            provider="unknown",
            summary=f"Provenance adapter failed: {type(exc).__name__}",
        )
    try:
        visible_watermark = ConservativeVisibleWatermarkHeuristic().inspect(candidate, mime_type)
    except Exception as exc:  # pragma: no cover - defensive adapter boundary
        visible_watermark = VisibleWatermarkAssessment(
            status=VisibleWatermarkStatus.HUMAN_REVIEW,
            summary=f"Visible-watermark heuristic failed: {type(exc).__name__}",
            signals=("heuristic_error",),
            applicable=mime_type.startswith("image/"),
        )
    try:
        removal_package_check = RemoveAiWatermarksInspectionAdapter().inspect(candidate, mime_type)
    except Exception as exc:  # pragma: no cover - defensive adapter boundary
        removal_package_check = RemovalPackageAssessment(
            status=RemovalPackageStatus.ERROR,
            provider=REMOVAL_PACKAGE_PROVIDER,
            summary=f"Watermark-removal package check failed: {type(exc).__name__}",
            applicable=mime_type.lower() in {"image/jpeg", "image/png", "image/webp"},
        )

    after_hash = sha256()
    original_preserved = before_hash == after_hash
    gate_status, gate_reasons = decide_integrity_gate(
        provenance,
        visible_watermark,
        removal_package_check,
        original_preserved=original_preserved,
        mime_type=mime_type,
        mime_type_mismatch=mime_type_mismatch,
    )
    return ContentIntegrityReceipt(
        asset_path=asset_path or candidate.as_posix(),
        inspected_at=datetime.now(timezone.utc).isoformat(),
        sha256=before_hash,
        sha256_after_inspection=after_hash,
        mime_type=mime_type,
        size_bytes=size_bytes,
        declared_mime_type=declared_mime_type,
        content_mime_type=content_mime_type,
        mime_type_mismatch=mime_type_mismatch,
        provenance=provenance,
        visible_watermark=visible_watermark,
        removal_package_check=removal_package_check,
        gate_status=gate_status,
        gate_reasons=gate_reasons,
        original_preserved=original_preserved,
    )
