"""Offline smoke for the pinned watermark-removal package inspection adapter."""

from __future__ import annotations

import hashlib
import socket
from pathlib import Path

import pytest

from med_paper_assistant.application.content_integrity import ContentIntegrityInspector
from med_paper_assistant.domain.value_objects.content_integrity import (
    REMOVAL_PACKAGE_INSPECTION_MODE,
    REMOVAL_PACKAGE_REQUIRED_CHECKS,
    REMOVAL_PACKAGE_VERSION,
    IntegrityGateStatus,
    RemovalPackageStatus,
)
from med_paper_assistant.infrastructure.external.content_integrity import (
    C2paProvenanceAdapter,
    ConservativeVisibleWatermarkHeuristic,
    RemoveAiWatermarksInspectionAdapter,
)

pytestmark = [pytest.mark.integration, pytest.mark.smoke]


def _textured_bgr(size: int = 512):
    import numpy as np

    return np.random.default_rng(0).integers(0, 255, (size, size, 3), dtype=np.uint8)


def _embed_open_dwt_dct(bgr, message: int):
    """Create an authorized synthetic fixture using the upstream MIT matrix method."""
    import cv2
    import numpy as np
    import pywt

    bits = [int(bit) for bit in format(message, "048b")]
    rows, columns, _channels = bgr.shape
    yuv = cv2.cvtColor(bgr, cv2.COLOR_BGR2YUV)
    coefficients, (horizontal, vertical, diagonal) = pywt.dwt2(
        yuv[: rows // 4 * 4, : columns // 4 * 4, 1], "haar"
    )
    block_size = 4
    scale = 36
    bit_index = 0
    for row in range(coefficients.shape[0] // block_size):
        for column in range(coefficients.shape[1] // block_size):
            block = coefficients[
                row * block_size : row * block_size + block_size,
                column * block_size : column * block_size + block_size,
            ]
            position = int(np.argmax(np.abs(block.flatten()[1:]))) + 1
            coefficient_row, coefficient_column = divmod(position, block_size)
            value = float(block[coefficient_row, coefficient_column])
            magnitude = abs(value)
            encoded = (magnitude // scale + 0.25 + 0.5 * bits[bit_index % len(bits)]) * scale
            block[coefficient_row, coefficient_column] = encoded if value >= 0 else -encoded
            bit_index += 1

    yuv[: rows // 4 * 4, : columns // 4 * 4, 1] = pywt.idwt2(
        (coefficients, (vertical, horizontal, diagonal)), "haar"
    )
    return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)


def test_pinned_removal_package_detects_synthetic_mark_without_writing_derivative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the real pinned detector on an upstream-algorithm synthetic mark."""
    import numpy as np
    from PIL import Image
    from remove_ai_watermarks.gemini_engine import GeminiEngine, get_watermark_config

    size = 1400
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    base = 145 + 18 * np.sin(xx / 40.0) + 14 * np.cos(yy / 55.0)
    image = np.clip(np.stack([base, base * 0.97, base * 1.03], axis=-1), 0, 255)
    engine = GeminiEngine()
    config = get_watermark_config(size, size)
    x, y = config.get_position(size, size)
    alpha = engine.get_interpolated_alpha(config.logo_size)
    height, width = alpha.shape
    roi = image[y : y + height, x : x + width]
    image[y : y + height, x : x + width] = (
        alpha[:, :, None] * 255.0 + (1.0 - alpha[:, :, None]) * roi
    )

    asset = tmp_path / "authorized-synthetic-gemini-mark.png"
    Image.fromarray(np.clip(image[..., ::-1], 0, 255).astype(np.uint8)).save(asset)
    before = hashlib.sha256(asset.read_bytes()).hexdigest()

    def deny_network(*_args, **_kwargs):
        raise AssertionError("watermark inspection must remain offline")

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setattr(
        "remove_ai_watermarks._internal.c2pa._manifest_json_uncached",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("package C2PA reader must not run in the pixel-only adapter")
        ),
    )
    monkeypatch.setattr(
        "remove_ai_watermarks.identify.extract_provenance_evidence",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("default metadata extraction must not run in the pixel-only adapter")
        ),
    )
    receipt = ContentIntegrityInspector(
        provenance_inspector=C2paProvenanceAdapter(),
        visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
        removal_package_inspector=RemoveAiWatermarksInspectionAdapter(),
    ).inspect(asset, asset_path="results/figures/authorized-synthetic-gemini-mark.png")

    after = hashlib.sha256(asset.read_bytes()).hexdigest()
    package_check = receipt.removal_package_check
    assert package_check.status is RemovalPackageStatus.DETECTED
    assert package_check.provider_version == REMOVAL_PACKAGE_VERSION
    assert any("Gemini" in watermark for watermark in package_check.watermarks)
    assert package_check.inspection_mode == REMOVAL_PACKAGE_INSPECTION_MODE
    assert package_check.checks_completed == REMOVAL_PACKAGE_REQUIRED_CHECKS
    assert package_check.automated_removal_performed is False
    assert package_check.derivative_written is False
    assert receipt.gate_status is IntegrityGateStatus.HUMAN_REVIEW
    assert receipt.original_preserved is True
    assert before == receipt.sha256 == receipt.sha256_after_inspection == after
    assert list(tmp_path.iterdir()) == [asset]


def test_pinned_removal_package_detects_open_dwt_dct_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cv2

    # Stable Diffusion XL's published 48-bit marker used by the upstream decoder.
    marked = _embed_open_dwt_dct(_textured_bgr(), 197828617679262)
    asset = tmp_path / "authorized-synthetic-sdxl-dwt.png"
    assert cv2.imwrite(str(asset), marked)
    before = hashlib.sha256(asset.read_bytes()).hexdigest()

    def deny_network(*_args, **_kwargs):
        raise AssertionError("open DWT-DCT inspection must remain offline")

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    result = RemoveAiWatermarksInspectionAdapter().inspect(asset, "image/png")

    assert result.status is RemovalPackageStatus.DETECTED
    assert result.provider_version == REMOVAL_PACKAGE_VERSION
    assert "Open invisible watermark: Stable Diffusion XL" in result.watermarks
    assert "invisible_watermark" in result.signal_names
    assert result.checks_completed == REMOVAL_PACKAGE_REQUIRED_CHECKS
    assert hashlib.sha256(asset.read_bytes()).hexdigest() == before
    assert list(tmp_path.iterdir()) == [asset]


def test_negative_package_result_never_turns_raster_gate_clean(tmp_path: Path) -> None:
    import cv2

    asset = tmp_path / "authorized-negative-control.png"
    assert cv2.imwrite(str(asset), _textured_bgr())
    receipt = ContentIntegrityInspector(
        provenance_inspector=C2paProvenanceAdapter(),
        visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
        removal_package_inspector=RemoveAiWatermarksInspectionAdapter(),
    ).inspect(asset)

    assert receipt.removal_package_check.status is RemovalPackageStatus.NOT_DETECTED
    assert receipt.gate_status is IntegrityGateStatus.HUMAN_REVIEW
    assert "CLEAN" not in {status.value for status in RemovalPackageStatus}
    assert list(tmp_path.iterdir()) == [asset]
