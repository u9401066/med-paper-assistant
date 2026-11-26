"""Compact evidence-pack synthesis for ``reference_action(action="evidence_pack")``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from med_paper_assistant.infrastructure.persistence import ReferenceManager

from ..._shared import log_tool_call, log_tool_result
from ._deps import REFERENCE, project_context_error

_FIELD_CHAR_CAP = 240


def _clip(value: Any, limit: int = _FIELD_CHAR_CAP) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _load_analysis_json(ref_dir: Path) -> dict[str, Any]:
    path = ref_dir / "analysis.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _citation_key(meta: dict[str, Any], pmid: str) -> str:
    key = meta.get("citation_key")
    if isinstance(key, str) and key.strip():
        return f"[[{key.strip()}]]"
    authors = meta.get("authors") or []
    first = str(authors[0]).split()[0].lower() if authors else "ref"
    first = "".join(ch for ch in first if ch.isalnum()) or "ref"
    year = str(meta.get("year") or "nd")
    return f"[[{first}{year}_{pmid}]]"


def _build_entry(ref_manager: ReferenceManager, pmid: str) -> dict[str, Any]:
    detail = ref_manager.get_reference_details(pmid) or {}
    meta = detail.get("metadata") or ref_manager.get_metadata(pmid) or {}
    ref_dir = Path(str(detail.get("ref_dir") or ""))
    analysis = _load_analysis_json(ref_dir) if ref_dir.parts else {}

    authors = meta.get("authors") or []
    usage_sections = analysis.get("usage_sections") or meta.get("usage_sections") or []
    if isinstance(usage_sections, str):
        usage_sections = [s.strip() for s in usage_sections.split(",") if s.strip()]

    source = str(meta.get("source") or "").lower()
    verified = bool(meta.get("verified") or source == "pubmed_mcp")
    summary_text = analysis.get("summary") or meta.get("agent_notes") or meta.get("abstract") or ""

    return {
        "pmid": pmid,
        "citation_key": _citation_key(meta, pmid),
        "year": str(meta.get("year") or ""),
        "first_author": str(authors[0]) if authors else "",
        "journal": str(meta.get("journal") or ""),
        "title": _clip(meta.get("title") or "Unknown", 180),
        "has_fulltext": bool(ref_manager.has_fulltext(pmid)),
        "analysis_completed": bool(analysis or meta.get("analysis_completed")),
        "trust_level": "verified_mcp" if verified else "agent_fallback",
        "relevance_score": int(analysis.get("relevance_score") or 0),
        "usage_sections": list(usage_sections),
        "summary": _clip(summary_text),
        "methodology": _clip(analysis.get("methodology") or ""),
        "key_findings": _clip(analysis.get("key_findings") or ""),
        "limitations": _clip(analysis.get("limitations") or ""),
    }


def _matches_filters(
    entry: dict[str, Any],
    sections: set[str],
    query_lower: str,
    min_relevance: int,
) -> bool:
    if min_relevance > 0 and entry["relevance_score"] < min_relevance:
        return False
    if sections:
        entry_sections = {s.strip().lower() for s in entry["usage_sections"]}
        if not (entry_sections & sections):
            return False
    if query_lower:
        haystack = " ".join(
            [
                entry["pmid"],
                entry["title"],
                entry["summary"],
                entry["key_findings"],
                entry["methodology"],
            ]
        ).lower()
        if query_lower not in haystack:
            return False
    return True


def get_reference_evidence_pack(
    usage_sections: str = "",
    query: str = "",
    min_relevance: int = 0,
    project: Optional[str] = None,
) -> str:
    """Return a single-call structured evidence digest of saved project references."""
    log_tool_call("get_reference_evidence_pack", {"usage_sections": usage_sections, "query": query})
    project_error = project_context_error(project)
    if project_error:
        return project_error

    ref_manager = REFERENCE.get().ref_manager
    entries = [_build_entry(ref_manager, pmid) for pmid in ref_manager.list_references()]
    section_filter = {s.strip().lower() for s in usage_sections.split(",") if s.strip()}
    query_lower = query.strip().lower()
    matched = [
        e for e in entries if _matches_filters(e, section_filter, query_lower, min_relevance)
    ]
    matched.sort(key=lambda e: (-e["relevance_score"], e["pmid"]))
    payload = {
        "schema": "mdpaper.evidence_pack.v1",
        "total_references": len(entries),
        "matched_references": len(matched),
        "analyzed_count": sum(1 for e in entries if e["analysis_completed"]),
        "fulltext_count": sum(1 for e in entries if e["has_fulltext"]),
        "unanalyzed_pmids": [e["pmid"] for e in entries if not e["analysis_completed"]][:25],
        "filters": {
            "usage_sections": sorted(section_filter),
            "query": query.strip(),
            "min_relevance": min_relevance,
        },
        "references": matched,
    }
    log_tool_result("get_reference_evidence_pack", f"matched={len(matched)}/{len(entries)}")
    return json.dumps(payload, ensure_ascii=False, indent=2)
