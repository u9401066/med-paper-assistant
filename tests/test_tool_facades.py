from __future__ import annotations

from mcp.server.fastmcp import FastMCP
import pytest

from med_paper_assistant.interfaces.mcp.tools.export.facade import register_export_facade_tools
from med_paper_assistant.interfaces.mcp.tools.project.facade import register_project_facade_tools
from med_paper_assistant.interfaces.mcp.tools.review.facade import register_review_facade_tools


@pytest.mark.asyncio
async def test_run_quality_checks_routes_to_review_hooks() -> None:
    captured: dict[str, object] = {}

    async def run_review_hooks(**kwargs):
        captured.update(kwargs)
        return "review-hooks-ok"

    funcs = register_review_facade_tools(
        FastMCP("review-test"),
        audit_tools={"run_review_hooks": run_review_hooks},
        pipeline_tools={},
    )

    result = await funcs["run_quality_checks"](
        action="review",
        round_num=2,
        hooks="R1,R2",
        issues_fixed=3,
        project="demo",
    )

    assert result == "review-hooks-ok"
    assert captured == {
        "round_num": 2,
        "hooks": "R1,R2",
        "issues_fixed": 3,
        "project": "demo",
    }


@pytest.mark.asyncio
async def test_pipeline_action_routes_submit_review_round() -> None:
    captured: dict[str, object] = {}

    async def submit_review_round(**kwargs):
        captured.update(kwargs)
        return "submitted"

    funcs = register_review_facade_tools(
        FastMCP("pipeline-test"),
        audit_tools={},
        pipeline_tools={"submit_review_round": submit_review_round},
    )

    result = await funcs["pipeline_action"](
        action="submit",
        scores='{"citation_quality": 8}',
        issues_found=4,
        issues_fixed=2,
        project="demo",
    )

    assert result == "submitted"
    assert captured == {
        "scores": '{"citation_quality": 8}',
        "issues_found": 4,
        "issues_fixed": 2,
        "project": "demo",
    }


@pytest.mark.asyncio
async def test_project_action_routes_update_settings() -> None:
    captured: dict[str, object] = {}

    def update_project_settings(**kwargs):
        captured.update(kwargs)
        return "updated"

    funcs = register_project_facade_tools(
        FastMCP("project-test"),
        crud_tools={},
        settings_tools={"update_project_settings": update_project_settings},
        exploration_tools={},
        workspace_state_tools={},
    )

    result = await funcs["project_action"](
        action="settings",
        paper_type="review-article",
        target_journal="BJA",
        citation_style="vancouver",
    )

    assert result == "updated"
    assert captured == {
        "paper_type": "review-article",
        "target_journal": "BJA",
        "interaction_style": "",
        "language_preference": "",
        "writing_style": "",
        "memo": "",
        "status": "",
        "citation_style": "vancouver",
    }


@pytest.mark.asyncio
async def test_workspace_state_action_preserves_structured_get_result() -> None:
    def get_workspace_state():
        return {
            "recovery_summary": "resume here",
            "workspace_state": {"current_project": "demo"},
            "startup_guidance": "none",
        }

    funcs = register_project_facade_tools(
        FastMCP("workspace-test"),
        crud_tools={},
        settings_tools={},
        exploration_tools={},
        workspace_state_tools={"get_workspace_state": get_workspace_state},
    )

    result = await funcs["workspace_state_action"](action="recover")

    assert result == {
        "status": "ok",
        "action": "get",
        "recovery_summary": "resume here",
        "workspace_state": {"current_project": "demo"},
        "startup_guidance": "none",
    }


@pytest.mark.asyncio
async def test_export_document_routes_docx() -> None:
    captured: dict[str, object] = {}

    def export_docx(**kwargs):
        captured.update(kwargs)
        return "docx-ok"

    funcs = register_export_facade_tools(
        FastMCP("export-test"),
        word_tools={},
        pandoc_tools={"export_docx": export_docx},
    )

    result = await funcs["export_document"](
        action="word",
        draft_filename="manuscript.md",
        csl_style="nature",
        project="demo",
    )

    assert result == "docx-ok"
    assert captured == {
        "draft_filename": "manuscript.md",
        "csl_style": "nature",
        "project": "demo",
    }


@pytest.mark.asyncio
async def test_inspect_export_routes_preview_alias() -> None:
    captured: dict[str, object] = {}

    def preview_citations(**kwargs):
        captured.update(kwargs)
        return "preview-ok"

    funcs = register_export_facade_tools(
        FastMCP("inspect-test"),
        word_tools={},
        pandoc_tools={"preview_citations": preview_citations},
    )

    result = await funcs["inspect_export"](
        action="preview",
        draft_filename="discussion.md",
        project="demo",
    )

    assert result == "preview-ok"
    assert captured == {
        "draft_filename": "discussion.md",
        "project": "demo",
    }