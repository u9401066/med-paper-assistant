"""Handlers that expose reference material for analysis and store the analysis."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from med_paper_assistant.infrastructure.persistence import ReferenceManager
from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
    REFERENCE_ANALYSIS_TEXT_MINIMUMS,
    derive_reference_source_revision,
)

from ..._shared import log_tool_call, log_tool_result
from ._deps import REFERENCE, project_context_error


def _analysis_header(pmid: str, meta: dict) -> list[str]:
    return [
        f"# Reference Analysis Package: PMID {pmid}",
        f"**Title**: {meta.get('title', 'N/A')}",
        f"**Authors**: {', '.join(meta.get('authors', [])[:5])}",
        f"**Journal**: {meta.get('journal', 'N/A')} ({meta.get('year', 'N/A')})",
        f"**DOI**: {meta.get('doi', 'N/A')}",
        "",
        "## Abstract",
        meta.get("abstract", "(No abstract available)"),
        "",
    ]


def _append_fulltext_sections(
    lines: list[str], ref_manager: ReferenceManager, pmid: str, ref_dir: Path
) -> bool:
    """Append every available fulltext block and report whether any was found."""
    # Check for fulltext
    fulltext_available = False
    if ref_manager.has_fulltext(pmid):
        text = ref_manager.read_fulltext(pmid)
        if text and not text.startswith("Error"):
            fulltext_available = True
            lines.append("## Fulltext (from PDF)")
            # Limit to reasonable size for subagent context
            if len(text) > 30000:
                lines.append(text[:30000])
                lines.append(f"\n... [Truncated at 30000 chars. Total: {len(text)}]")
            else:
                lines.append(text)
            lines.append("")

    # Check for normalized asset-aware parsed sections first
    normalized_sections_path = ref_dir / "artifacts" / "asset-aware" / "sections.md"
    if normalized_sections_path.is_file():
        content = normalized_sections_path.read_text(encoding="utf-8")
        lines.append("## Fulltext (asset-aware parsed)")
        lines.append(content[:10000])
        lines.append("")
        fulltext_available = True

    # Legacy fallback: older parsed section layout
    analysis_sections_dir = ref_dir / "sections"
    if analysis_sections_dir.is_dir():
        for section_file in sorted(analysis_sections_dir.iterdir()):
            if section_file.suffix == ".md":
                section_name = section_file.stem
                content = section_file.read_text(encoding="utf-8")
                lines.append(f"## Section: {section_name} (asset-aware parsed)")
                lines.append(content[:10000])
                lines.append("")
                fulltext_available = True

    return fulltext_available


def _append_analysis_footer(lines: list[str], meta: dict, fulltext_available: bool) -> None:
    lines.append("---")
    lines.append(f"**Fulltext available**: {'Yes' if fulltext_available else 'No (abstract only)'}")
    lines.append(
        f"**Analysis status**: {'Completed' if meta.get('analysis_completed') else 'PENDING'}"
    )

    if not fulltext_available:
        lines.append("")
        lines.append(
            "⚠️ **Abstract-only reference**: Analysis will be limited. "
            "This reference can only support general background claims, "
            "NOT specific methodological or quantitative citations."
        )


def get_reference_for_analysis(pmid: str, project: Optional[str] = None) -> str:
    """
    📖 Get reference content for subagent analysis (Phase 2.1).

    Returns structured reference data (abstract + fulltext if available)
    for a subagent to read and produce analysis. Use this to extract
    material before calling save_reference_analysis().

    Design: Each reference should be analyzed by a SEPARATE subagent
    to prevent context pollution across papers.

    Args:
        pmid: PubMed ID of saved reference
        project: Project slug (uses current if omitted)
    """
    ref_manager = REFERENCE.get().ref_manager
    log_tool_call("get_reference_for_analysis", {"pmid": pmid, "project": project})

    project_error = project_context_error(project, with_project_list=False)
    if project_error:
        return project_error

    # Get reference metadata
    detail = ref_manager.get_reference_details(pmid)
    if not detail:
        return f"❌ Reference PMID:{pmid} not found in saved references."

    meta = detail.get("metadata", {})
    ref_dir = Path(detail.get("ref_dir", ""))

    lines = _analysis_header(pmid, meta)
    fulltext_available = _append_fulltext_sections(lines, ref_manager, pmid, ref_dir)
    _append_analysis_footer(lines, meta, fulltext_available)

    result = "\n".join(lines)
    log_tool_result("get_reference_for_analysis", f"pmid={pmid}, fulltext={fulltext_available}")
    return result


@dataclass(frozen=True)
class _AnalysisPlan:
    ref_dir: Path
    analysis: dict
    sections_list: list[str]
    source_revision: str


def _validate_analysis_input(
    summary: str,
    methodology: str,
    key_findings: str,
    limitations: str,
    relevance_score: int,
) -> Union[dict[str, str], str]:
    """Return the stripped structured fields, or the error message to show the caller."""
    structured_fields = {
        "summary": summary.strip(),
        "methodology": methodology.strip(),
        "key_findings": key_findings.strip(),
        "limitations": limitations.strip(),
    }
    insufficient_fields = [
        f"{name}>={REFERENCE_ANALYSIS_TEXT_MINIMUMS[name]} chars"
        for name, value in structured_fields.items()
        if len(value) < REFERENCE_ANALYSIS_TEXT_MINIMUMS[name]
    ]
    if insufficient_fields:
        return (
            "❌ A complete reference analysis requires substantive fields: "
            + ", ".join(insufficient_fields)
            + "."
        )
    if isinstance(relevance_score, bool) or not isinstance(relevance_score, int):
        return "❌ relevance_score must be an integer from 1 to 5."
    if not 1 <= relevance_score <= 5:
        return "❌ relevance_score must be between 1 and 5."
    return structured_fields


def _prepare_analysis(
    ref_manager: ReferenceManager,
    pmid: str,
    structured_fields: dict[str, str],
    usage_sections: str,
    relevance_score: int,
) -> Union[_AnalysisPlan, str]:
    """Resolve the reference and build the analysis record, or return the error message."""
    # Find reference directory
    detail = ref_manager.get_reference_details(pmid)
    if not detail:
        return f"❌ Reference PMID:{pmid} not found."

    ref_dir = Path(detail.get("ref_dir", ""))

    # Parse usage sections
    sections_list = (
        [s.strip() for s in usage_sections.split(",") if s.strip()] if usage_sections else []
    )
    if not sections_list:
        return "❌ usage_sections must name at least one manuscript section."

    metadata = ref_manager.get_metadata(pmid)
    source_valid, source_details, source_revision, source_kind = derive_reference_source_revision(
        ref_dir, metadata
    )
    if not source_valid:
        return f"❌ Reference source evidence is incomplete: {source_details}"

    # Build analysis data
    analysis = {
        "schema": "mdpaper.reference_analysis.v1",
        "source_tool": "save_reference_analysis",
        "pmid": pmid,
        "summary": structured_fields["summary"],
        "methodology": structured_fields["methodology"],
        "key_findings": structured_fields["key_findings"],
        "limitations": structured_fields["limitations"],
        "usage_sections": sections_list,
        "relevance_score": relevance_score,
        "source_revision_sha256": source_revision,
        "source_kind": source_kind,
        "analyzed_at": __import__("datetime").datetime.now().astimezone().isoformat(),
    }
    return _AnalysisPlan(ref_dir, analysis, sections_list, source_revision)


def _store_analysis(ref_manager: ReferenceManager, pmid: str, plan: _AnalysisPlan) -> str:
    analysis = plan.analysis
    summary = analysis["summary"]
    sections_list = plan.sections_list

    # Save analysis.json
    analysis_path = plan.ref_dir / "analysis.json"
    analysis_path.write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    analysis_hash = hashlib.sha256(analysis_path.read_bytes()).hexdigest()

    update_result = ref_manager.update_reference_analysis_status(
        pmid,
        summary,
        usage_sections=sections_list,
        analysis_completed=True,
        analysis_receipt={
            "analysis_artifact_sha256": analysis_hash,
            "analysis_source_tool": "save_reference_analysis",
            "analysis_completed_at": analysis["analyzed_at"],
            "analysis_source_revision_sha256": plan.source_revision,
        },
    )
    if update_result != f"Updated {pmid}.":
        return f"⚠️ Analysis saved but metadata update failed: {update_result}"

    result = (
        f"✅ Analysis saved for PMID:{pmid}\n"
        f"**Summary**: {summary[:100]}...\n"
        f"**Usage sections**: {', '.join(sections_list) or 'Not specified'}\n"
        f"**Relevance**: {'⭐' * analysis['relevance_score']}\n"
        f"📁 Saved to: {analysis_path}"
    )
    log_tool_result("save_reference_analysis", f"pmid={pmid}, sections={sections_list}")
    return result


def save_reference_analysis(
    pmid: str,
    summary: str,
    methodology: str = "",
    key_findings: str = "",
    limitations: str = "",
    usage_sections: str = "",
    relevance_score: int = 0,
    project: Optional[str] = None,
) -> str:
    """
    💾 Save subagent's analysis result for a reference (Phase 2.1).

    After a subagent reads and analyzes a reference (via get_reference_for_analysis),
    save the structured analysis back. This creates an analysis.json file in the
    reference directory and updates metadata.

    Args:
        pmid: PubMed ID of the reference
        summary: 2-3 sentence summary of what this paper contributes
        methodology: Study design, sample size, key methods (1-2 sentences)
        key_findings: Main results and conclusions (2-3 bullet points as text)
        limitations: Noted limitations or bias concerns
        usage_sections: Comma-separated sections where this ref is useful
                       (e.g., "Introduction,Discussion" or "Methods,Results")
        relevance_score: 1-5 relevance to current project (5=essential)
        project: Project slug (uses current if omitted)
    """
    ref_manager = REFERENCE.get().ref_manager
    log_tool_call("save_reference_analysis", {"pmid": pmid, "project": project})

    structured_fields = _validate_analysis_input(
        summary, methodology, key_findings, limitations, relevance_score
    )
    if isinstance(structured_fields, str):
        return structured_fields

    project_error = project_context_error(project, with_project_list=False)
    if project_error:
        return project_error

    plan = _prepare_analysis(ref_manager, pmid, structured_fields, usage_sections, relevance_score)
    if isinstance(plan, str):
        return plan

    return _store_analysis(ref_manager, pmid, plan)
