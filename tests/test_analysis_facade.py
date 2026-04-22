from __future__ import annotations

from unittest.mock import MagicMock

from med_paper_assistant.interfaces.mcp.tools.analysis import register_analysis_tools


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

    assert captured == {}
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