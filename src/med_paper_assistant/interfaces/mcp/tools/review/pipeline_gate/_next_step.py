"""GPS next-step navigator for ``pipeline_action(action="next")``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
    PipelineGateValidator,
)

from ..._shared import log_tool_call, log_tool_error, log_tool_result, resolve_project_context
from ._common import _PHASE_NAMES

_PHASE_CALL_TEMPLATES: dict[int, list[dict[str, Any]]] = {
    0: [
        {
            "tool": "project_action",
            "arguments": {"action": "journal_profile", "target_journal": "<target_journal>"},
            "reason": "Generate journal-profile.yaml with word, reference, and style limits",
        },
        {
            "tool": "project_action",
            "arguments": {"action": "source_materials"},
            "reason": "Scan and register local source files if present",
        },
    ],
    1: [
        {
            "tool": "pipeline_action",
            "arguments": {"action": "validate_structure"},
            "reason": "Verify required project directories and metadata files",
        }
    ],
    2: [
        {
            "tool": "pubmed-search:unified_search",
            "arguments": {"query": "<research topic>", "limit": 20},
            "reason": "Search PubMed/multi-source literature to meet minimum reference count",
        },
        {
            "tool": "save_reference_mcp",
            "arguments": {"pmid": "<PMID>"},
            "reason": "Save verified PubMed references directly via MCP-to-MCP",
        },
    ],
    21: [
        {
            "tool": "reference_action",
            "arguments": {"action": "evidence_pack"},
            "reason": "Inspect unanalyzed_pmids and fulltext coverage in one call",
        },
        {
            "tool": "reference_action",
            "arguments": {"action": "analysis_save", "pmid": "<PMID>", "summary": "..."},
            "reason": "Persist structured Phase 2.1 analysis for saved references",
        },
    ],
    3: [
        {
            "tool": "validation_action",
            "arguments": {"action": "concept", "filename": "concept.md"},
            "reason": "Validate 🔒 protected sections and novelty score before drafting",
        }
    ],
    4: [
        {
            "tool": "draft_action",
            "arguments": {"action": "check_order"},
            "reason": "Confirm section writing order and create manuscript-plan.yaml",
        }
    ],
    5: [
        {
            "tool": "draft_action",
            "arguments": {"action": "brief", "section": "Introduction"},
            "reason": "Load 5-layer cognitive brief (Golden Thread, plan, section evidence, neighbor handoffs, thinking scaffold) before drafting",
        },
        {
            "tool": "draft_action",
            "arguments": {"action": "write", "filename": "manuscript.md", "content": "..."},
            "reason": "Draft or update manuscript sections (auto-refreshes narrative-thread.yaml)",
        },
        {
            "tool": "run_quality_checks",
            "arguments": {"action": "coherence"},
            "reason": "Audit paragraph flow, Results->Discussion echo, terminology drift, and Golden Thread coverage",
        },
        {
            "tool": "run_quality_checks",
            "arguments": {"action": "repair_plan"},
            "reason": "Get prioritized writing-hook fixes after drafting",
        },
    ],
    6: [
        {
            "tool": "run_quality_checks",
            "arguments": {"action": "quality_audit", "scores": "<dimension scores JSON>"},
            "reason": "Generate .audit/quality-scorecard.json for Phase 6",
        },
        {
            "tool": "run_quality_checks",
            "arguments": {"action": "data_artifacts"},
            "reason": "Cross-validate figures, tables, and data provenance",
        },
    ],
    65: [
        {
            "tool": "run_quality_checks",
            "arguments": {"action": "repair_plan", "hooks": "all"},
            "reason": "Resolve remaining quality warnings before entering autonomous review",
        }
    ],
    7: [
        {
            "tool": "pipeline_action",
            "arguments": {"action": "start_review"},
            "reason": "Initialize or continue an autonomous multi-round review loop",
        },
        {
            "tool": "run_quality_checks",
            "arguments": {"action": "review_hooks"},
            "reason": "Verify R1-R6 review quality hooks before submitting round",
        },
        {
            "tool": "pipeline_action",
            "arguments": {"action": "submit_review", "scores": "<6-dimension JSON>"},
            "reason": "Record review round scores and verdict",
        },
    ],
    8: [
        {
            "tool": "draft_action",
            "arguments": {"action": "sync_references", "filename": "manuscript.md"},
            "reason": "Resolve [[wikilinks]] and regenerate formatted References section",
        },
        {
            "tool": "validation_action",
            "arguments": {"action": "wikilinks", "filename": "manuscript.md"},
            "reason": "Confirm zero unresolved wikilinks",
        },
    ],
    9: [
        {
            "tool": "export_document",
            "arguments": {
                "action": "docx",
                "draft_filename": "manuscript.md",
                "output_filename": "paper.docx",
            },
            "reason": "Export publication-ready Word document via Pandoc",
        },
        {
            "tool": "inspect_export",
            "arguments": {"action": "inspect_docx_xml", "output_filename": "paper.docx"},
            "reason": "Smoke-check exported DOCX structure",
        },
    ],
    10: [
        {
            "tool": "run_quality_checks",
            "arguments": {"action": "pipeline_retrospective", "summary": "..."},
            "reason": "Write .audit/pipeline-run-*.md retrospective with D7/D8 headings",
        },
        {
            "tool": "run_quality_checks",
            "arguments": {"action": "meta_learning"},
            "reason": "Run D1-D9 self-improvement analysis",
        },
    ],
    11: [
        {
            "tool": "pipeline_action",
            "arguments": {
                "action": "validate_phase",
                "phase": 11,
                "response_format": "json",
                "compact": True,
            },
            "reason": "Confirm final delivery gate passes",
        }
    ],
}


def _library_wiki_payload(project_info: dict[str, Any]) -> dict[str, Any]:
    """Return a library-wiki next-step payload without forcing manuscript gates."""
    slug = project_info.get("slug")
    return {
        "schema": "mdpaper.pipeline_next.v1",
        "project": slug,
        "workflow_mode": "library-wiki",
        "status": "library_wiki_active",
        "message": (
            "Active project is in library-wiki mode. Manuscript pipeline gates are skipped "
            "unless you switch workflow_mode to 'manuscript'."
        ),
        "next_calls": [
            {
                "tool": "library_action",
                "arguments": {"action": "show_queues", "project": slug},
                "reason": "Review capture, reading, concept-build, and synthesis queues",
            },
            {
                "tool": "library_action",
                "arguments": {"action": "build_dashboard", "project": slug},
                "reason": "Inspect wiki link health and concept coverage",
            },
            {
                "tool": "reference_action",
                "arguments": {"action": "evidence_pack", "project": slug},
                "reason": "Digest saved references and analysis coverage",
            },
        ],
    }


def _customize_calls(
    phase: int,
    slug: str,
    target_journal: str,
) -> list[dict[str, Any]]:
    """Fill known project metadata into the phase's suggested compact tool calls."""
    calls: list[dict[str, Any]] = []
    for template in _PHASE_CALL_TEMPLATES.get(phase, []):
        args = dict(template["arguments"])
        if args.get("target_journal") == "<target_journal>" and target_journal:
            args["target_journal"] = target_journal
        if template["tool"] not in {"pubmed-search:unified_search", "save_reference_mcp"}:
            args.setdefault("project", slug)
        calls.append({"tool": template["tool"], "arguments": args, "reason": template["reason"]})
    return calls


