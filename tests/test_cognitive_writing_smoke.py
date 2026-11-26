"""End-to-end edge & smoke tests for the Cognitive Writing Harness (brief, thread, coherence)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from med_paper_assistant.infrastructure.persistence.project_manager import _reset_project_manager
from med_paper_assistant.interfaces.mcp.server import create_server

pytestmark = pytest.mark.smoke


def _text(result: Any) -> str:
    content = result[0] if isinstance(result, tuple) else getattr(result, "content", result)
    if isinstance(content, list):
        return "\n".join(getattr(item, "text", str(item)) for item in content)
    return str(content)


def _seed_project_artifacts(project_dir: Path) -> None:
    (project_dir / "concept.md").write_text(
        "# Research Concept\n\n"
        "## Research Question\n"
        "Does remimazolam reduce postoperative delirium compared with propofol in older adults undergoing orthopedic surgery?\n\n"
        "## 🔒 NOVELTY STATEMENT\n"
        "First multicenter titration-guided remimazolam protocol linking intraoperative electroencephalogram burst suppression reduction to lower delirium.\n\n"
        "## 🔒 KEY SELLING POINTS\n"
        "- Titration-guided remimazolam halved postoperative delirium incidence relative to propofol.\n"
        "- Intraoperative electroencephalogram burst suppression duration mediated cognitive protection.\n"
        "- Hemodynamic hypotension episodes decreased without delaying extubation recovery.\n",
        encoding="utf-8",
    )
    (project_dir / "manuscript-plan.yaml").write_text(
        "sections:\n"
        "  discussion:\n"
        "    word_budget: 1200\n"
        "    paragraphs:\n"
        "      - id: D1\n"
        "        topic: Direct answer to primary delirium objective\n"
        "        must_cite: ['39000021']\n"
        "asset_plan:\n"
        "  - id: Fig1\n"
        "    section: discussion\n"
        "    caption: Mediation diagram\n",
        encoding="utf-8",
    )
    ref_dir = project_dir / "references" / "39000021"
    ref_dir.mkdir(parents=True, exist_ok=True)
    (ref_dir / "metadata.json").write_text(
        json.dumps(
            {
                "pmid": "39000021",
                "citation_key": "chen2024_39000021",
                "title": "Electroencephalogram burst suppression and delirium under remimazolam",
                "authors": ["Chen Y", "Lin H"],
                "journal": "Br J Anaesth",
                "year": "2024",
                "abstract": "Remimazolam reduced burst suppression and delirium.",
            }
        ),
        encoding="utf-8",
    )
    (ref_dir / "analysis.json").write_text(
        json.dumps(
            {
                "pmid": "39000021",
                "summary": "Multicenter trial on burst suppression mediation.",
                "key_findings": "Burst suppression decreased by 48% with lower delirium incidence.",
                "limitations": "Limited to 72-hour cognitive follow-up.",
                "usage_sections": ["Discussion", "Introduction"],
                "relevance_score": 5,
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_cognitive_writing_nonlinear_smoke_and_coherence_convergence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MEDPAPER_BASE_DIR", str(tmp_path))
    monkeypatch.setenv("MEDPAPER_TOOL_SURFACE", "compact")
    _reset_project_manager()

    srv = create_server(tool_surface="compact")
    await srv.call_tool(
        "project_action",
        {
            "action": "create",
            "name": "Remimazolam Cognitive Study",
            "paper_type": "original-research",
        },
    )
    project_dir = tmp_path / "projects" / "remimazolam-cognitive-study"
    _seed_project_artifacts(project_dir)

    # 1. Configure narrative thread with canonical terminology (older adults != elderly patients)
    thread_raw = _text(
        await srv.call_tool(
            "draft_action",
            {
                "action": "thread",
                "content": json.dumps(
                    {
                        "central_thesis": "Titration-guided remimazolam lowers delirium by curbing burst suppression and hypotension.",
                        "canonical_terms": {
                            "older adults": ["elderly patients", "geriatric cohort"]
                        },
                    }
                ),
            },
        )
    )
    thread = json.loads(thread_raw)
    assert thread["schema"] == "mdpaper.narrative_thread.v1"
    assert len(thread["selling_points"]) == 3
    assert (project_dir / ".memory" / "narrative-thread.yaml").is_file()

    # 2. Seed nonlinear drafts (Methods + Results exist before Discussion) and pull 5-layer Brief
    drafts_dir = project_dir / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    (drafts_dir / "results.md").write_text(
        "## Results\n\n"
        "Among 320 older adults, postoperative delirium occurred in 11.2% with remimazolam versus 21.8% with propofol (RR 0.51, p=0.008).\n",
        encoding="utf-8",
    )
    brief = json.loads(
        _text(await srv.call_tool("draft_action", {"action": "brief", "section": "Discussion"}))
    )
    assert brief["schema"] == "mdpaper.cognitive_brief.v1"
    assert brief["plan_blueprint"]["found"] is True
    assert brief["section_evidence"][0]["pmid"] == "39000021"
    assert brief["cross_section_handoffs"]["upstream_reading_neighbor"]["section"] == "results"
    assert "11.2%" in brief["cross_section_handoffs"]["numeric_anchors_by_section"]["results"]
    assert len(brief["thinking_scaffold"]["pre_write_questions"]) >= 3

    # 3. Write a deliberately flawed manuscript to verify ALL 6 detectors (COH-1..3, THR-1..3)
    flawed_ms = (
        "# Abstract\n\n"
        "In 320 older adults, postoperative delirium fell to 14.5% versus 21.8% (p=0.008) with remimazolam.\n\n"
        "# Introduction\n\n"
        "Surgical anesthesia requires careful hemodynamic monitoring in busy hospitals across modern operating rooms every day.\n\n"
        "Furthermore, orthopedic fractures increase hospital length of stay and rehabilitation costs across surgical wards globally.\n\n"
        "This trial aimed to evaluate whether remimazolam lowers delirium and electroencephalogram burst suppression in elderly patients.\n\n"
        "# Methods\n\n"
        "We enrolled 320 older adults randomized to titration-guided remimazolam or propofol with continuous electroencephalogram monitoring.\n\n"
        "# Results\n\n"
        "Postoperative delirium occurred in 11.2% of remimazolam recipients compared with 21.8% of propofol recipients (RR 0.51, p=0.008) while electroencephalogram burst suppression decreased substantially.\n\n"
        "# Discussion\n\n"
        "Postoperative delirium occurred in 11.2% of remimazolam recipients compared with 21.8% of propofol recipients in this trial [[chen2024_39000021]]. "
        "Hospital administrators should evaluate pharmacy inventory logistics across regional networks.\n"
    )
    (drafts_dir / "manuscript.md").write_text(flawed_ms, encoding="utf-8")

    flawed_audit = json.loads(
        _text(
            await srv.call_tool(
                "run_quality_checks", {"action": "coherence", "draft_filename": "manuscript.md"}
            )
        )
    )
    codes = {item["code"] for item in flawed_audit["issues"]}
    assert {"COH-1", "COH-2", "COH-3", "THR-1", "THR-2", "THR-3"}.issubset(codes)
    assert flawed_audit["coherence_score"] < 60
    assert any(not sp["grounded_in"] for sp in flawed_audit["selling_point_coverage"])

    # 4. Revise into a coherent, concept-threaded manuscript and verify convergence to clean (100)
    clean_ms = (
        "# Abstract\n\n"
        "In 320 older adults, titration-guided remimazolam reduced postoperative delirium to 11.2% versus 21.8% (RR 0.51, p=0.008), cut electroencephalogram burst suppression, and lowered hypotension without delaying extubation recovery.\n\n"
        "# Introduction\n\n"
        "Postoperative delirium threatens cognitive recovery in older adults undergoing orthopedic anesthesia, especially when deep sedation triggers intraoperative electroencephalogram burst suppression [[chen2024_39000021]].\n\n"
        "Because burst suppression and hemodynamic hypotension often co-occur under propofol anesthesia, a multicenter titration-guided remimazolam protocol linking intraoperative electroencephalogram burst suppression reduction to lower delirium remains urgently needed.\n\n"
        "Therefore, we investigated whether titration-guided remimazolam reduces postoperative delirium, intraoperative electroencephalogram burst suppression, and hemodynamic hypotension without delaying extubation recovery in older adults.\n\n"
        "# Methods\n\n"
        "We conducted a multicenter randomized trial enrolling 320 older adults assigned to titration-guided remimazolam or propofol with standardized electroencephalogram monitoring.\n\n"
        "# Results\n\n"
        "Titration-guided remimazolam halved postoperative delirium incidence (11.2% vs 21.8%, RR 0.51, p=0.008), shortened intraoperative electroencephalogram burst suppression duration, and decreased hemodynamic hypotension episodes without delaying extubation recovery.\n\n"
        "# Discussion\n\n"
        "Our multicenter titration-guided remimazolam protocol directly answered the primary objective by halving postoperative delirium in older adults through reduced intraoperative electroencephalogram burst suppression and fewer hemodynamic hypotension episodes without delaying extubation recovery [[chen2024_39000021]].\n\n"
        "Consistent with prior mechanistic evidence on burst suppression mediation [[chen2024_39000021]], curbing hemodynamic hypotension and excessive cortical suppression explains why remimazolam preserved cognitive recovery without prolonging extubation.\n"
    )
    (drafts_dir / "manuscript.md").write_text(clean_ms, encoding="utf-8")

    clean_audit = json.loads(
        _text(
            await srv.call_tool(
                "run_quality_checks", {"action": "coherence", "draft_filename": "manuscript.md"}
            )
        )
    )
    assert clean_audit["status"] == "clean", clean_audit["issues"]
    assert clean_audit["coherence_score"] == 100
    assert all(sp["grounded_in"] for sp in clean_audit["selling_point_coverage"])


@pytest.mark.asyncio
async def test_cognitive_brief_edge_empty_section_and_missing_plan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MEDPAPER_BASE_DIR", str(tmp_path))
    _reset_project_manager()

    srv = create_server(tool_surface="compact")
    await srv.call_tool("project_action", {"action": "create", "name": "Bare Edge Project"})

    # Missing section argument returns actionable error cleanly
    with pytest.raises(Exception, match="brief requires"):
        await srv.call_tool("draft_action", {"action": "brief", "section": ""})

    # Works cleanly even when manuscript-plan.yaml and references are empty
    brief = json.loads(
        _text(await srv.call_tool("draft_action", {"action": "brief", "section": "Introduction"}))
    )
    assert brief["plan_blueprint"]["found"] is False
    assert brief["section_evidence"] == []
    assert brief["thinking_scaffold"]["pre_write_questions"]
