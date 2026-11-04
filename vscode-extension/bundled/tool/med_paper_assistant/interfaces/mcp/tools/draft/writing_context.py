"""
Draft Writing Context

check_writing_order and draft_section implementations.
"""

import os
import re
from typing import Any, Optional

from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.prompts import SECTION_PROMPTS

from .._shared import (
    get_concept_path,
    log_tool_call,
    log_tool_result,
)
from .writing_gates import (
    _check_section_prerequisites,
    _guard_writing_tool,
    _section_gate_error,
)


def _get_author_block() -> str:
    """Get formatted author block from current project's project.json.

    Returns:
        Formatted author block markdown, or empty string if no authors.
    """
    from med_paper_assistant.domain.value_objects.author import Author, generate_author_block
    from med_paper_assistant.infrastructure.persistence import get_project_manager

    pm = get_project_manager()
    current_info = pm.get_project_info()
    if not current_info or not current_info.get("authors"):
        return ""

    authors_data = current_info["authors"]
    author_objs = [Author.from_dict(a) for a in authors_data]
    if not author_objs or not any(a.name for a in author_objs):
        return ""

    return generate_author_block(author_objs)


def _existing_draft_titles(drafts_dir: str) -> list[str]:
    existing_drafts = []
    if os.path.isdir(drafts_dir):
        existing_drafts = [
            f.replace(".md", "").replace("_", " ").replace("-", " ").title()
            for f in os.listdir(drafts_dir)
            if f.endswith(".md") and f != "concept.md"
        ]
    return [s.lower() for s in existing_drafts]


def _section_done(name: str, existing_lower: list[str]) -> bool:
    return any(name.lower() in ex or ex in name.lower() for ex in existing_lower)


def _progress_table(sorted_sections: list, existing_lower: list[str]) -> str:
    output = "| # | Section | 狀態 | 前置條件 |\n"
    output += "|---|---------|------|----------|\n"

    for section_name, info in sorted_sections:
        order = info["order"]
        prereqs = info.get("prerequisites", [])

        # Check if this section exists
        section_exists = _section_done(section_name, existing_lower)
        status = "✅ 已完成" if section_exists else "⬜ 未開始"

        # Check prerequisites
        prereq_status = []
        for p in prereqs:
            p_exists = _section_done(p, existing_lower)
            prereq_status.append(f"{'✅' if p_exists else '❌'} {p}")

        prereq_str = ", ".join(prereq_status) if prereq_status else "（無）"
        output += f"| {order} | {section_name} | {status} | {prereq_str} |\n"
    return output


def _next_section_hint(sorted_sections: list, existing_lower: list[str]) -> str:
    # Suggest next section
    for section_name, info in sorted_sections:
        if not _section_done(section_name, existing_lower):
            prereqs = info.get("prerequisites", [])
            all_met = all(_section_done(p, existing_lower) for p in prereqs)
            if all_met:
                return f"\n💡 **建議下一步**: 撰寫 **{section_name}**"
    return ""


def _check_writing_order(project: Optional[str]) -> str:
    log_tool_call("check_writing_order", {"project": project})

    guard_error = _guard_writing_tool("check_writing_order", project, log_invalid=False)
    if guard_error is not None:
        return guard_error

    from med_paper_assistant.domain.paper_types import WRITING_ORDER, _format_writing_order
    from med_paper_assistant.infrastructure.persistence import get_project_manager

    pm = get_project_manager()
    current_info = pm.get_project_info()
    if not current_info or not current_info.get("project_path"):
        return "❌ 無法取得專案資訊"

    project_path = str(current_info["project_path"])
    paper_type = current_info.get("paper_type", "other")
    drafts_dir = os.path.join(project_path, "drafts")

    order_map = WRITING_ORDER.get(paper_type, {})
    if not order_map:
        result = f"📋 Paper type `{paper_type}` 無定義寫作順序。"
        log_tool_result("check_writing_order", result, success=True)
        return result

    # Check existing drafts
    existing_lower = _existing_draft_titles(drafts_dir)

    output = f"## 📋 寫作進度 — {current_info.get('name', paper_type)}\n\n"
    output += f"**Paper Type**: {paper_type}\n"
    output += f"**建議順序**: {_format_writing_order(paper_type)}\n\n"

    sorted_sections = sorted(order_map.items(), key=lambda x: x[1]["order"])
    output += _progress_table(sorted_sections, existing_lower)
    output += _next_section_hint(sorted_sections, existing_lower)

    log_tool_result("check_writing_order", f"showed progress for {paper_type}", success=True)
    return output