def _extract_blockers(phase_entry: dict[str, Any]) -> list[dict[str, str]]:
    """Return concise failing checks for a single phase."""
    blockers: list[dict[str, str]] = []
    for item in phase_entry.get("details", []):
        if isinstance(item, dict) and not item.get("passed", True):
            blockers.append(
                {
                    "check": str(item.get("check", "unknown")),
                    "details": str(item.get("details", ""))[:240],
                }
            )
    return blockers[:10]


def _manuscript_payload(project_info: dict[str, Any]) -> dict[str, Any]:
    """Compute the single-phase GPS payload for a manuscript project."""
    slug = str(project_info.get("slug", ""))
    project_dir = Path(str(project_info["project_path"]))
    target_journal = str(project_info.get("target_journal") or "")

    status = PipelineGateValidator(project_dir).get_pipeline_status()
    phases = status.get("phases", [])
    failing = [p for p in phases if not p.get("passed", False)]

    if not failing:
        return {
            "schema": "mdpaper.pipeline_next.v1",
            "project": slug,
            "workflow_mode": "manuscript",
            "status": "complete",
            "completion_pct": status.get("completion_pct", 100.0),
            "phases_passed": status.get("phases_passed", len(phases)),
            "phases_total": status.get("phases_total", len(phases)),
            "blockers": [],
            "next_calls": _customize_calls(11, slug, target_journal),
        }

    current = failing[0]
    phase_num = int(current["phase"])
    return {
        "schema": "mdpaper.pipeline_next.v1",
        "project": slug,
        "workflow_mode": "manuscript",
        "status": "in_progress",
        "current_phase": phase_num,
        "current_phase_name": current.get("name") or _PHASE_NAMES.get(phase_num, ""),
        "completion_pct": status.get("completion_pct", 0.0),
        "phases_passed": status.get("phases_passed", 0),
        "phases_total": status.get("phases_total", len(phases)),
        "blocker_count": current.get("critical_failures", 0),
        "blockers": _extract_blockers(current),
        "next_calls": _customize_calls(phase_num, slug, target_journal),
        "validate_call": {
            "tool": "pipeline_action",
            "arguments": {
                "action": "validate_phase",
                "phase": phase_num,
                "project": slug,
                "response_format": "json",
                "compact": True,
            },
        },
    }


def pipeline_next(project: Optional[str] = None) -> str:
    """Return a concise JSON GPS snapshot with the exact next compact MCP calls."""
    log_tool_call("pipeline_next", {"project": project})
    try:
        project_info, error = resolve_project_context(project)
        if error or project_info is None:
            return (
                error
                or '❌ No active project. Call `project_action(action="list")` or `project_action(action="create", name="...")`.'
            )

        workflow = str(project_info.get("workflow_mode") or "manuscript").strip().lower()
        payload = (
            _library_wiki_payload(project_info)
            if workflow == "library-wiki"
            else _manuscript_payload(project_info)
        )
        log_tool_result("pipeline_next", f"status={payload['status']}", success=True)
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception as e:
        log_tool_error("pipeline_next", e)
        return f"❌ Error computing next pipeline step: {e}"
