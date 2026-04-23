from __future__ import annotations

import pytest
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.interfaces.mcp.tools.export.facade import register_export_facade_tools
from med_paper_assistant.interfaces.mcp.tools.project.facade import register_project_facade_tools
from med_paper_assistant.interfaces.mcp.tools.review.facade import register_review_facade_tools
from med_paper_assistant.interfaces.mcp.tools.validation.facade import (
    register_validation_facade_tools,
)


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
async def test_run_quality_checks_routes_domain_constraints_with_project() -> None:
    captured: dict[str, object] = {}

    def check_domain_constraints(**kwargs):
        captured.update(kwargs)
        return "constraints-ok"

    funcs = register_review_facade_tools(
        FastMCP("review-constraints-test"),
        audit_tools={"check_domain_constraints": check_domain_constraints},
        pipeline_tools={},
    )

    result = await funcs["run_quality_checks"](
        action="constraints",
        content="Results content",
        section="results",
        paper_type="original-research",
        project="demo",
    )

    assert result == "constraints-ok"
    assert captured == {
        "content": "Results content",
        "section": "results",
        "paper_type": "original-research",
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
        "graph_views_json": "",
    }


@pytest.mark.asyncio
async def test_library_action_routes_new_library_workflow_handlers() -> None:
    triage_captured: dict[str, object] = {}
    metadata_captured: dict[str, object] = {}
    materialize_captured: dict[str, object] = {}

    def triage_library_note(**kwargs):
        triage_captured.update(kwargs)
        return "triaged"

    def update_library_note_metadata(**kwargs):
        metadata_captured.update(kwargs)
        return "metadata-ok"

    def materialize_concept_page(**kwargs):
        materialize_captured.update(kwargs)
        return "materialized"

    funcs = register_project_facade_tools(
        FastMCP("library-facade-test"),
        crud_tools={},
        settings_tools={},
        exploration_tools={},
        workspace_state_tools={},
        library_tools={
            "triage_library_note": triage_library_note,
            "update_library_note_metadata": update_library_note_metadata,
            "materialize_concept_page": materialize_concept_page,
        },
    )

    triage_result = await funcs["library_action"](
        action="triage",
        filename="signal-note",
        to_section="concepts",
        tags_csv="sedation",
        related_notes_csv="projects:review-hub",
        status="curated",
        project="demo",
    )
    assert triage_result == "triaged"
    assert triage_captured == {
        "note_ref": "signal-note",
        "target_section": "concepts",
        "status": "curated",
        "tags_csv": "sedation",
        "related_notes_csv": "projects:review-hub",
        "project": "demo",
    }

    metadata_result = await funcs["library_action"](
        action="frontmatter",
        filename="signal-note",
        title="Signal Note",
        add_tags_csv="alpha2",
        remove_tags_csv="old-tag",
        related_notes_csv="concepts:signal-map",
        note_type="library-evidence",
        project="demo",
    )
    assert metadata_result == "metadata-ok"
    assert metadata_captured == {
        "note_ref": "signal-note",
        "title": "Signal Note",
        "status": "",
        "tags_csv": "",
        "add_tags_csv": "alpha2",
        "remove_tags_csv": "old-tag",
        "related_notes_csv": "concepts:signal-map",
        "note_type": "library-evidence",
        "project": "demo",
    }

    materialize_result = await funcs["library_action"](
        action="materialize",
        source_note="signal-note",
        title="Signal Map",
        content="Derived summary",
        tags_csv="sedation,concept",
        status="What stabilizes the thread?",
        project="demo",
    )
    assert materialize_result == "materialized"
    assert materialize_captured == {
        "filename": "",
        "title": "Signal Map",
        "summary": "Derived summary",
        "source_notes_csv": "signal-note",
        "tags_csv": "sedation,concept",
        "open_questions": "What stabilizes the thread?",
        "project": "demo",
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


@pytest.mark.asyncio
async def test_validation_action_routes_literature_compare() -> None:
    captured: dict[str, object] = {}

    def compare_with_literature(**kwargs):
        captured.update(kwargs)
        return "literature-ok"

    funcs = register_validation_facade_tools(
        FastMCP("validation-facade-test"),
        concept_tools={},
        idea_tools={"compare_with_literature": compare_with_literature},
    )

    result = await funcs["validation_action"](
        action="compare",
        idea="Does remimazolam reduce hypotension risk?",
        project="demo",
    )

    assert result == "literature-ok"
    assert captured == {
        "idea": "Does remimazolam reduce hypotension risk?",
        "project": "demo",
    }


@pytest.mark.asyncio
async def test_validation_action_lists_supported_actions() -> None:
    funcs = register_validation_facade_tools(
        FastMCP("validation-list-test"),
        concept_tools={},
        idea_tools={},
    )

    result = await funcs["validation_action"](action="list")

    assert "concept" in result
    assert "wikilinks" in result
    assert "literature" in result
