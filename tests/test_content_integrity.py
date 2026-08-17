"""Smoke tests for read-only provenance and watermark integrity inspection."""

from __future__ import annotations

import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from med_paper_assistant.application.content_integrity import ContentIntegrityInspector
from med_paper_assistant.domain.value_objects.content_integrity import (
    IntegrityGateStatus,
    ProvenanceAssessment,
    ProvenanceStatus,
    VisibleWatermarkAssessment,
    VisibleWatermarkStatus,
    decide_integrity_gate,
)
from med_paper_assistant.infrastructure.external.content_integrity import (
    C2paProvenanceAdapter,
    ConservativeVisibleWatermarkHeuristic,
)


class _FakeSettings:
    @staticmethod
    def from_dict(config):
        return config


class _FakeContext:
    def __init__(self, settings):
        self.settings = settings

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class _FakeReader:
    def __init__(self, state: str, failure_codes: tuple[str, ...] = ()):
        self._state = state
        self._failure_codes = failure_codes

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def get_validation_state(self):
        return self._state

    def get_validation_results(self):
        return {"activeManifest": {"failure": [{"code": code} for code in self._failure_codes]}}

    def is_embedded(self):
        return True


def _fake_c2pa(reader: _FakeReader | None):
    class ReaderFactory:
        @staticmethod
        def try_create(_path, context):
            assert context.settings["verify"]["remote_manifest_fetch"] is False
            return reader

    return SimpleNamespace(Settings=_FakeSettings, Context=_FakeContext, Reader=ReaderFactory)


@pytest.mark.parametrize(
    ("reader", "expected"),
    [
        (_FakeReader("Trusted"), ProvenanceStatus.PRESENT_VALID_TRUSTED),
        (_FakeReader("Valid"), ProvenanceStatus.PRESENT_VALID_UNTRUSTED),
        (None, ProvenanceStatus.ABSENT),
        (
            _FakeReader("Invalid", ("assertion.dataHash.mismatch",)),
            ProvenanceStatus.PRESENT_INVALID,
        ),
    ],
)
def test_c2pa_adapter_classifies_clean_absent_and_invalid(tmp_path: Path, reader, expected):
    asset = tmp_path / "figure.png"
    asset.write_bytes(b"image bytes")
    adapter = C2paProvenanceAdapter(module_loader=lambda: _fake_c2pa(reader))

    result = adapter.inspect(asset, "image/png")

    assert result.status is expected


def test_c2pa_adapter_missing_optional_dependency_is_unsupported(tmp_path: Path):
    asset = tmp_path / "figure.png"
    asset.write_bytes(b"image bytes")

    def missing_module():
        raise ModuleNotFoundError("No module named 'c2pa'")

    result = C2paProvenanceAdapter(module_loader=missing_module).inspect(asset, "image/png")

    assert result.status is ProvenanceStatus.UNSUPPORTED


def test_inspector_preserves_hash_mime_and_original_bytes(tmp_path: Path):
    asset = tmp_path / "clean.png"
    original = b"not-a-decoded-image-but-stable-test-bytes"
    asset.write_bytes(original)
    inspector = ContentIntegrityInspector(
        provenance_inspector=C2paProvenanceAdapter(
            module_loader=lambda: _fake_c2pa(_FakeReader("Trusted"))
        ),
        visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
    )

    receipt = inspector.inspect(asset, asset_path="results/figures/clean.png")

    assert receipt.gate_status is IntegrityGateStatus.HUMAN_REVIEW
    assert receipt.visible_watermark.status is VisibleWatermarkStatus.UNCERTAIN
    assert receipt.mime_type == "image/png"
    assert receipt.sha256 == receipt.sha256_after_inspection
    assert receipt.original_preserved is True
    assert receipt.automated_removal_performed is False
    assert asset.read_bytes() == original


@pytest.mark.parametrize("status", [ProvenanceStatus.ABSENT, ProvenanceStatus.UNSUPPORTED])
@pytest.mark.parametrize("filename", ["asset.png", "asset.jpg", "asset.jpeg"])
def test_absent_or_unsupported_provenance_does_not_bypass_raster_review(
    tmp_path: Path,
    status,
    filename: str,
):
    asset = tmp_path / filename
    asset.write_bytes(b"stable")

    class StaticProvenance:
        def inspect(self, _path, _mime_type):
            return ProvenanceAssessment(status=status, provider="test", summary="test")

    inspector = ContentIntegrityInspector(
        provenance_inspector=StaticProvenance(),
        visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
    )

    assert inspector.inspect(asset).gate_status is IntegrityGateStatus.HUMAN_REVIEW


