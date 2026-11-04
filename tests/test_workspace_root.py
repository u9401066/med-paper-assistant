"""Tests for the plugin-aware workspace root resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from med_paper_assistant.shared import workspace_root as wr

_ALL_VARS = wr.WORKSPACE_ENV_VARS + wr.PLUGIN_ROOT_ENV_VARS + wr.PLUGIN_DATA_ENV_VARS


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ALL_VARS:
        monkeypatch.delenv(name, raising=False)


def test_medpaper_base_dir_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MEDPAPER_BASE_DIR", str(tmp_path / "ws"))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "claude"))
    assert wr.resolve_workspace_root() == (tmp_path / "ws").resolve()


def test_claude_project_dir_used_when_no_explicit_base(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    assert wr.resolve_workspace_root() == tmp_path.resolve()


def test_cwd_used_outside_plugin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PLUGIN_ROOT", str(tmp_path / "elsewhere"))
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path / "data"))
    assert wr.resolve_workspace_root() == tmp_path.resolve()


def test_plugin_root_cwd_redirects_to_plugin_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    monkeypatch.chdir(plugin)
    monkeypatch.setenv("PLUGIN_ROOT", str(plugin))
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path / "data"))
    resolved = wr.resolve_workspace_root()
    assert resolved == (tmp_path / "data" / "workspace").resolve()
    assert resolved.is_dir()


def test_claude_plugin_aliases(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    monkeypatch.chdir(plugin)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin))
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "cdata"))
    assert wr.resolve_workspace_root() == (tmp_path / "cdata" / "workspace").resolve()


def test_plugin_root_without_data_falls_back_to_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PLUGIN_ROOT", str(tmp_path))
    assert wr.resolve_workspace_root() == tmp_path.resolve()


def test_project_manager_uses_resolver(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager

    plugin = tmp_path / "plugin"
    plugin.mkdir()
    monkeypatch.chdir(plugin)
    monkeypatch.setenv("PLUGIN_ROOT", str(plugin))
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path / "data"))
    pm = ProjectManager()
    assert pm.base_path == (tmp_path / "data" / "workspace").resolve()
    assert not (plugin / "projects").exists()
