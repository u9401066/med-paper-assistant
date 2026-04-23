from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest

from med_paper_assistant.interfaces.mcp.tools.reference import manager as reference_tools


def _capture_reference_tools(ref_manager):
    mock_mcp = MagicMock()
    captured = {}

    def fake_tool(*args, **kwargs):
        def decorator(fn):
            captured[fn.__name__] = fn
            return fn

        return decorator

    mock_mcp.tool = fake_tool
    reference_tools.register_reference_manager_tools(
        mock_mcp,
        ref_manager=ref_manager,
        drafter=MagicMock(),
        project_manager=None,
    )
    assert inspect.isfunction(captured["import_local_papers"])
    return captured


def test_import_local_papers_allows_workspace_contained_absolute_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MEDPAPER_BASE_DIR", str(tmp_path))
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"paper")
    ref_manager = MagicMock()
    ref_manager._project_manager = None
    ref_manager.import_local_file.return_value = "imported"
    funcs = _capture_reference_tools(ref_manager)

    result = funcs["import_local_papers"](paths=str(source))

    assert "paper.pdf: imported" in result
    ref_manager.import_local_file.assert_called_once_with(str(source.resolve()), metadata={})


@pytest.mark.parametrize("path", ["../paper.pdf", r"C:\tmp\paper.pdf", r"\\server\share\paper.pdf"])
def test_import_local_papers_rejects_unsafe_paths(tmp_path, monkeypatch, path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MEDPAPER_BASE_DIR", str(tmp_path))
    ref_manager = MagicMock()
    ref_manager._project_manager = None
    funcs = _capture_reference_tools(ref_manager)

    result = funcs["import_local_papers"](paths=path)

    assert "Invalid local import path" in result
    ref_manager.import_local_file.assert_not_called()
