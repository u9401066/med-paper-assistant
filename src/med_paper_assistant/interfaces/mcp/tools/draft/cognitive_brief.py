"""Cognitive section brief and narrative thread handlers for ``draft_action``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import yaml

from med_paper_assistant.infrastructure.persistence.narrative_thread_store import (
    NarrativeThreadStore,
)

from .._shared import log_tool_call, log_tool_result, resolve_project_context

_READING_ORDER = ("abstract", "introduction", "methods", "results", "discussion", "conclusions")

_THINKING_SCAFFOLDS: dict[str, dict[str, Any]] = {
    "introduction": {
        "section_mission": "Frame clinical tension, synthesize prior evidence, isolate the gap, and commit to the 🔒 NOVELTY STATEMENT and study objective.",
        "pre_write_questions": [
            "What concrete clinical problem or paradox makes this question urgent right now?",
            "Where do prior studies agree, where do they diverge, and what exact gap remains unresolved?",
            "How does our final paragraph directly set up the Methods and the exact question Discussion will answer?",
        ],
        "coherence_rules": [
            "Move each paragraph from Given (prior sentence/paragraph anchor) -> New (next layer of the funnel).",
            "Do NOT preview study results in the Introduction.",
            "Avoid mechanical openers (Furthermore, Moreover, Additionally); bridge via evidence contrast or mechanism.",
        ],
    },
    "methods": {
        "section_mission": "Operationalize the hypothesis into reproducible design, population, outcomes, and statistical tests matching Results.",
        "pre_write_questions": [
            "Can an independent researcher replicate eligibility, intervention/exposure, and primary outcome definition from this text alone?",
            "Does every statistical test planned here correspond 1-to-1 with comparisons reported in Results?",
            "Are ethics approval, registration, and sample-size/power assumptions explicitly anchored?",
        ],
        "coherence_rules": [
            "Use consistent past tense and canonical terminology defined in narrative-thread.yaml.",
            "Mirror subsection sequence with Results so readers can cross-check effortlessly.",
        ],
    },
    "results": {
        "section_mission": "Deliver objective, quantified answers in strict parallel with Methods—supporting every 🔒 Selling Point with numbers, not speculation.",
        "pre_write_questions": [
            "What is the exact primary outcome effect size, 95% CI, and p-value that answers the Introduction's aim?",
            "Do all cohort N-values match Participant Flow, Table 1, and every subgroup table?",
            "Which numbers should be highlighted in prose versus left to tables/figures to avoid redundant narration?",
        ],
        "coherence_rules": [
            "Keep Results strictly objective—defer mechanistic interpretation to Discussion.",
            "Introduce each table/figure naturally inside the claim it supports.",
        ],
    },
    "discussion": {
        "section_mission": "Directly answer Introduction's aim in paragraph 1, interpret (do not copy-paste) Results, defend all 🔒 KEY SELLING POINTS against competing literature, and face limitations honestly.",
        "pre_write_questions": [
            "Does paragraph 1 directly answer the Introduction's objective without copying Results sentences verbatim?",
            "Which prior studies contradict or qualify our findings, and what biological/methodological mechanism explains the difference?",
            "What is Reviewer 2's sharpest methodological critique, and how do we address it transparently in Limitations?",
            "Have ALL 🔒 KEY SELLING POINTS been explicitly grounded in our actual findings?",
        ],
        "coherence_rules": [
            "Open with synthesis & interpretation, not a verbatim repeat of Results statistics.",
            "Chain each paragraph via conceptual bridges (mechanism -> comparison -> clinical relevance -> limitation -> conclusion).",
        ],
    },
    "abstract": {
        "section_mission": "Condense the whole Golden Thread into a self-contained, citation-free, numerically exact mirror of the manuscript.",
        "pre_write_questions": [
            "Do Background aim, Methods design, Results primary numbers, and Conclusions match the body word-for-word in meaning and figures?",
            "Is every number in the Abstract verified against the Results section?",
        ],
        "coherence_rules": [
            "No citations; exact numeric parity with Results; stay strictly within journal word limit.",
        ],
    },
}


def _normalize_section(section: str) -> str:
    low = section.strip().lower().replace("_", " ").replace("-", " ")
    for key in _READING_ORDER:
        if key in low or (key == "methods" and "material" in low):
            return key
    return low or "manuscript"


def _load_plan_blueprint(project_dir: Path, section_key: str) -> dict[str, Any]:
    plan_path = project_dir / "manuscript-plan.yaml"
    if not plan_path.is_file():
        return {"found": False, "paragraphs": [], "assets": []}
    try:
        plan = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {"found": False, "paragraphs": [], "assets": []}
    sections = plan.get("sections") or {}
    matched_section: dict[str, Any] = {}
    if isinstance(sections, dict):
        for name, spec in sections.items():
            if _normalize_section(str(name)) == section_key and isinstance(spec, dict):
                matched_section = spec
                break
    assets = [
        item
        for item in (plan.get("asset_plan") or [])
        if isinstance(item, dict)
        and _normalize_section(str(item.get("section") or "")) == section_key
    ]
    return {
        "found": bool(matched_section),
        "word_budget": matched_section.get("word_budget"),
        "paragraphs": matched_section.get("paragraphs") or [],
        "assets": assets,
    }


def _read_ref_entry(
    meta_path: Path,
    section_key: str,
    must_cite: set[str],
) -> tuple[int, int, dict[str, Any]] | None:
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    pmid = str(meta.get("pmid") or meta_path.parent.name)
    analysis_path = meta_path.parent / "analysis.json"
    analysis: dict[str, Any] = {}
    if analysis_path.is_file():
        try:
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            analysis = {}
    usage = [
        _normalize_section(str(s))
        for s in (analysis.get("usage_sections") or meta.get("usage_sections") or [])
    ]
    cite_key = str(meta.get("citation_key") or pmid)
    is_must = pmid in must_cite or cite_key in must_cite or f"[[{cite_key}]]" in must_cite
    is_sec_match = section_key in usage
    priority = 2 if is_must else (1 if is_sec_match else 0)
    rel = int(analysis.get("relevance_score") or 0)
    summary = str(
        analysis.get("key_findings") or analysis.get("summary") or meta.get("abstract") or ""
    )
    entry = {
        "pmid": pmid,
        "citation_key": f"[[{cite_key}]]",
        "year": str(meta.get("year") or ""),
        "title": str(meta.get("title") or "")[:140],
        "matched_section": is_sec_match or is_must,
        "relevance_score": rel,
        "key_findings": summary[:240],
        "limitations": str(analysis.get("limitations") or "")[:180],
    }
    return priority, rel, entry


def _load_section_evidence(
    project_dir: Path,
    section_key: str,
    must_cite: set[str],
) -> list[dict[str, Any]]:
    refs_dir = project_dir / "references"
    if not refs_dir.is_dir():
        return []
    entries = [
        entry
        for meta_path in sorted(refs_dir.glob("*/metadata.json"))
        if (entry := _read_ref_entry(meta_path, section_key, must_cite)) is not None
    ]
    entries.sort(key=lambda item: (-item[0], -item[1], item[2]["pmid"]))
    return [item[2] for item in entries[:12]]


def _cross_section_handoffs(thread: dict[str, Any], section_key: str) -> dict[str, Any]:
    handoffs = thread.get("section_handoffs") or {}
    upstream: dict[str, Any] | None = None
    downstream: dict[str, Any] | None = None
    if section_key in _READING_ORDER:
        idx = _READING_ORDER.index(section_key)
        for prev_key in reversed(_READING_ORDER[:idx]):
            if prev_key in handoffs:
                upstream = handoffs[prev_key]
                break
        for next_key in _READING_ORDER[idx + 1 :]:
            if next_key in handoffs:
                downstream = handoffs[next_key]
                break
    all_abbrs: dict[str, str] = {}
    all_numbers: dict[str, list[str]] = {}
    for sec, card in handoffs.items():
        if isinstance(card, dict):
            all_abbrs.update(card.get("abbreviations") or {})
            if card.get("numeric_anchors"):
                all_numbers[sec] = list(card["numeric_anchors"])[:8]
    return {
        "upstream_reading_neighbor": upstream,
        "downstream_reading_neighbor": downstream,
        "defined_abbreviations": all_abbrs,
        "numeric_anchors_by_section": all_numbers,
    }


def _brief_payload(
    slug: str,
    section_key: str,
    thread: dict[str, Any],
    blueprint: dict[str, Any],
    evidence: list[dict[str, Any]],
    scaffold: dict[str, Any],
    notes: str,
) -> dict[str, Any]:
    return {
        "schema": "mdpaper.cognitive_brief.v1",
        "project": slug,
        "section": section_key,
        "golden_thread": {
            "central_thesis": thread["central_thesis"],
            "research_question": thread["research_question"],
            "novelty_statement": thread["novelty_statement"],
            "selling_points": thread["selling_points"],
            "section_mission": scaffold["section_mission"],
        },
        "canonical_terms": thread["canonical_terms"],
        "plan_blueprint": blueprint,
        "section_evidence": evidence,
        "cross_section_handoffs": _cross_section_handoffs(thread, section_key),
        "thinking_scaffold": {
            "pre_write_questions": scaffold["pre_write_questions"],
            "coherence_rules": scaffold["coherence_rules"],
        },
        "author_notes": notes.strip(),
        "next_calls": [
            {
                "tool": "draft_action",
                "arguments": {"action": "write", "section": section_key, "content": "<draft>"},
            },
            {
                "tool": "run_quality_checks",
                "arguments": {"action": "coherence", "project": slug},
            },
        ],
    }


def build_cognitive_brief(
    section: str,
    notes: str = "",
    project: Optional[str] = None,
) -> str:
    """Assemble a 5-layer cognitive drafting brief for deep, coherent section writing."""
    log_tool_call("build_cognitive_brief", {"section": section, "project": project})
    project_info, error = resolve_project_context(project, required_mode="manuscript")
    if error or project_info is None:
        return error or "❌ No active manuscript project."
    if not section.strip():
        return '❌ brief requires `section` (e.g., `draft_action(action="brief", section="Discussion")`).'

    project_dir = Path(str(project_info["project_path"]))
    section_key = _normalize_section(section)
    thread = NarrativeThreadStore(project_dir).load()
    blueprint = _load_plan_blueprint(project_dir, section_key)
    must_cite = {
        str(c)
        for para in (blueprint.get("paragraphs") or [])
        if isinstance(para, dict)
        for c in (para.get("must_cite") or [])
    }
    scaffold = _THINKING_SCAFFOLDS.get(
        section_key,
        {
            "section_mission": f"Advance the manuscript's Golden Thread cleanly in {section}.",
            "pre_write_questions": [
                "What core claim does this section establish, and what evidence grounds it?",
                "How does this section connect to upstream and downstream sections without repetition?",
            ],
            "coherence_rules": [
                "Maintain Given->New paragraph continuity and canonical terminology."
            ],
        },
    )
    payload = _brief_payload(
        slug=str(project_info.get("slug") or ""),
        section_key=section_key,
        thread=thread,
        blueprint=blueprint,
        evidence=_load_section_evidence(project_dir, section_key, must_cite),
        scaffold=scaffold,
        notes=notes,
    )
    log_tool_result("build_cognitive_brief", f"section={section_key}", success=True)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def manage_narrative_thread(
    content: str = "",
    notes: str = "",
    project: Optional[str] = None,
) -> str:
    """Read or update `.memory/narrative-thread.yaml` for whole-manuscript conceptual threading."""
    log_tool_call(
        "manage_narrative_thread", {"has_content": bool(content.strip()), "project": project}
    )
    project_info, error = resolve_project_context(project, required_mode="manuscript")
    if error or project_info is None:
        return error or "❌ No active manuscript project."

    project_dir = Path(str(project_info["project_path"]))
    store = NarrativeThreadStore(project_dir)
    if not content.strip() and not notes.strip():
        thread = store.update()
        return json.dumps(thread, ensure_ascii=False, indent=2)

    parsed: dict[str, Any] = {}
    if content.strip():
        try:
            loaded = yaml.safe_load(content)
            parsed = loaded if isinstance(loaded, dict) else {"central_thesis": content.strip()}
        except yaml.YAMLError:
            parsed = {"central_thesis": content.strip()}

    raw_terms = parsed.get("canonical_terms")
    canonical_terms: dict[str, list[str]] | None = None
    if isinstance(raw_terms, dict):
        canonical_terms = {
            str(k): [str(v) for v in vals] if isinstance(vals, list) else [str(vals)]
            for k, vals in raw_terms.items()
        }

    updated = store.update(
        central_thesis=str(parsed.get("central_thesis") or ""),
        canonical_terms=canonical_terms,
        selling_point_map=(
            parsed.get("selling_point_map")
            if isinstance(parsed.get("selling_point_map"), dict)
            else None
        ),
        notes=notes or str(parsed.get("notes") or ""),
    )
    log_tool_result("manage_narrative_thread", f"sections={len(updated['section_handoffs'])}")
    return json.dumps(updated, ensure_ascii=False, indent=2)
