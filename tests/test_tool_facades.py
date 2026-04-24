from __future__ import annotations

import json

import pytest
import yaml
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
async def test_run_quality_checks_lists_machine_readable_schema() -> None:
    funcs = register_review_facade_tools(
        FastMCP("review-list-test"),
        audit_tools={},
        pipeline_tools={},
    )

    result = await funcs["run_quality_checks"](action="list")
    payload = json.loads(result)

    assert payload["schema"] == "mdpaper.facade_actions.v1"
    assert payload["tool"] == "run_quality_checks"
    assert "meta_learning" in payload["actions"]
    assert "writing_hooks" in payload["actions"]
    assert "pipeline_retrospective" in payload["actions"]


@pytest.mark.asyncio
async def test_run_quality_checks_routes_pipeline_retrospective_writer() -> None:
    captured: dict[str, object] = {}

    async def write_pipeline_retrospective(**kwargs):
        captured.update(kwargs)
        return "retrospective-ok"

    funcs = register_review_facade_tools(
        FastMCP("review-retrospective-test"),
        audit_tools={"write_pipeline_retrospective": write_pipeline_retrospective},
        pipeline_tools={},
    )

    result = await funcs["run_quality_checks"](
        action="pipeline_retrospective",
        summary="Pipeline summary",
        d7_retrospective="Review lessons",
        d8_retrospective="EQUATOR lessons",
        project="demo",
    )

    assert result == "retrospective-ok"
    assert captured == {
        "summary": "Pipeline summary",
        "d7_retrospective": "Review lessons",
        "d8_retrospective": "EQUATOR lessons",
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
async def test_pipeline_action_help_lists_supported_actions() -> None:
    funcs = register_review_facade_tools(
        FastMCP("pipeline-help-test"),
        audit_tools={},
        pipeline_tools={},
    )

    result = await funcs["pipeline_action"](action="help")

    payload = json.loads(result)
    assert payload["schema"] == "mdpaper.facade_actions.v1"
    assert payload["tool"] == "pipeline_action"
    assert "validate_phase" in payload["actions"]
    assert "start_review" in payload["actions"]
    assert "submit_review" in payload["actions"]
    assert "doctor" in payload["actions"]
    assert "score_schema" in payload["actions"]["submit_review"]
    assert "analysis_action" in " ".join(payload["notes"])


@pytest.mark.asyncio
async def test_pipeline_action_routes_doctor() -> None:
    captured: dict[str, object] = {}

    def pipeline_doctor(**kwargs):
        captured.update(kwargs)
        return '{"schema":"mdpaper.pipeline_doctor.v1"}'

    funcs = register_review_facade_tools(
        FastMCP("pipeline-doctor-route-test"),
        audit_tools={},
        pipeline_tools={"pipeline_doctor": pipeline_doctor},
    )

    result = await funcs["pipeline_action"](action="doctor", project="demo")

    assert "mdpaper.pipeline_doctor.v1" in result
    assert captured == {"project": "demo"}


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
async def test_project_action_writes_journal_profile(tmp_path, monkeypatch) -> None:
    import med_paper_assistant.interfaces.mcp.tools.project.facade as project_facade

    project_dir = tmp_path / "demo-project"
    project_dir.mkdir()

    def fake_resolve_project_context(project=None, **kwargs):
        return (
            {
                "slug": "demo",
                "name": "Demo",
                "project_path": str(project_dir),
                "target_journal": "BJA",
                "paper_type": "original-research",
            },
            None,
        )

    monkeypatch.setattr(project_facade, "resolve_project_context", fake_resolve_project_context)
    funcs = register_project_facade_tools(
        FastMCP("project-journal-profile-test"),
        crud_tools={},
        settings_tools={},
        exploration_tools={},
        workspace_state_tools={},
    )

    result = await funcs["project_action"](
        action="journal_profile",
        target_journal="BJA",
        paper_type="original-research",
        citation_style="vancouver",
        language_preference="en-GB",
    )

    profile_path = project_dir / "journal-profile.yaml"
    assert "status: ok" in result
    assert profile_path.is_file()
    data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    assert data["journal"]["name"] == "BJA"
    assert data["journal"]["locale"] == "en-GB"
    assert data["paper"]["type"] == "original-research"
    assert data["pipeline"]["writing"]["prefer_language"] == "british"


@pytest.mark.asyncio
async def test_project_action_scans_source_materials(tmp_path, monkeypatch) -> None:
    import med_paper_assistant.interfaces.mcp.tools.project.facade as project_facade

    workspace = tmp_path / "workspace"
    project_dir = workspace / "projects" / "demo-project"
    project_dir.mkdir(parents=True)
    (project_dir / ".audit").mkdir()
    source_docx = workspace / "20240115 Table formal data.docx"
    source_docx.write_text("fake docx bytes", encoding="utf-8")
    generated_docx = project_dir / "drafts" / "generated.docx"
    generated_docx.parent.mkdir()
    generated_docx.write_text("generated", encoding="utf-8")

    def fake_resolve_project_context(project=None, **kwargs):
        return (
            {
                "slug": "demo",
                "name": "Demo",
                "project_path": str(project_dir),
                "target_journal": "BJA",
                "paper_type": "original-research",
            },
            None,
        )

    monkeypatch.setattr(project_facade, "resolve_project_context", fake_resolve_project_context)
    funcs = register_project_facade_tools(
        FastMCP("project-source-materials-test"),
        crud_tools={},
        settings_tools={},
        exploration_tools={},
        workspace_state_tools={},
    )

    result = await funcs["project_action"](action="source_materials")

    manifest_path = project_dir / ".audit" / "source-materials.yaml"
    assert "status: ok" in result
    assert "pending_asset_aware: 1" in result
    assert manifest_path.is_file()
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert data["schema"] == "mdpaper.source_materials.v1"
    assert data["summary"]["total_candidates"] == 1
    assert data["materials"][0]["filename"] == source_docx.name
    assert data["materials"][0]["ingestion"]["status"] == "pending_asset_aware"


@pytest.mark.asyncio
async def test_project_action_records_asset_ingestion_receipt(tmp_path, monkeypatch) -> None:
    import med_paper_assistant.interfaces.mcp.tools.project.facade as project_facade

    project_dir = tmp_path / "projects" / "demo-project"
    project_dir.mkdir(parents=True)
    (project_dir / ".audit").mkdir()
    (project_dir / ".audit" / "source-materials.yaml").write_text(
        yaml.dump(
            {
                "schema": "mdpaper.source_materials.v1",
                "materials": [
                    {
                        "id": "source-001",
                        "filename": "table.docx",
                        "relative_path": "table.docx",
                        "path": str(tmp_path / "table.docx"),
                        "evidence_priority": "primary_user_material",
                        "ingestion": {
                            "status": "pending_asset_aware",
                            "required": True,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def fake_resolve_project_context(project=None, **kwargs):
        return (
            {
                "slug": "demo",
                "name": "Demo",
                "project_path": str(project_dir),
                "target_journal": "BJA",
                "paper_type": "original-research",
            },
            None,
        )

    monkeypatch.setattr(project_facade, "resolve_project_context", fake_resolve_project_context)
    funcs = register_project_facade_tools(
        FastMCP("project-record-asset-ingestion-test"),
        crud_tools={},
        settings_tools={},
        exploration_tools={},
        workspace_state_tools={},
    )

    result = await funcs["project_action"](
        action="record_asset_ingestion",
        source_material_id="source-001",
        asset_aware_doc_id="doc_123",
        sections_json='["Methods", "Results"]',
        artifact_paths_json='["artifacts/asset-aware/sections.md"]',
    )

    data = yaml.safe_load(
        (project_dir / ".audit" / "source-materials.yaml").read_text(encoding="utf-8")
    )
    material = data["materials"][0]
    assert "status: ok" in result
    assert material["ingestion"]["status"] == "ingested_asset_aware"
    assert material["ingestion"]["asset_aware_doc_id"] == "doc_123"
    assert data["summary"]["pending_asset_aware"] == 0


@pytest.mark.asyncio
async def test_project_action_help_lists_machine_readable_schema() -> None:
    funcs = register_project_facade_tools(
        FastMCP("project-help-schema-test"),
        crud_tools={},
        settings_tools={},
        exploration_tools={},
        workspace_state_tools={},
    )

    result = await funcs["project_action"](action="help")
    payload = json.loads(result)

    assert payload["schema"] == "mdpaper.facade_actions.v1"
    assert payload["tool"] == "project_action"
    assert "journal_profile" in payload["actions"]
    assert "source_materials" in payload["actions"]
    assert "record_asset_ingestion" in payload["actions"]


@pytest.mark.asyncio
async def test_workspace_state_action_lists_structured_schema() -> None:
    funcs = register_project_facade_tools(
        FastMCP("workspace-state-list-test"),
        crud_tools={},
        settings_tools={},
        exploration_tools={},
        workspace_state_tools={},
    )

    result = await funcs["workspace_state_action"](action="list")

    assert result["status"] == "ok"
    assert result["schema"] == "mdpaper.facade_actions.v1"
    assert "get" in result["actions"]


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
async def test_inspect_export_routes_docx_smoke_alias() -> None:
    captured: dict[str, object] = {}

    def inspect_docx_xml(**kwargs):
        captured.update(kwargs)
        return "docx-smoke-ok"

    funcs = register_export_facade_tools(
        FastMCP("inspect-docx-smoke-test"),
        word_tools={},
        pandoc_tools={"inspect_docx_xml": inspect_docx_xml},
    )

    result = await funcs["inspect_export"](
        action="docx_smoke",
        output_filename="paper.docx",
        project="demo",
    )

    assert result == "docx-smoke-ok"
    assert captured == {
        "output_filename": "paper.docx",
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

    payload = json.loads(result)
    assert payload["schema"] == "mdpaper.facade_actions.v1"
    assert payload["tool"] == "validation_action"
    assert "concept" in payload["actions"]
    assert "wikilinks" in payload["actions"]
    assert "literature" in payload["actions"]


@pytest.mark.asyncio
async def test_export_facades_list_machine_readable_schema() -> None:
    funcs = register_export_facade_tools(
        FastMCP("export-list-test"),
        word_tools={},
        pandoc_tools={},
    )

    export_payload = json.loads(await funcs["export_document"](action="list"))
    inspect_payload = json.loads(await funcs["inspect_export"](action="list"))

    assert export_payload["schema"] == "mdpaper.facade_actions.v1"
    assert export_payload["tool"] == "export_document"
    assert "docx" in export_payload["actions"]
    assert inspect_payload["schema"] == "mdpaper.facade_actions.v1"
    assert inspect_payload["tool"] == "inspect_export"
    assert "list_templates" in inspect_payload["actions"]
    assert "inspect_docx_xml" in inspect_payload["actions"]
