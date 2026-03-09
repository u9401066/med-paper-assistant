"""Tests for figure embedding helpers used by autopaper/export workflows."""

from __future__ import annotations

import base64

from med_paper_assistant.interfaces.mcp.tools.analysis.figures import (
    _build_figure_insertion_markdown,
    _to_markdown_asset_path,
)
from med_paper_assistant.interfaces.mcp.tools.project.diagrams import (
    _save_companion_rendered_asset,
)


def test_build_figure_insertion_markdown_prefers_companion_asset(tmp_path):
    project_dir = tmp_path / "project"
    drafts_dir = project_dir / "drafts"
    figures_dir = project_dir / "results" / "figures"
    drafts_dir.mkdir(parents=True)
    figures_dir.mkdir(parents=True)

    (figures_dir / "consort.drawio").write_text("<mxfile />", encoding="utf-8")
    (figures_dir / "consort.png").write_bytes(b"png-bytes")

    markdown, asset_path = _build_figure_insertion_markdown(
        str(project_dir),
        "consort.drawio",
        "CONSORT patient flow.",
        1,
    )

    assert asset_path == str(figures_dir / "consort.png")
    assert "![Figure 1. CONSORT patient flow.]" in markdown
    assert "../results/figures/consort.png" in markdown
    assert "**Figure 1.** CONSORT patient flow." in markdown


def test_build_figure_insertion_markdown_falls_back_to_caption_only(tmp_path):
    project_dir = tmp_path / "project"
    figures_dir = project_dir / "results" / "figures"
    figures_dir.mkdir(parents=True)
    (figures_dir / "prisma.drawio").write_text("<mxfile />", encoding="utf-8")

    markdown, asset_path = _build_figure_insertion_markdown(
        str(project_dir),
        "prisma.drawio",
        "PRISMA selection flow.",
        2,
    )

    assert asset_path is None
    assert markdown.strip() == "**Figure 2.** PRISMA selection flow."


def test_save_companion_rendered_asset_writes_binary_png(tmp_path):
    diagram_path = tmp_path / "study-flow.drawio"
    diagram_path.write_text("<mxfile />", encoding="utf-8")
    png_payload = base64.b64encode(b"fake-png-binary").decode("ascii")

    asset_path = _save_companion_rendered_asset(
        diagram_path,
        png_payload,
        "png",
        "auto",
    )

    assert asset_path.name == "study-flow.png"
    assert asset_path.read_bytes() == b"fake-png-binary"


def test_to_markdown_asset_path_normalizes_windows_separators(monkeypatch, tmp_path):
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir()

    monkeypatch.setattr(
        "med_paper_assistant.interfaces.mcp.tools.analysis.figures.os.path.relpath",
        lambda asset_path, start: "..\\results\\figures\\consort.png",
    )

    markdown_path = _to_markdown_asset_path(
        str(tmp_path / "results" / "figures" / "consort.png"),
        drafts_dir,
    )

    assert markdown_path == "../results/figures/consort.png"
