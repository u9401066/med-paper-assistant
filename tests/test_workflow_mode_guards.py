from __future__ import annotations

import asyncio
import inspect
from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.interfaces.mcp.tools.analysis import figures as figures_tools
from med_paper_assistant.interfaces.mcp.tools.analysis import stats as stats_tools
from med_paper_assistant.interfaces.mcp.tools.analysis import table_one as table_one_tools
from med_paper_assistant.interfaces.mcp.tools.export import pandoc_export
from med_paper_assistant.interfaces.mcp.tools.export import word as word_export
from med_paper_assistant.interfaces.mcp.tools.review import audit_hooks as audit_hook_tools
from med_paper_assistant.interfaces.mcp.tools.review import formatting as formatting_tools
from med_paper_assistant.interfaces.mcp.tools.review import pipeline_gate as pipeline_tools


def _capture_tool_functions(register_callback):
    mock_mcp = MagicMock()
    captured = {}

    def fake_tool(*args, **kwargs):
        def decorator(fn):
            if inspect.iscoroutinefunction(fn):

                def sync_wrapper(*wrapper_args, **wrapper_kwargs):
                    return asyncio.run(fn(*wrapper_args, **wrapper_kwargs))

                sync_wrapper.__name__ = fn.__name__
                captured[fn.__name__] = sync_wrapper
            else:
                captured[fn.__name__] = fn
            return fn

        return decorator

    mock_mcp.tool = fake_tool
    register_callback(mock_mcp)
    return captured


def test_table_one_tools_guard_library_workflow(monkeypatch):
    monkeypatch.setattr(
        table_one_tools,
        "resolve_project_context",
        lambda project=None, required_mode="manuscript", project_manager=None: (None, "workflow-guard"),
    )
    monkeypatch.setattr(
        table_one_tools,
        "ensure_project_context",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not reach project context")),
    )

    captured = _capture_tool_functions(
        lambda mcp: table_one_tools.register_table_one_tools(mcp, analyzer=MagicMock())
    )

    result = captured["generate_table_one"](
        filename="demo.csv",
        group_col="arm",
        continuous_cols="age",
        categorical_cols="sex",
        project="library",
    )

    assert result == "workflow-guard"


def test_stats_tools_guard_library_workflow(monkeypatch):
    monkeypatch.setattr(
        stats_tools,
        "resolve_project_context",
        lambda project=None, required_mode="manuscript", project_manager=None: (None, "workflow-guard"),
    )
    monkeypatch.setattr(
        stats_tools,
        "ensure_project_context",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not reach project context")),
    )

    captured = _capture_tool_functions(
        lambda mcp: stats_tools.register_stats_tools(mcp, analyzer=MagicMock())
    )

    result = captured["analyze_dataset"](filename="demo.csv", project="library")

    assert result == "workflow-guard"


def test_figure_tools_guard_library_workflow(monkeypatch):
    monkeypatch.setattr(
        figures_tools,
        "resolve_project_context",
        lambda project=None, required_mode="manuscript", project_manager=None: (None, "workflow-guard"),
    )
    monkeypatch.setattr(
        figures_tools,
        "ensure_project_context",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not reach project context")),
    )

    captured = _capture_tool_functions(
        lambda mcp: figures_tools.register_figure_tools(mcp, drafter=MagicMock())
    )

    result = captured["insert_figure"](
        filename="plot.png",
        caption="Example",
        project="library",
    )

    assert result == "workflow-guard"


def test_pandoc_export_tools_guard_library_workflow(monkeypatch):
    monkeypatch.setattr(
        pandoc_export,
        "resolve_project_context",
        lambda project=None, required_mode="manuscript", project_manager=None: (None, "workflow-guard"),
    )
    monkeypatch.setattr(
        pandoc_export,
        "ensure_project_context",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not reach project context")),
    )

    funcs = pandoc_export.register_pandoc_export_tools(FastMCP("pandoc-guard-test"))
    result = funcs["export_docx"](draft_filename="discussion.md", project="library")

    assert result == "workflow-guard"


def test_word_export_tools_guard_library_workflow(monkeypatch):
    monkeypatch.setattr(
        word_export,
        "resolve_project_context",
        lambda project=None, required_mode="manuscript", project_manager=None: (None, "workflow-guard"),
    )

    funcs = word_export.register_word_export_tools(
        FastMCP("word-guard-test"),
        formatter=MagicMock(),
        template_reader=MagicMock(),
        word_writer=MagicMock(),
    )
    result = funcs["start_document_session"](session_id="word-1", project="library")

    assert result == "workflow-guard"


