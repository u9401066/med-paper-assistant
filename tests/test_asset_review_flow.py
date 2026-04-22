"""Tests for asset review receipts before figure/table insertion."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from med_paper_assistant.infrastructure.persistence import ProjectManager, _reset_project_manager
from med_paper_assistant.infrastructure.persistence.data_artifact_tracker import DataArtifactTracker
from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager
from med_paper_assistant.interfaces.mcp.tools.analysis.figures import register_figure_tools


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
    (project_dir / "results" / "figures" / "consort.png").write_bytes(b"png")
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
        "med_paper_assistant.interfaces.mcp.tools.analysis.figures.validate_project_for_workflow",
        lambda project=None, required_mode="manuscript": (True, ""),
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
    )
    assert "Asset Review Recorded" in review_result

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
