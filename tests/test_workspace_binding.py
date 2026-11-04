"""Tests for binding the running MCP server to an explicit workspace folder."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from mcp.server import MCPServer

from med_paper_assistant.infrastructure.persistence import (
    _reset_project_manager,
    get_project_manager,
    get_workspace_state_manager,
    reset_workspace_state_manager,
)
from med_paper_assistant.interfaces.mcp.tools._shared import tool_logging
from med_paper_assistant.interfaces.mcp.tools._shared.workspace_binding import (
    workspace_binding_info,
)
from med_paper_assistant.interfaces.mcp.tools.project.workspace_state import (
    register_workspace_state_tools,
)
from med_paper_assistant.shared import workspace_root as wr

_ALL_VARS = wr.WORKSPACE_ENV_VARS + wr.PLUGIN_ROOT_ENV_VARS + wr.PLUGIN_DATA_ENV_VARS


def _reset_singletons() -> None:
    wr.clear_workspace_binding()
    _reset_project_manager()
    reset_workspace_state_manager()


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in _ALL_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(tool_logging, "_tool_store", tool_logging._tool_store)
    _reset_singletons()
    yield
    _reset_singletons()


def _dirs(tmp_path: Path) -> tuple[Path, Path]:
    start = tmp_path / "start"
    target = tmp_path / "target"
    start.mkdir()
    target.mkdir()
    return start, target


def test_get_workspace_state_binds_and_rebinds_managers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    start, target = _dirs(tmp_path)
    monkeypatch.chdir(start)
    singleton = get_project_manager()
    injected = type(singleton)(str(start))
    tools = register_workspace_state_tools(MCPServer("bind-test"), project_manager=injected)

    result = tools["get_workspace_state"](workspace_dir=str(target))

    resolved = target.resolve()
    assert "status" not in result
    assert result["workspace"] == {"root": str(resolved), "source": "bound", "binding_hint": ""}
    for manager in (singleton, injected):
        assert manager.base_path == resolved
        assert manager.projects_dir == resolved / "projects"
        assert manager.state_file == resolved / manager.STATE_FILE
    assert (resolved / "projects").is_dir()
    assert get_workspace_state_manager().base_path == resolved
    assert tool_logging._tool_store is not None
    assert tool_logging._tool_store._dir == resolved / ".audit"


def test_get_workspace_state_reports_bind_errors_without_rebinding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    start, _ = _dirs(tmp_path)
    monkeypatch.chdir(start)
    manager = get_project_manager()
    tools = register_workspace_state_tools(MCPServer("bind-error"), project_manager=manager)

    result = tools["get_workspace_state"](workspace_dir="relative/dir")

    assert result["status"] == "error"
    assert "absolute" in result["message"]
    assert result["workspace"]["source"] == wr.SOURCE_CWD
    assert manager.base_path == start.resolve()


def test_get_workspace_state_without_dir_reports_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MEDPAPER_BASE_DIR", str(tmp_path))
    tools = register_workspace_state_tools(MCPServer("bind-get"))

    result = tools["get_workspace_state"]()

    assert result["workspace"] == {
        "root": str(tmp_path.resolve()),
        "source": "env:MEDPAPER_BASE_DIR",
        "binding_hint": "",
    }


def test_binding_hint_for_plugin_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    monkeypatch.chdir(plugin)
    monkeypatch.setenv("PLUGIN_ROOT", str(plugin))
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path / "data"))

    info = workspace_binding_info()

    assert info["source"] == wr.SOURCE_PLUGIN_DATA
    assert 'action="bind"' in info["binding_hint"]


def test_binding_hint_only_for_cwd_without_projects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    assert 'action="bind"' in workspace_binding_info()["binding_hint"]

    (tmp_path / "projects").mkdir()
    assert workspace_binding_info()["binding_hint"] == ""
