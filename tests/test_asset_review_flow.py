"""Tests for asset review receipts before figure/table insertion."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from med_paper_assistant.application.content_integrity import ContentIntegrityInspector
from med_paper_assistant.domain.value_objects.content_integrity import (
    ProvenanceAssessment,
    ProvenanceStatus,
)
from med_paper_assistant.infrastructure.external.content_integrity import (
    C2paProvenanceAdapter,
    ConservativeVisibleWatermarkHeuristic,
    RemoveAiWatermarksInspectionAdapter,
)
from med_paper_assistant.infrastructure.persistence import ProjectManager, _reset_project_manager
from med_paper_assistant.infrastructure.persistence.data_artifact_tracker import DataArtifactTracker
from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager
from med_paper_assistant.interfaces.mcp.tools.analysis.figures import register_figure_tools

_HUMAN_RASTER_REVIEW = (
    "Human reviewer inspected the original raster, found no visible watermark, "
    "and confirmed authorized reuse."
)


def _write_test_png(path: Path) -> None:
    from PIL import Image

    Image.new("RGB", (320, 320), color=(220, 225, 230)).save(path, format="PNG")


class TestCaptionNormalization:
    """Unit tests for caption normalization logic."""

    def test_trailing_period_ignored(self):
        assert DataArtifactTracker._normalize_caption(
            "Hello."
        ) == DataArtifactTracker._normalize_caption("Hello")

    def test_case_insensitive(self):
        assert DataArtifactTracker._normalize_caption(
            "CONSORT Flow"
        ) == DataArtifactTracker._normalize_caption("consort flow")

    def test_trailing_comma_ignored(self):
        assert DataArtifactTracker._normalize_caption(
            "Table 1,"
        ) == DataArtifactTracker._normalize_caption("Table 1")

    def test_whitespace_stripped(self):
        assert DataArtifactTracker._normalize_caption(
            "  Hello  "
        ) == DataArtifactTracker._normalize_caption("Hello")


@pytest.fixture()
def figure_tool_funcs(tmp_path: Path, monkeypatch):
    project_dir = tmp_path / "project"
    (project_dir / "results" / "figures").mkdir(parents=True)
    (project_dir / "results" / "tables").mkdir(parents=True)
    (project_dir / ".audit").mkdir(parents=True)
    (project_dir / "drafts").mkdir(parents=True)
    _write_test_png(project_dir / "results" / "figures" / "consort.png")
    (project_dir / "results" / "tables" / "baseline.md").write_text("|A|B|\n|---|---|\n|1|2|")

    _reset_project_manager()
    pm = ProjectManager(base_path=str(tmp_path))
    pm.create_project(name="Project", paper_type="original-research")
    pm.switch_project("project")

    monkeypatch.setattr(
        "med_paper_assistant.interfaces.mcp.tools.analysis.figures.ensure_project_context",
        lambda project=None: (True, "", {"slug": "project", "project_path": str(project_dir)}),
    )
    monkeypatch.setattr(
        "med_paper_assistant.interfaces.mcp.tools.analysis.figures._get_project_path",
        lambda project=None: str(project_dir),
    )
    monkeypatch.setattr(
        "med_paper_assistant.interfaces.mcp.tools.analysis.figures.resolve_project_context",
        lambda project=None, required_mode="manuscript", project_manager=None: (
            {"slug": "project", "project_path": str(project_dir)},
            None,
        ),
    )

    mock_mcp = MagicMock()
    captured = {}

    def fake_tool(*args, **kwargs):
        def decorator(fn):
            captured[fn.__name__] = fn
            return fn

        return decorator

    mock_mcp.tool = fake_tool

    mock_drafter = MagicMock()
    mock_drafter.drafts_dir = str(project_dir / "drafts")
    mock_drafter.ref_manager = ReferenceManager(base_dir=str(project_dir / "references"))
    register_figure_tools(mock_mcp, mock_drafter)

    yield captured, project_dir
    _reset_project_manager()


def test_insert_figure_blocked_without_review_receipt(figure_tool_funcs):
    tool_funcs, _project_dir = figure_tool_funcs

    result = tool_funcs["insert_figure"](
        filename="consort.png",
        caption="CONSORT flow diagram",
        project="project",
    )

    assert "caption blocked" in result
    assert "review_asset_for_insertion" in result


def test_review_then_insert_figure_passes(figure_tool_funcs):
    tool_funcs, project_dir = figure_tool_funcs

    review_result = tool_funcs["review_asset_for_insertion"](
        asset_type="figure",
        filename="consort.png",
        observations="Two-arm flow|Enrollment and allocation counts shown",
        rationale="The caption accurately states the asset is a CONSORT-style flow diagram.",
        proposed_caption="CONSORT flow diagram",
        evidence_excerpt="Allocation counts visible",
        project="project",
        visible_watermark_review=_HUMAN_RASTER_REVIEW,
    )
    assert "Asset Review Recorded" in review_result
    assert "Automated removal:** disabled" in review_result

    audit = yaml.safe_load((project_dir / ".audit" / "data-artifacts.yaml").read_text())
    integrity_receipt = audit["content_integrity_receipts"][0]
    assert (
        integrity_receipt["file"]["sha256"] == integrity_receipt["file"]["sha256_after_inspection"]
    )
    assert integrity_receipt["original_preserved"] is True
    assert integrity_receipt["automated_removal_performed"] is False

    insert_result = tool_funcs["insert_figure"](
        filename="consort.png",
        caption="CONSORT flow diagram",
        project="project",
    )
    assert "Figure 1 Registered" in insert_result
    assert (project_dir / "results" / "manifest.json").exists()
    figure_note = project_dir / "notes" / "figures" / "figure-1-consort.md"
    assert figure_note.exists()
    figure_note_text = figure_note.read_text(encoding="utf-8")
    assert "^asset-summary" in figure_note_text
    assert "^review-observation-1" in figure_note_text


def test_insert_table_blocked_when_caption_differs_from_review(figure_tool_funcs):
    tool_funcs, _project_dir = figure_tool_funcs

    tool_funcs["review_asset_for_insertion"](
        asset_type="table",
        filename="baseline.md",
        observations="Two columns present|Contains baseline counts",
        rationale="The reviewed caption describes the displayed baseline summary.",
        proposed_caption="Baseline characteristics table",
        project="project",
    )

    insert_result = tool_funcs["insert_table"](
        filename="baseline.md",
        caption="Different caption after review",
        project="project",
    )

    assert "caption blocked" in insert_result
    assert "reviewed proposed_caption" in insert_result


def test_caption_normalized_comparison_ignores_trailing_punctuation(figure_tool_funcs):
    """Caption matching should be case/punctuation tolerant."""
    tool_funcs, _project_dir = figure_tool_funcs

    tool_funcs["review_asset_for_insertion"](
        asset_type="figure",
        filename="consort.png",
        observations="Two-arm flow|Enrollment and allocation counts shown",
        rationale="The caption fits the asset.",
        proposed_caption="CONSORT flow diagram",
        project="project",
        visible_watermark_review=_HUMAN_RASTER_REVIEW,
    )

    # Same caption with trailing period and different case — should still pass
    insert_result = tool_funcs["insert_figure"](
        filename="consort.png",
        caption="CONSORT flow diagram.",
        project="project",
    )
    assert "Figure 1 Registered" in insert_result


def test_insert_table_with_inline_content_auto_reviews(figure_tool_funcs):
    """When table_content is provided, review receipt is auto-generated — no manual review needed."""
    tool_funcs, project_dir = figure_tool_funcs

    insert_result = tool_funcs["insert_table"](
        filename="auto_table.md",
        caption="Auto-generated table",
        table_content="|Col A|Col B|\n|---|---|\n|1|2|\n|3|4|",
        project="project",
    )

    assert "Table 1 Registered" in insert_result
    assert (project_dir / "results" / "tables" / "auto_table.md").exists()

    # Verify review receipt was auto-recorded
    from med_paper_assistant.infrastructure.persistence import DataArtifactTracker

    tracker = DataArtifactTracker(project_dir / ".audit", project_dir)
    review = tracker.get_asset_review("results/tables/auto_table.md", asset_type="table")
    assert review is not None
    assert "inline" in review["observations"][1].lower()
    assert review["content_integrity_receipt_id"].startswith("CI-")


def test_asset_hash_change_after_review_blocks_insertion(figure_tool_funcs):
    tool_funcs, project_dir = figure_tool_funcs

    tool_funcs["review_asset_for_insertion"](
        asset_type="figure",
        filename="consort.png",
        observations="Two-arm flow|Enrollment and allocation counts shown",
        rationale="The caption fits the reviewed asset.",
        proposed_caption="CONSORT flow diagram",
        project="project",
        visible_watermark_review=_HUMAN_RASTER_REVIEW,
    )
    (project_dir / "results" / "figures" / "consort.png").write_bytes(b"changed")

    result = tool_funcs["insert_figure"](
        filename="consort.png",
        caption="CONSORT flow diagram",
        project="project",
    )

    assert "caption blocked" in result
    assert "SHA-256 changed" in result


def test_visible_watermark_signal_requires_documented_human_review(figure_tool_funcs):
    tool_funcs, project_dir = figure_tool_funcs
    _write_test_png(project_dir / "results" / "figures" / "watermarked-preview.png")
    kwargs = {
        "asset_type": "figure",
        "filename": "watermarked-preview.png",
        "observations": "Visible diagonal overlay|Source label appears in the corner",
        "rationale": "The caption identifies only the reviewed scientific content.",
        "proposed_caption": "Reviewed source figure",
        "project": "project",
    }

    blocked = tool_funcs["review_asset_for_insertion"](**kwargs)
    assert "Human Review Required" in blocked

    reviewed = tool_funcs["review_asset_for_insertion"](
        **kwargs,
        visible_watermark_review=(
            "Human reviewer confirmed the visible source mark must remain and reuse is authorized."
        ),
    )
    assert "Asset Review Recorded" in reviewed


def test_uncertain_raster_requires_documented_human_review(figure_tool_funcs):
    tool_funcs, project_dir = figure_tool_funcs
    kwargs = {
        "asset_type": "figure",
        "filename": "consort.png",
        "observations": "Two-arm flow|Enrollment and allocation counts shown",
        "rationale": "The caption fits the reviewed raster.",
        "proposed_caption": "CONSORT flow diagram",
        "project": "project",
    }

    blocked = tool_funcs["review_asset_for_insertion"](**kwargs)

    assert "Human Review Required" in blocked
    tracker = DataArtifactTracker(project_dir / ".audit", project_dir)
    assert tracker.get_asset_review("results/figures/consort.png", asset_type="figure") is None
    integrity = tracker.get_content_integrity_receipt("results/figures/consort.png")
    assert integrity is not None
    assert integrity["visible_watermark"]["status"] == "UNCERTAIN"
    assert integrity["gate_status"] == "HUMAN_REVIEW"

    reviewed = tool_funcs["review_asset_for_insertion"](
        **kwargs,
        visible_watermark_review=_HUMAN_RASTER_REVIEW,
    )
    assert "Asset Review Recorded" in reviewed


def test_tracker_rejects_pass_receipt_for_uncertain_raster(figure_tool_funcs):
    _tool_funcs, project_dir = figure_tool_funcs
    asset_path = "results/figures/consort.png"
    tracker = DataArtifactTracker(project_dir / ".audit", project_dir)
    integrity = ContentIntegrityInspector(
        provenance_inspector=C2paProvenanceAdapter(),
        visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
        removal_package_inspector=RemoveAiWatermarksInspectionAdapter(),
    ).inspect(project_dir / asset_path, asset_path=asset_path)
    forged_pass = integrity.to_dict()
    forged_pass["gate_status"] = "PASS"
    forged_pass["visible_watermark"]["applicable"] = False
    receipt = tracker.record_content_integrity_receipt(
        asset_type="figure",
        asset_path=asset_path,
        receipt=forged_pass,
    )
    tracker.record_asset_review(
        asset_type="figure",
        asset_path=asset_path,
        observations=["Two-arm flow", "Enrollment counts shown"],
        rationale="Caption fits the reviewed raster.",
        proposed_caption="CONSORT flow diagram",
        content_integrity_receipt_id=receipt["id"],
        visible_watermark_review=_HUMAN_RASTER_REVIEW,
    )

    ok, detail = tracker.review_satisfies_caption(
        asset_path,
        "CONSORT flow diagram",
        asset_type="figure",
    )

    assert ok is False
    assert "weaker than the recomputed decision" in detail


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("provider_version", "99.0.0", "unpinned"),
        ("derivative_written", True, "no derivative"),
        ("automated_removal_performed", True, "removal was disabled"),
        ("checks_completed", [], "complete every required pixel check"),
    ],
)
def test_tracker_rejects_tampered_removal_package_receipt(
    figure_tool_funcs,
    field,
    value,
    expected,
):
    _tool_funcs, project_dir = figure_tool_funcs
    asset_path = "results/figures/consort.png"
    tracker = DataArtifactTracker(project_dir / ".audit", project_dir)
    receipt_payload = (
        ContentIntegrityInspector(
            provenance_inspector=C2paProvenanceAdapter(),
            visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
            removal_package_inspector=RemoveAiWatermarksInspectionAdapter(),
        )
        .inspect(project_dir / asset_path, asset_path=asset_path)
        .to_dict()
    )
    receipt_payload["removal_package_check"][field] = value
    receipt = tracker.record_content_integrity_receipt(
        asset_type="figure",
        asset_path=asset_path,
        receipt=receipt_payload,
    )
    tracker.record_asset_review(
        asset_type="figure",
        asset_path=asset_path,
        observations=["Two-arm flow", "Enrollment counts shown"],
        rationale="Caption fits the reviewed raster.",
        proposed_caption="CONSORT flow diagram",
        content_integrity_receipt_id=receipt["id"],
        visible_watermark_review=_HUMAN_RASTER_REVIEW,
    )

    ok, detail = tracker.review_satisfies_caption(
        asset_path,
        "CONSORT flow diagram",
        asset_type="figure",
    )

    assert ok is False
    assert expected in detail


@pytest.mark.parametrize("status", ["PRESENT_INVALID", "ERROR"])
def test_tracker_recomputes_and_rejects_forged_provenance_gate(
    figure_tool_funcs,
    status,
):
    _tool_funcs, project_dir = figure_tool_funcs
    asset_path = "results/figures/consort.png"
    tracker = DataArtifactTracker(project_dir / ".audit", project_dir)
    receipt_payload = (
        ContentIntegrityInspector(
            provenance_inspector=C2paProvenanceAdapter(),
            visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
            removal_package_inspector=RemoveAiWatermarksInspectionAdapter(),
        )
        .inspect(project_dir / asset_path, asset_path=asset_path)
        .to_dict()
    )
    receipt_payload["provenance"]["status"] = status
    receipt_payload["gate_status"] = "HUMAN_REVIEW"
    receipt = tracker.record_content_integrity_receipt(
        asset_type="figure",
        asset_path=asset_path,
        receipt=receipt_payload,
    )
    tracker.record_asset_review(
        asset_type="figure",
        asset_path=asset_path,
        observations=["Two-arm flow", "Enrollment counts shown"],
        rationale="Caption fits the reviewed raster.",
        proposed_caption="CONSORT flow diagram",
        content_integrity_receipt_id=receipt["id"],
        visible_watermark_review=_HUMAN_RASTER_REVIEW,
    )

    ok, detail = tracker.review_satisfies_caption(
        asset_path,
        "CONSORT flow diagram",
        asset_type="figure",
    )

    assert ok is False
    assert "recomputes to a blocked gate" in detail


def test_tracker_rejects_receipt_that_hides_live_invalid_provenance(
    figure_tool_funcs,
    monkeypatch,
):
    """Editing both serialized status and gate cannot bypass current-byte inspection."""
    _tool_funcs, project_dir = figure_tool_funcs
    asset_path = "results/figures/consort.png"
    tracker = DataArtifactTracker(project_dir / ".audit", project_dir)
    receipt_payload = (
        ContentIntegrityInspector(
            provenance_inspector=C2paProvenanceAdapter(),
            visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
            removal_package_inspector=RemoveAiWatermarksInspectionAdapter(),
        )
        .inspect(project_dir / asset_path, asset_path=asset_path)
        .to_dict()
    )
    receipt_payload["provenance"]["status"] = "ABSENT"
    receipt_payload["gate_status"] = "HUMAN_REVIEW"
    receipt = tracker.record_content_integrity_receipt(
        asset_type="figure",
        asset_path=asset_path,
        receipt=receipt_payload,
    )
    tracker.record_asset_review(
        asset_type="figure",
        asset_path=asset_path,
        observations=["Two-arm flow", "Enrollment counts shown"],
        rationale="Caption fits the reviewed raster.",
        proposed_caption="CONSORT flow diagram",
        content_integrity_receipt_id=receipt["id"],
        visible_watermark_review=_HUMAN_RASTER_REVIEW,
    )

    original_reinspect = tracker._inspect_current_content_integrity

    def invalid_live_receipt(candidate, reviewed_path):
        live = original_reinspect(candidate, reviewed_path)
        live["provenance"]["status"] = "PRESENT_INVALID"
        live["gate_status"] = "BLOCK"
        return live

    monkeypatch.setattr(tracker, "_inspect_current_content_integrity", invalid_live_receipt)
    ok, detail = tracker.review_satisfies_caption(
        asset_path,
        "CONSORT flow diagram",
        asset_type="figure",
    )

    assert ok is False
    assert "live content-integrity reinspection blocks" in detail


def test_tracker_rejects_svg_applicability_and_gate_tamper(figure_tool_funcs):
    _tool_funcs, project_dir = figure_tool_funcs
    asset_path = "results/figures/diagram.svg"
    (project_dir / asset_path).write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><text>Evidence flow</text></svg>',
        encoding="utf-8",
    )
    tracker = DataArtifactTracker(project_dir / ".audit", project_dir)
    receipt_payload = (
        ContentIntegrityInspector(
            provenance_inspector=C2paProvenanceAdapter(),
            visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
            removal_package_inspector=RemoveAiWatermarksInspectionAdapter(),
        )
        .inspect(project_dir / asset_path, asset_path=asset_path)
        .to_dict()
    )
    receipt_payload["visible_watermark"]["applicable"] = False
    receipt_payload["gate_status"] = "PASS"
    receipt = tracker.record_content_integrity_receipt(
        asset_type="figure",
        asset_path=asset_path,
        receipt=receipt_payload,
    )
    tracker.record_asset_review(
        asset_type="figure",
        asset_path=asset_path,
        observations=["Evidence flow", "Single text label"],
        rationale="Caption matches the reviewed vector.",
        proposed_caption="Evidence flow diagram",
        content_integrity_receipt_id=receipt["id"],
        visible_watermark_review="Human reviewer inspected the SVG source and approved reuse.",
    )

    ok, detail = tracker.review_satisfies_caption(
        asset_path,
        "Evidence flow diagram",
        asset_type="figure",
    )

    assert ok is False
    assert "differs from live reinspection" in detail or "inconsistently passes" in detail


def test_tracker_rejects_stale_content_integrity_schema(figure_tool_funcs):
    _tool_funcs, project_dir = figure_tool_funcs
    asset_path = "results/figures/consort.png"
    tracker = DataArtifactTracker(project_dir / ".audit", project_dir)
    receipt_payload = (
        ContentIntegrityInspector(
            provenance_inspector=C2paProvenanceAdapter(),
            visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
            removal_package_inspector=RemoveAiWatermarksInspectionAdapter(),
        )
        .inspect(project_dir / asset_path, asset_path=asset_path)
        .to_dict()
    )
    receipt_payload["schema_version"] = "1.0"
    receipt = tracker.record_content_integrity_receipt(
        asset_type="figure",
        asset_path=asset_path,
        receipt=receipt_payload,
    )
    tracker.record_asset_review(
        asset_type="figure",
        asset_path=asset_path,
        observations=["Two-arm flow", "Enrollment counts shown"],
        rationale="Caption fits the reviewed raster.",
        proposed_caption="CONSORT flow diagram",
        content_integrity_receipt_id=receipt["id"],
        visible_watermark_review=_HUMAN_RASTER_REVIEW,
    )

    ok, detail = tracker.review_satisfies_caption(
        asset_path,
        "CONSORT flow diagram",
        asset_type="figure",
    )

    assert ok is False
    assert "schema is stale" in detail


def test_invalid_c2pa_receipt_blocks_review_gate(figure_tool_funcs, monkeypatch):
    tool_funcs, project_dir = figure_tool_funcs

    class InvalidProvenance:
        def inspect(self, _path, _mime_type):
            return ProvenanceAssessment(
                status=ProvenanceStatus.PRESENT_INVALID,
                provider="test-c2pa",
                summary="data hash mismatch",
                failure_codes=("assertion.dataHash.mismatch",),
            )

    inspector = ContentIntegrityInspector(
        provenance_inspector=InvalidProvenance(),
        visible_watermark_inspector=ConservativeVisibleWatermarkHeuristic(),
        removal_package_inspector=RemoveAiWatermarksInspectionAdapter(),
    )
    monkeypatch.setattr(
        "med_paper_assistant.interfaces.mcp.tools.analysis.figures._build_content_integrity_inspector",
        lambda: inspector,
    )

    result = tool_funcs["review_asset_for_insertion"](
        asset_type="figure",
        filename="consort.png",
        observations="Two-arm flow|Enrollment and allocation counts shown",
        rationale="The caption fits the reviewed asset.",
        proposed_caption="CONSORT flow diagram",
        project="project",
    )

    assert "Asset Integrity Gate Blocked" in result
    tracker = DataArtifactTracker(project_dir / ".audit", project_dir)
    assert tracker.get_asset_review("results/figures/consort.png", asset_type="figure") is None
    integrity = tracker.get_content_integrity_receipt("results/figures/consort.png")
    assert integrity is not None
    assert integrity["gate_status"] == "BLOCK"
