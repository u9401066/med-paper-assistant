from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import PipelineGateValidator
from med_paper_assistant.infrastructure.persistence.writing_hooks import WritingHooksEngine
from med_paper_assistant.interfaces.mcp.tools.project.facade import register_project_facade_tools


@pytest.mark.asyncio
async def test_golden_mini_project_source_ingestion_claim_and_anchor_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Golden mini-project for the highest-risk Auto-Paper path.

    Covers Phase 0 source-material intake, asset-aware receipt backfill,
    Phase 2.1 pending-source enforcement, C14 claim evidence, and F4 data-anchor
    provenance without depending on real external MCP processes.
    """
    import med_paper_assistant.interfaces.mcp.tools.project.facade as project_facade

    workspace = tmp_path / "workspace"
    project_dir = workspace / "projects" / "golden"
    for dirname in ["drafts", "references", "data", "results", ".audit", ".memory", "exports"]:
        (project_dir / dirname).mkdir(parents=True, exist_ok=True)
    (project_dir / "project.json").write_text('{"slug": "golden"}', encoding="utf-8")
    for i in range(20):
        ref_dir = project_dir / "references" / f"ref-{i}"
        ref_dir.mkdir(parents=True, exist_ok=True)
        (ref_dir / "metadata.json").write_text(
            json.dumps({"pmid": f"1000{i}", "analysis_completed": True}),
            encoding="utf-8",
        )
    source_docx = workspace / "20240112 primary screening table.docx"
    source_docx.write_text("mock docx", encoding="utf-8")

    def fake_resolve_project_context(project=None, **kwargs):
        return (
            {
                "slug": "golden",
                "name": "Golden",
                "project_path": str(project_dir),
                "target_journal": "BJA",
                "paper_type": "original-research",
            },
            None,
        )

    monkeypatch.setattr(project_facade, "resolve_project_context", fake_resolve_project_context)
    funcs = register_project_facade_tools(
        FastMCP("golden-mini-project"),
        crud_tools={},
        settings_tools={},
        exploration_tools={},
        workspace_state_tools={},
    )

    scan_result = await funcs["project_action"](action="source_materials")
    assert "pending_asset_aware: 1" in scan_result

    (project_dir / "journal-profile.yaml").write_text(
        yaml.dump({"paper": {"type": "original-research"}}),
        encoding="utf-8",
    )
    validator = PipelineGateValidator(project_dir)
    assert validator.validate_phase(0).passed

    (project_dir / "references" / "fulltext-ingestion-status.md").write_text("none", encoding="utf-8")
    pending_phase = validator.validate_phase(21)
    assert not pending_phase.passed
    assert "source-materials:asset-aware" in pending_phase.missing

    receipt_result = await funcs["project_action"](
        action="record_asset_ingestion",
        source_material_id="source-001",
        asset_aware_doc_id="doc_asset_001",
        sections_json=json.dumps(["Methods", "Results"]),
    )
    assert "status: ok" in receipt_result
    assert validator.validate_phase(21).passed

    (project_dir / "data-artifacts.yaml").write_text(
        yaml.dump(
            {
                "data_anchors": {
                    "screened": {
                        "value": 112,
                        "source_material_id": "source-001",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    manuscript = (
        "This approach fundamentally changes the geometry of selected transnasal access "
        "when compared with conventional approaches [@wang2022_36424554].\n\n"
        "We screened 112 patients."
    )
    engine = WritingHooksEngine(project_dir)
    assert engine.check_claim_evidence_alignment(manuscript).passed
    assert engine.validate_data_artifacts(manuscript).passed