def test_review_formatting_tools_guard_library_workflow(monkeypatch):
    monkeypatch.setattr(
        formatting_tools,
        "resolve_project_context",
        lambda project=None, required_mode="manuscript", project_manager=None: (None, "workflow-guard"),
    )

    captured = _capture_tool_functions(
        lambda mcp: formatting_tools.register_formatting_tools(
            mcp,
            drafter=MagicMock(),
            ref_manager=MagicMock(),
        )
    )

    result = captured["check_formatting"](
        draft_filename="discussion.md",
        project="library",
    )

    assert result == "workflow-guard"


def test_review_audit_tools_guard_library_workflow(monkeypatch):
    monkeypatch.setattr(
        audit_hook_tools,
        "resolve_project_context",
        lambda project=None, required_mode="manuscript", project_manager=None: (
            None,
            "❌ This tool is only available for Manuscript Path projects.\n\nCurrent workflow: Library Wiki Path.\nSwitch project or update the current project workflow before retrying.\n\nSuggested fix:\n- `project_action(action=\"update\", workflow_mode=\"manuscript\")`\n- or switch to a project that already uses the required workflow mode.",
        ),
    )

    captured = _capture_tool_functions(
        lambda mcp: audit_hook_tools.register_audit_hook_tools(mcp)
    )

    assert (
        captured["record_hook_event"](
            hook_id="A1",
            event_type="trigger",
            project="library",
        )
        .startswith("❌ This tool is only available for Manuscript Path projects.")
    )
    assert (
        captured["run_quality_audit"](
            scores='{"citation_quality": 8, "text_quality": 8, "concept_consistency": 8, "format_compliance": 8}',
            project="library",
        )
        .startswith("❌ This tool is only available for Manuscript Path projects.")
    )
    assert captured["run_meta_learning"](project="library").startswith(
        "❌ This tool is only available for Manuscript Path projects."
    )
    assert captured["validate_data_artifacts"](project="library").startswith(
        "❌ This tool is only available for Manuscript Path projects."
    )
    assert captured["run_writing_hooks"](project="library").startswith(
        "❌ This tool is only available for Manuscript Path projects."
    )
    assert captured["run_review_hooks"](project="library").startswith(
        "❌ This tool is only available for Manuscript Path projects."
    )
    assert (
        captured["check_domain_constraints"](
            content="Results text",
            project="library",
        )
        .startswith("❌ This tool is only available for Manuscript Path projects.")
    )
    assert (
        captured["evolve_constraint"](
            constraint_id="L001",
            rule="no_passive_results",
            category="boundary",
            description="Do not use passive voice in results.",
            project="library",
        )
        .startswith("❌ This tool is only available for Manuscript Path projects.")
    )


def test_review_pipeline_tools_guard_library_workflow(monkeypatch):
    monkeypatch.setattr(
        pipeline_tools,
        "resolve_project_context",
        lambda project=None, required_mode="manuscript", project_manager=None: (None, "workflow-guard"),
    )

    captured = _capture_tool_functions(
        lambda mcp: pipeline_tools.register_pipeline_tools(mcp, project_manager=MagicMock())
    )

    assert captured["validate_phase_gate"](phase=7, project="library") == "workflow-guard"
    assert captured["pipeline_heartbeat"](project="library") == "workflow-guard"
    assert captured["start_review_round"](project="library") == "workflow-guard"
    assert (
        captured["submit_review_round"](
            scores='{"citation_quality": 8}',
            project="library",
        )
        == "workflow-guard"
    )
    assert captured["validate_project_structure"](project="library") == "workflow-guard"
    assert (
        captured["request_section_rewrite"](
            sections="Methods",
            reason="Needs rewrite",
            project="library",
        )
        == "workflow-guard"
    )
    assert captured["pause_pipeline"](project="library") == "workflow-guard"
    assert captured["resume_pipeline"](project="library") == "workflow-guard"
    assert (
        captured["approve_section"](
            section="Methods",
            project="library",
        )
        == "workflow-guard"
    )
    assert (
        captured["approve_concept_review"](
            action="approve",
            rationale="Need human override",
            project="library",
        )
        == "workflow-guard"
    )
    assert (
        captured["reset_review_loop"](
            project="library",
            confirm=True,
        )
        == "workflow-guard"
    )