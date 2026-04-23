from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from med_paper_assistant.interfaces.mcp.tools.project import diagrams as diagram_tools


def _capture_diagram_tools(monkeypatch):
    mock_mcp = MagicMock()
    captured = {}

    def fake_tool(*args, **kwargs):
        def decorator(fn):
            captured[fn.__name__] = fn
            return fn

        return decorator

    mock_mcp.tool = fake_tool
    monkeypatch.setattr(
        diagram_tools,
        "ensure_project_context",
        lambda project=None: (False, "no project", None),
    )
    diagram_tools.register_diagram_tools(mock_mcp, project_manager=MagicMock())
    return captured


def test_save_diagram_standalone_allows_workspace_relative_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    funcs = _capture_diagram_tools(monkeypatch)

    result = funcs["save_diagram"](
        filename="flow",
        content="<mxfile />",
        output_dir="exports/diagrams",
    )

    assert "Diagram Saved" in result
    assert (tmp_path / "exports" / "diagrams" / "flow.drawio").exists()


@pytest.mark.parametrize("output_dir", ["../escape", "/tmp/escape", r"C:\tmp\escape"])
def test_save_diagram_standalone_rejects_unsafe_output_dir(
    tmp_path,
    monkeypatch,
    output_dir,
):
    monkeypatch.chdir(tmp_path)
    funcs = _capture_diagram_tools(monkeypatch)

    result = funcs["save_diagram"](
        filename="flow",
        content="<mxfile />",
        output_dir=output_dir,
    )

    assert result.startswith("❌ Invalid diagram path:")
