"""Tests for the plugin-aware workspace root resolver."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from med_paper_assistant.shared import workspace_root as wr

_ALL_VARS = wr.WORKSPACE_ENV_VARS + wr.PLUGIN_ROOT_ENV_VARS + wr.PLUGIN_DATA_ENV_VARS


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in _ALL_VARS:
        monkeypatch.delenv(name, raising=False)
    wr.clear_workspace_binding()
    yield
    wr.clear_workspace_binding()


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


def test_describe_reports_env_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    assert wr.describe_workspace_root() == (tmp_path.resolve(), "env:CLAUDE_PROJECT_DIR")


def test_describe_reports_cwd_and_plugin_data_sources(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    assert wr.describe_workspace_root() == (tmp_path.resolve(), wr.SOURCE_CWD)

    plugin = tmp_path / "plugin"
    plugin.mkdir()
    monkeypatch.chdir(plugin)
    monkeypatch.setenv("PLUGIN_ROOT", str(plugin))
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path / "data"))
    info = wr.describe_workspace_root()
    assert info.source == wr.SOURCE_PLUGIN_DATA
    assert info.path == (tmp_path / "data" / "workspace").resolve()


def test_binding_overrides_env_until_cleared(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_root = tmp_path / "env"
    bound = tmp_path / "bound"
    bound.mkdir()
    monkeypatch.setenv("MEDPAPER_BASE_DIR", str(env_root))

    assert wr.bind_workspace_root(str(bound)) == bound.resolve()
    assert wr.describe_workspace_root() == (bound.resolve(), wr.SOURCE_BOUND)
    assert wr.resolve_workspace_root() == bound.resolve()

    wr.clear_workspace_binding()
    assert wr.describe_workspace_root() == (env_root.resolve(), "env:MEDPAPER_BASE_DIR")


@pytest.mark.parametrize("value", ["", "   ", "relative/dir"])
def test_binding_rejects_empty_or_relative_paths(value: str) -> None:
    with pytest.raises(ValueError):
        wr.bind_workspace_root(value)
    assert wr.describe_workspace_root().source != wr.SOURCE_BOUND


def test_binding_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        wr.bind_workspace_root(str(tmp_path / "missing"))


def test_binding_rejects_plugin_package(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plugin = tmp_path / "plugin"
    (plugin / "skills").mkdir(parents=True)
    monkeypatch.setenv("PLUGIN_ROOT", str(plugin))
    with pytest.raises(ValueError, match="Agent Plugins package"):
        wr.bind_workspace_root(str(plugin / "skills"))
