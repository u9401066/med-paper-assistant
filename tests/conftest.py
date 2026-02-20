"""Shared test fixtures for med-paper-assistant."""

import pytest


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with standard structure."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    (project_dir / "references").mkdir()
    (project_dir / "drafts").mkdir()
    (project_dir / ".memory").mkdir()
    (project_dir / ".memory" / "activeContext.md").write_text("# Active Context\n")
    (project_dir / ".memory" / "progress.md").write_text("# Progress\n")
    return project_dir


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch, tmp_path):
    """Ensure tests don't accidentally write to real project directories."""
    monkeypatch.setenv("MDPAPER_TEST_MODE", "1")
