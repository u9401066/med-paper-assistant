from __future__ import annotations

from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.interfaces.mcp.tools.analysis import register_analysis_tools
from med_paper_assistant.interfaces.mcp.tools.analysis.facade import register_analysis_facade_tools


def _capture_tool_functions(register_callback):
    mock_mcp = MagicMock()
    captured = {}

    def fake_tool(*args, **kwargs):
        def decorator(fn):
            captured[fn.__name__] = fn
            return fn

        return decorator

    mock_mcp.tool = fake_tool
    result = register_callback(mock_mcp)
    return captured, result


def test_register_analysis_tools_uses_env_surface_for_compact(monkeypatch):
    captured, handlers = _capture_tool_functions(
        lambda mcp: register_analysis_tools(
            mcp,
            analyzer=MagicMock(),
            drafter=MagicMock(),
            tool_surface="compact",
        )
    )

    assert set(captured) == {"analysis_action"}
    assert {
        "analyze_dataset",
        "run_statistical_test",
        "create_plot",
        "generate_table_one",
        "detect_variable_types",
        "list_data_files",
        "review_asset_for_insertion",
        "insert_figure",
        "insert_table",
        "list_assets",
        "analysis_action",
    } <= set(handlers)


def test_register_analysis_tools_exposes_granular_tools_on_full_surface():
    captured, handlers = _capture_tool_functions(
        lambda mcp: register_analysis_tools(
            mcp,
            analyzer=MagicMock(),
            drafter=MagicMock(),
            tool_surface="full",
        )
    )

    expected_tools = {
        "analyze_dataset",
        "run_statistical_test",
        "create_plot",
        "generate_table_one",
        "detect_variable_types",
        "list_data_files",
        "review_asset_for_insertion",
        "insert_figure",
        "insert_table",
        "list_assets",
    }

    assert expected_tools <= set(captured)
    assert expected_tools <= set(handlers)
    assert "analysis_action" not in handlers


def test_analysis_action_routes_asset_tools_on_compact_surface():
    figure_calls: dict[str, object] = {}

    def insert_figure(**kwargs):
        figure_calls.update(kwargs)
        return "figure-ok"

    handlers = register_analysis_facade_tools(
        FastMCP("analysis-facade-test"),
        stats_tools={},
        table_one_tools={},
        figure_tools={"insert_figure": insert_figure},
    )
    result = __import__("asyncio").run(
        handlers["analysis_action"](
            action="insert_figure",
            filename="flow.png",
            caption="Flow diagram",
            draft_filename="results.md",
            after_section="Results",
            project="demo",
        )
    )

    assert result == "figure-ok"
    assert figure_calls == {
        "filename": "flow.png",
        "caption": "Flow diagram",
        "draft_filename": "results.md",
        "after_section": "Results",
        "project": "demo",
    }