def test_non_image_uncertain_screening_is_not_applicable_and_can_pass(tmp_path: Path):
    asset = tmp_path / "table.md"
    asset.write_text("| A |\n|---|\n| 1 |", encoding="utf-8")

    class StaticProvenance:
        def inspect(self, _path, _mime_type):
            return ProvenanceAssessment(
                status=ProvenanceStatus.UNSUPPORTED,
                provider="test",
                summary="not applicable",
            )

    receipt = ContentIntegrityInspector(
        provenance_inspector=StaticProvenance(),
        visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
    ).inspect(asset)

    assert receipt.visible_watermark.status is VisibleWatermarkStatus.UNCERTAIN
    assert receipt.visible_watermark.applicable is False
    assert receipt.gate_status is IntegrityGateStatus.PASS


@pytest.mark.parametrize("mime_type", ["image/png", "image/jpeg"])
def test_raster_mime_fails_closed_even_if_adapter_marks_screening_not_applicable(
    mime_type: str,
):
    status, reasons = decide_integrity_gate(
        ProvenanceAssessment(
            status=ProvenanceStatus.ABSENT,
            provider="test",
            summary="absent",
        ),
        VisibleWatermarkAssessment(
            status=VisibleWatermarkStatus.UNCERTAIN,
            summary="adapter could not determine",
            applicable=False,
        ),
        original_preserved=True,
        mime_type=mime_type,
    )

    assert status is IntegrityGateStatus.HUMAN_REVIEW
    assert "inconclusive" in reasons[0]


def test_invalid_provenance_blocks_gate(tmp_path: Path):
    asset = tmp_path / "asset.png"
    asset.write_bytes(b"stable")

    class InvalidProvenance:
        def inspect(self, _path, _mime_type):
            return ProvenanceAssessment(
                status=ProvenanceStatus.PRESENT_INVALID,
                provider="test",
                summary="invalid",
            )

    inspector = ContentIntegrityInspector(
        provenance_inspector=InvalidProvenance(),
        visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
    )

    assert inspector.inspect(asset).gate_status is IntegrityGateStatus.BLOCK


def test_visible_watermark_heuristic_never_claims_clean(tmp_path: Path):
    ordinary = tmp_path / "ordinary.png"
    suspicious = tmp_path / "watermarked-preview.png"
    ordinary.write_bytes(b"image")
    suspicious.write_bytes(b"image")
    heuristic = ConservativeVisibleWatermarkHeuristic()

    ordinary_result = heuristic.inspect(ordinary, "image/png")
    suspicious_result = heuristic.inspect(suspicious, "image/png")

    assert ordinary_result.status is VisibleWatermarkStatus.UNCERTAIN
    assert suspicious_result.status is VisibleWatermarkStatus.HUMAN_REVIEW
    assert {ordinary_result.status, suspicious_result.status} <= {
        VisibleWatermarkStatus.UNCERTAIN,
        VisibleWatermarkStatus.HUMAN_REVIEW,
    }


def test_changed_bytes_are_detected_and_blocked(tmp_path: Path):
    asset = tmp_path / "asset.png"
    asset.write_bytes(b"before")

    class MutatingProvenance:
        def inspect(self, path, _mime_type):
            path.write_bytes(b"after")
            return ProvenanceAssessment(
                status=ProvenanceStatus.ABSENT,
                provider="test",
                summary="test mutation",
            )

    class UncertainVisible:
        def inspect(self, _path, _mime_type):
            return VisibleWatermarkAssessment(
                status=VisibleWatermarkStatus.UNCERTAIN,
                summary="uncertain",
            )

    receipt = ContentIntegrityInspector(
        provenance_inspector=MutatingProvenance(),
        visible_watermark_inspector=UncertainVisible(),
    ).inspect(asset)

    assert receipt.original_preserved is False
    assert receipt.gate_status is IntegrityGateStatus.BLOCK


def test_provenance_extra_declares_the_read_only_c2pa_sdk() -> None:
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert pyproject["project"]["optional-dependencies"]["provenance"] == [
        "c2pa-python>=0.37.1,<0.38"
    ]
