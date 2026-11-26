"""End-to-end contract tests for v1.2.0 Agent-First Harness & Compact Ergonomics."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from med_paper_assistant.infrastructure.persistence.project_manager import _reset_project_manager
from med_paper_assistant.interfaces.mcp.config import SERVER_INSTRUCTIONS
from med_paper_assistant.interfaces.mcp.server import create_server
from med_paper_assistant.interfaces.mcp.tools._shared.facade_dispatch import (
    format_unsupported_action_error,
)
from med_paper_assistant.interfaces.mcp.tools._shared.guidance import (
    build_startup_guidance,
    compact_tool_hint,
)
from med_paper_assistant.interfaces.mcp.tools._shared.progress import report_tool_progress

ROOT = Path(__file__).resolve().parents[1]
BUNDLED_RESEARCH_AGENTS = (
    "concept-challenger.agent.md",
    "domain-reviewer.agent.md",
    "literature-searcher.agent.md",
    "meta-learner.agent.md",
    "methodology-reviewer.agent.md",
    "paper-reviewer.agent.md",
    "reference-analyzer.agent.md",
    "review-orchestrator.agent.md",
    "statistics-reviewer.agent.md",
)


def _extract_text(result: Any) -> str:
    content = result[0] if isinstance(result, tuple) else getattr(result, "content", result)
    if isinstance(content, list):
        return "\n".join(getattr(item, "text", str(item)) for item in content)
    return str(content)


def _find_leaks(text: str, full_only: list[str]) -> list[str]:
    return [
        name
        for name in full_only
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text)
    ]


@pytest.mark.asyncio
async def test_compact_instructions_and_bundled_agents_have_zero_full_only_leaks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MEDPAPER_BASE_DIR", str(tmp_path))
    _reset_project_manager()

    full_tools = {t.name for t in await create_server(tool_surface="full").list_tools()}
    compact_tools = {t.name for t in await create_server(tool_surface="compact").list_tools()}
    assert len(full_tools) == 118
    assert len(compact_tools) == 12
    full_only = sorted(full_tools - compact_tools)

    # Strip facade action="..." option lists so only standalone full-only tool names are flagged.
    action_opt_re = re.compile(r'action="[^"]+"(?:\s*\\?\|\s*"[^"]+")*')
    instruction_text = action_opt_re.sub("", SERVER_INSTRUCTIONS)
    assert _find_leaks(instruction_text, full_only) == []
    assert 'draft_action(action="review_asset")' not in SERVER_INSTRUCTIONS
    assert 'analysis_action(action="review_asset")' in SERVER_INSTRUCTIONS
    assert 'pipeline_action(action="next")' in SERVER_INSTRUCTIONS
    assert 'reference_action(action="evidence_pack"' in SERVER_INSTRUCTIONS
    assert 'run_quality_checks(action="repair_plan")' in SERVER_INSTRUCTIONS

    for agent_file in BUNDLED_RESEARCH_AGENTS:
        raw = (ROOT / ".github" / "agents" / agent_file).read_text(encoding="utf-8")
        cleaned = action_opt_re.sub("", raw)
        leaks = _find_leaks(cleaned, full_only)
        assert leaks == [], f"{agent_file} leaked full-only tools: {leaks}"


@pytest.mark.asyncio
async def test_report_tool_progress_tolerates_context_outside_request() -> None:
    ctx = AsyncMock()
    ctx.report_progress.side_effect = ValueError("Context is not available outside of a request")
    await report_tool_progress(ctx, 1, 3, "Working")
    ctx.report_progress.assert_awaited_once()


def test_compact_tool_hint_and_startup_guidance_follow_surface(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MEDPAPER_TOOL_SURFACE", "compact")
    assert compact_tool_hint("write_draft") == 'draft_action(action="write")'
    assert (
        compact_tool_hint("evolve_constraint") == 'run_quality_checks(action="evolve_constraint")'
    )

    audit = tmp_path / ".audit"
    audit.mkdir()
    (audit / "pending-evolutions.yaml").write_text(
        "items:\n- id: PE-1\n  type: suggestion\n  status: pending\n  source: test\n  payload: {}\n",
        encoding="utf-8",
    )
    startup = build_startup_guidance(tmp_path)
    assert startup is not None
    assert 'run_quality_checks(action="pending_evolutions"' in startup
    assert "apply_pending_evolutions" not in startup


def test_fuzzy_unsupported_action_error_suggests_close_match() -> None:
    msg = format_unsupported_action_error(
        "pipeline_action",
        "doctr",
        ["doctor", "next", "heartbeat"],
        aliases={"gps": "next"},
    )
    assert "Did you mean: doctor?" in msg
    assert 'pipeline_action(action="list")' in msg


@pytest.mark.asyncio
async def test_compact_end_to_end_gps_evidence_pack_and_repair_plan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MEDPAPER_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MEDPAPER_TOOL_SURFACE", "compact")
    _reset_project_manager()

    srv = create_server(tool_surface="compact")

    # 1. Empty project name is rejected cleanly (no silent 'untitled' project)
    with pytest.raises(Exception, match="name"):
        await srv.call_tool("project_action", {"action": "create", "name": "   "})

    # 2. Create manuscript project and verify pipeline_action(action="next") GPS
    await srv.call_tool(
        "project_action",
        {
            "action": "create",
            "name": "Remimazolam Delirium Study",
            "paper_type": "original-research",
            "target_journal": "British Journal of Anaesthesia",
        },
    )
    gps_raw = _extract_text(await srv.call_tool("pipeline_action", {"action": "next"}))
    gps = json.loads(gps_raw)
    assert gps["schema"] == "mdpaper.pipeline_next.v1"
    assert gps["workflow_mode"] == "manuscript"
    assert gps["current_phase"] == 0
    assert gps["next_calls"][0]["tool"] == "project_action"
    assert gps["next_calls"][0]["arguments"]["action"] == "journal_profile"
    assert gps["next_calls"][0]["arguments"]["target_journal"] == "British Journal of Anaesthesia"
    assert len(gps_raw) < 3000

    # 3. Save reference + analysis using list usage_sections and save_analysis alias, then evidence_pack
    await srv.call_tool(
        "reference_action",
        {
            "action": "save_agent",
            "article": {
                "pmid": "39000011",
                "title": "Remimazolam vs Propofol in Elderly Surgical Patients",
                "authors": ["Chen Y", "Lin H"],
                "journal": "Br J Anaesth",
                "year": "2024",
                "abstract": "Background: Elderly patients face postoperative delirium. Methods: Randomized trial of 320 surgical patients. Results: Remimazolam reduced delirium from 21.8% to 11.2% (RR 0.51, p=0.008). Conclusion: Remimazolam lowers delirium incidence.",
                "fulltext_unavailable_reason": "Publisher paywall without PMC open-access version.",
            },
        },
    )
    ref_dir = tmp_path / "projects" / "remimazolam-delirium-study" / "references" / "39000011"
    meta_path = ref_dir / "metadata.json"
    meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
    meta_data["fulltext_unavailable_reason"] = "Publisher paywall without PMC open-access version."
    meta_path.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
    save_analysis_out = _extract_text(
        await srv.call_tool(
            "reference_action",
            {
                "action": "save_analysis",
                "pmid": "39000011",
                "summary": "Randomized controlled trial evaluating remimazolam versus propofol for postoperative delirium prevention in elderly surgical patients.",
                "methodology": "Single-center randomized controlled trial enrolling 320 elderly patients undergoing elective surgery with 3-day delirium assessment.",
                "key_findings": "Remimazolam lowered postoperative delirium incidence from 21.8% to 11.2% (RR 0.51, 95% CI 0.31-0.84, p=0.008).",
                "limitations": "Single-center design with short 3-day follow-up window and exclusion of emergency surgical cases.",
                "usage_sections": ["Introduction", "Discussion"],
                "relevance_score": 5,
            },
        )
    )
    assert "✅ Analysis saved for PMID:39000011" in save_analysis_out

    pack_raw = _extract_text(
        await srv.call_tool(
            "reference_action",
            {"action": "evidence_pack", "usage_sections": ["Introduction"]},
        )
    )
    pack = json.loads(pack_raw)
    assert pack["schema"] == "mdpaper.evidence_pack.v1"
    assert pack["total_references"] == 1
    assert pack["matched_references"] == 1
    assert pack["analyzed_count"] == 1
    assert pack["references"][0]["citation_key"].startswith("[[")
    assert pack["references"][0]["relevance_score"] == 5

    # 4. Write a section draft (without manuscript.md) and run repair_plan + writing_hooks
    drafts_dir = tmp_path / "projects" / "remimazolam-delirium-study" / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    (drafts_dir / "introduction.md").write_text(
        "# Introduction\n\n"
        "Postoperative delirium is a pivotal and multifaceted complication [[chen2024_39000011]]. "
        "It is worth noting that anesthesia plays a crucial role in elderly care.\n",
        encoding="utf-8",
    )

    repair_raw = _extract_text(
        await srv.call_tool(
            "run_quality_checks",
            {
                "action": "repair_plan",
                "hooks": "A3,A4,C5",
                "draft_filename": "introduction.md",
            },
        )
    )
    repair = json.loads(repair_raw)
    assert repair["schema"] == "mdpaper.repair_plan.v1"
    assert repair["target_file"] == "introduction.md"
    assert repair["status"] == "needs_repair"
    assert repair["counts"]["total_items"] >= 1
    assert repair["items"][0]["priority"] == 1
    assert repair["items"][0]["suggested_call"]["tool"] in {"draft_action", "validation_action"}

    # Fallback when manuscript.md is absent also works automatically for writing_hooks
    hooks_out = _extract_text(
        await srv.call_tool("run_quality_checks", {"action": "writing_hooks", "hooks": "A3"})
    )
    assert "target_file: introduction.md" in hooks_out

    # 5. Library-wiki mode GPS + library_action(action="help")
    await srv.call_tool(
        "project_action",
        {"action": "create", "name": "Sedation Knowledge Base", "workflow_mode": "library-wiki"},
    )
    wiki_gps = json.loads(_extract_text(await srv.call_tool("pipeline_action", {"action": "next"})))
    assert wiki_gps["workflow_mode"] == "library-wiki"
    assert wiki_gps["next_calls"][0]["tool"] == "library_action"

    lib_help = json.loads(_extract_text(await srv.call_tool("library_action", {"action": "help"})))
    assert lib_help["schema"] == "mdpaper.facade_actions.v1"
    assert lib_help["tool"] == "library_action"
    assert "write_note" in lib_help["actions"]