def _concept_pmids(concept_content: str) -> list[str]:
    # Find all wikilinks in concept
    wikilinks = re.findall(r"\[\[([^\]]+)\]\]", concept_content)
    pmids = []
    for wl in wikilinks:
        if "_" in wl:
            pmid = wl.split("_")[-1]
            if pmid.isdigit():
                pmids.append(pmid)
        elif wl.isdigit():
            pmids.append(wl)
    return pmids


def _reference_entry(meta: dict, pmid: str) -> str:
    title = meta.get("title", "Unknown Title")
    abstract = meta.get("abstract", "No abstract available.")
    # Extract key numbers/findings if possible (simple heuristic)
    findings = re.findall(r"\d+\.?\d*\s*%", abstract)
    findings_str = f" (Key figures: {', '.join(findings)})" if findings else ""

    entry = f"#### [[{meta.get('citation_key', pmid)}]]\n"
    entry += f"**Title**: {title}\n"
    entry += f"**Abstract Summary**: {abstract[:500]}...\n"
    entry += f"**Evidence**: {findings_str}\n\n"
    return entry


def _gather_reference_context(drafter: Drafter) -> str:
    ref_context = ""
    concept_path = get_concept_path()
    if concept_path and os.path.exists(concept_path):
        with open(concept_path, "r", encoding="utf-8") as f:
            concept_content = f.read()

        pmids = _concept_pmids(concept_content)

        if pmids:
            ref_context = "\n### 📚 Key Evidence from References\n\n"
            for pmid in list(set(pmids))[:5]:  # Limit to top 5 for context window
                meta = drafter.ref_manager.get_metadata(pmid)
                if meta:
                    ref_context += _reference_entry(meta, pmid)
    return ref_context


def _drafting_instructions(
    topic: str,
    notes: str,
    prereq_warning: str,
    strategy: Any,
    author_block: str,
    protected: dict,
    ref_context: str,
) -> str:
    output = f"## 📝 Drafting Instructions for {topic}\n\n"

    if prereq_warning:
        output += f"{prereq_warning}\n\n---\n\n"

    output += f"### 🎯 Writing Strategy\n{strategy}\n\n"

    if author_block:
        output += f"### 👥 Author Information (from project.json)\n\n{author_block}\n\n"
        output += "💡 Include this author block in the title page draft.\n\n"

    if protected.get("novelty_statement"):
        output += (
            f"### 🔒 NOVELTY STATEMENT (MUST PRESERVE)\n> {protected['novelty_statement']}\n\n"
        )

    if protected.get("selling_points"):
        output += f"### 🔒 KEY SELLING POINTS (MUST EMPHASIZE)\n{protected['selling_points']}\n\n"

    output += f"### 📝 User Notes/Outline\n{notes}\n\n"
    output += ref_context

    output += "\n---\n"
    output += "💡 **Agent Action**: Use the evidence above to write a solid, data-driven section. "
    output += (
        "Avoid generic AI filler. Focus on the logical flow from existing evidence to your novelty."
    )
    return output


def _draft_section(
    drafter: Drafter,
    topic: str,
    notes: str,
    project: Optional[str],
    skip_validation: bool,
) -> str:
    log_tool_call(
        "draft_section",
        {
            "topic": topic,
            "notes_len": len(notes),
            "project": project,
            "skip_validation": skip_validation,
        },
    )

    guard_error = _guard_writing_tool("draft_section", project)
    if guard_error is not None:
        return guard_error

    # 1. Enforce Concept Validation + 1.1 Reference Sufficiency (A7 hard gate)
    gate_error, protected = _section_gate_error(skip_validation)
    if gate_error is not None:
        return gate_error

    # 1.5 Check Writing Order Prerequisites (advisory)
    prereq_warning = _check_section_prerequisites(topic)

    # 2. Gather Reference Context
    ref_context = _gather_reference_context(drafter)

    # 3. Get Writing Strategy
    strategy = SECTION_PROMPTS.get(topic.lower(), "Write a professional medical section.")

    # 3.5 Get Author Block for Title Page
    author_block = ""
    if topic.lower() in ("title page", "title", "titlepage"):
        author_block = _get_author_block()

    # 4. Construct Final Instructions for the Agent
    output = _drafting_instructions(
        topic, notes, prereq_warning, strategy, author_block, protected, ref_context
    )

    log_tool_result("draft_section", f"prepared context for {topic}", success=True)
    return output
