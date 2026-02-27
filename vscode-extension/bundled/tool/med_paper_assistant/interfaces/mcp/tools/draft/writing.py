"""
Draft Writing Tools

write_draft, draft_section, read_draft, list_drafts
"""

import os
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.domain.paper_types import check_writing_prerequisites
from med_paper_assistant.domain.services.wikilink_validator import validate_wikilinks_in_content
from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.concept_validator import ConceptValidator
from med_paper_assistant.infrastructure.services.prompts import SECTION_PROMPTS

from .._shared import (
    get_concept_path,
    get_drafts_dir,
    log_agent_misuse,
    log_tool_call,
    log_tool_error,
    log_tool_result,
    validate_project_for_tool,
)
from .._shared.guidance import build_guidance_hint

# Global validator instance
_concept_validator = ConceptValidator()


def _enforce_concept_validation(require_novelty: bool = True) -> tuple:
    """
    Check concept validation status (advisory, not blocking).

    Returns:
        Tuple of (can_proceed: bool, message: str, protected_content: dict)

    Note: Novelty score is advisory. Low score returns warning, not block.
    """
    concept_path = get_concept_path()

    if not concept_path or not os.path.exists(concept_path):
        return (
            False,
            "❌ **VALIDATION REQUIRED**\n\n"
            "No concept.md found for current project.\n"
            "You must create and validate a concept file first:\n\n"
            "1. Use `/mdpaper.concept` to develop your research concept\n"
            "2. Fill in 🔒 NOVELTY STATEMENT\n"
            "3. Fill in 🔒 KEY SELLING POINTS (at least 3)\n"
            "4. Run `validate_concept` to verify\n\n"
            "Draft writing is blocked until concept.md exists.",
            {},
        )

    result = _concept_validator.validate(
        concept_path,
        run_novelty_check=require_novelty,
        run_consistency_check=True,
        force_refresh=False,
    )

    # Extract protected content regardless of score
    novelty_section = result.sections.get("novelty_statement")
    selling_section = result.sections.get("selling_points")

    protected_content = {
        "novelty_statement": novelty_section.content if novelty_section else "",
        "selling_points": selling_section.content if selling_section else "",
        "novelty_score": result.novelty_average,
    }

    # Check structural requirements (these ARE blocking)
    if not novelty_section or not novelty_section.has_content:
        return (
            False,
            "❌ **MISSING REQUIRED SECTION**\n\n"
            "🔒 NOVELTY STATEMENT is empty.\n"
            "Please fill in your research novelty before writing drafts.",
            {},
        )

    if not selling_section or not selling_section.has_content:
        return (
            False,
            "❌ **MISSING REQUIRED SECTION**\n\n"
            "🔒 KEY SELLING POINTS is empty.\n"
            "Please add at least 3 key selling points before writing drafts.",
            {},
        )

    # Novelty score is ADVISORY, not blocking
    if result.novelty_average < 75:
        return (
            True,  # Allow proceeding!
            f"💡 Novelty score: {result.novelty_average:.1f}/100 (reference: 75)\n"
            f"這是參考指標，您可以選擇直接寫或補充後再寫。",
            protected_content,
        )

    return (
        True,
        f"✅ Concept validation passed (Novelty score: {result.novelty_average:.1f}/100)",
        protected_content,
    )


def _validate_wikilinks_in_content(content: str, references_dir: Optional[str] = None) -> tuple:
    """
    驗證內容中的 wikilinks 並自動修復。

    Returns:
        Tuple of (fixed_content: str, report: str or None)
    """
    result, fixed_content = validate_wikilinks_in_content(
        content, references_dir=references_dir, auto_fix=True
    )

    report = None
    if result.auto_fixed > 0:
        report = f"🔧 自動修復 {result.auto_fixed} 個 wikilink 格式錯誤"
    elif result.issues:
        report = result.to_report()

    return fixed_content, report


def _check_section_prerequisites(section_name: str) -> str:
    """
    Check writing order prerequisites for a section (advisory).

    Returns warning message if prerequisites are missing, empty string otherwise.
    """
    from med_paper_assistant.infrastructure.persistence import get_project_manager

    pm = get_project_manager()
    current_info = pm.get_project_info()
    if not current_info or not current_info.get("project_path"):
        return ""

    project_path = str(current_info["project_path"])
    paper_type = current_info.get("paper_type", "other")
    drafts_dir = os.path.join(project_path, "drafts")

    result = check_writing_prerequisites(paper_type, section_name, drafts_dir)
    return result.get("warning", "")


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


def register_writing_tools(mcp: FastMCP, drafter: Drafter):
    """Register draft writing tools."""

    @mcp.tool()
    def check_writing_order(project: Optional[str] = None) -> str:
        """
        Check the recommended writing order and current progress for the active project.

        Shows which sections have been written and which prerequisites remain.
        Advisory only — CONSTITUTION §22 allows reordering phases.

        Args:
            project: Project slug (uses current if omitted)
        """
        log_tool_call("check_writing_order", {"project": project})

        is_valid, error_msg = validate_project_for_tool(project)
        if not is_valid:
            return error_msg

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
        existing_drafts = []
        if os.path.isdir(drafts_dir):
            existing_drafts = [
                f.replace(".md", "").replace("_", " ").replace("-", " ").title()
                for f in os.listdir(drafts_dir)
                if f.endswith(".md") and f != "concept.md"
            ]
        existing_lower = [s.lower() for s in existing_drafts]

        output = f"## 📋 寫作進度 — {current_info.get('name', paper_type)}\n\n"
        output += f"**Paper Type**: {paper_type}\n"
        output += f"**建議順序**: {_format_writing_order(paper_type)}\n\n"
        output += "| # | Section | 狀態 | 前置條件 |\n"
        output += "|---|---------|------|----------|\n"

        sorted_sections = sorted(order_map.items(), key=lambda x: x[1]["order"])
        for section_name, info in sorted_sections:
            order = info["order"]
            prereqs = info.get("prerequisites", [])

            # Check if this section exists
            section_exists = any(
                section_name.lower() in ex or ex in section_name.lower() for ex in existing_lower
            )
            status = "✅ 已完成" if section_exists else "⬜ 未開始"

            # Check prerequisites
            prereq_status = []
            for p in prereqs:
                p_exists = any(p.lower() in ex or ex in p.lower() for ex in existing_lower)
                prereq_status.append(f"{'✅' if p_exists else '❌'} {p}")

            prereq_str = ", ".join(prereq_status) if prereq_status else "（無）"
            output += f"| {order} | {section_name} | {status} | {prereq_str} |\n"

        # Suggest next section
        for section_name, info in sorted_sections:
            section_exists = any(
                section_name.lower() in ex or ex in section_name.lower() for ex in existing_lower
            )
            if not section_exists:
                prereqs = info.get("prerequisites", [])
                all_met = all(
                    any(p.lower() in ex or ex in p.lower() for ex in existing_lower)
                    for p in prereqs
                )
                if all_met:
                    output += f"\n💡 **建議下一步**: 撰寫 **{section_name}**"
                    break

        log_tool_result("check_writing_order", f"showed progress for {paper_type}", success=True)
        return output

    @mcp.tool()
    def draft_section(
        topic: str, notes: str, project: Optional[str] = None, skip_validation: bool = False
    ) -> str:
        """
        Draft a paper section using concept.md and saved references as context.

        Args:
            topic: Section name (e.g., "Introduction")
            notes: Raw notes/bullet points to convert
            project: Project slug (uses current if omitted)
            skip_validation: Internal use only
        """
        log_tool_call(
            "draft_section",
            {
                "topic": topic,
                "notes_len": len(notes),
                "project": project,
                "skip_validation": skip_validation,
            },
        )

        is_valid, error_msg = validate_project_for_tool(project)
        if not is_valid:
            log_agent_misuse(
                "draft_section", "valid project context required", {"project": project}, error_msg
            )
            return error_msg

        # 1. Enforce Concept Validation
        if not skip_validation:
            can_proceed, message, protected = _enforce_concept_validation()
            if not can_proceed:
                log_tool_result("draft_section", "concept validation failed", success=False)
                return message
        else:
            protected = {}

        # 1.5 Check Writing Order Prerequisites (advisory)
        prereq_warning = _check_section_prerequisites(topic)

        # 2. Gather Reference Context
        ref_context = ""
        concept_path = get_concept_path()
        if concept_path and os.path.exists(concept_path):
            with open(concept_path, "r", encoding="utf-8") as f:
                concept_content = f.read()

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

            if pmids:
                ref_context = "\n### 📚 Key Evidence from References\n\n"
                for pmid in list(set(pmids))[:5]:  # Limit to top 5 for context window
                    meta = drafter.ref_manager.get_metadata(pmid)
                    if meta:
                        title = meta.get("title", "Unknown Title")
                        abstract = meta.get("abstract", "No abstract available.")
                        # Extract key numbers/findings if possible (simple heuristic)
                        findings = re.findall(r"\d+\.?\d*\s*%", abstract)
                        findings_str = f" (Key figures: {', '.join(findings)})" if findings else ""

                        ref_context += f"#### [[{meta.get('citation_key', pmid)}]]\n"
                        ref_context += f"**Title**: {title}\n"
                        ref_context += f"**Abstract Summary**: {abstract[:500]}...\n"
                        ref_context += f"**Evidence**: {findings_str}\n\n"

        # 3. Get Writing Strategy
        strategy = SECTION_PROMPTS.get(topic.lower(), "Write a professional medical section.")

        # 3.5 Get Author Block for Title Page
        author_block = ""
        if topic.lower() in ("title page", "title", "titlepage"):
            author_block = _get_author_block()

        # 4. Construct Final Instructions for the Agent
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
            output += (
                f"### 🔒 KEY SELLING POINTS (MUST EMPHASIZE)\n{protected['selling_points']}\n\n"
            )

        output += f"### 📝 User Notes/Outline\n{notes}\n\n"
        output += ref_context

        output += "\n---\n"
        output += (
            "💡 **Agent Action**: Use the evidence above to write a solid, data-driven section. "
        )
        output += "Avoid generic AI filler. Focus on the logical flow from existing evidence to your novelty."

        log_tool_result("draft_section", f"prepared context for {topic}", success=True)
        return output

    @mcp.tool()
    def write_draft(
        filename: str, content: str, project: Optional[str] = None, skip_validation: bool = False
    ) -> str:
        """
        Create/update a draft file with auto citation formatting.
        Use (PMID:123456) or [PMID:123456] for citations.

        Args:
            filename: Draft filename (e.g., "draft.md")
            content: Text content with citation placeholders
            project: Project slug (uses current if omitted)
            skip_validation: Internal use only
        """
        log_tool_call(
            "write_draft",
            {
                "filename": filename,
                "content_len": len(content),
                "project": project,
                "skip_validation": skip_validation,
            },
        )

        is_valid, error_msg = validate_project_for_tool(project)
        if not is_valid:
            log_agent_misuse(
                "write_draft", "valid project context required", {"project": project}, error_msg
            )
            return error_msg

        is_concept_file = "concept" in filename.lower()

        if not skip_validation and not is_concept_file:
            can_proceed, message, protected = _enforce_concept_validation()
            if not can_proceed:
                log_tool_result("write_draft", "concept validation failed", success=False)
                return message

        # Check writing order prerequisites (advisory, non-blocking)
        prereq_warning = ""
        if not is_concept_file:
            section_name = (
                os.path.splitext(os.path.basename(filename))[0]
                .replace("_", " ")
                .replace("-", " ")
                .title()
            )
            prereq_warning = _check_section_prerequisites(section_name)

        # 🔧 Pre-check: 驗證並修復 wikilink 格式
        references_dir = None
        from med_paper_assistant.infrastructure.persistence import get_project_manager

        pm = get_project_manager()
        current_info = pm.get_project_info()
        if current_info and current_info.get("project_path"):
            references_dir = os.path.join(str(current_info["project_path"]), "references")

        fixed_content, wikilink_report = _validate_wikilinks_in_content(content, references_dir)

        try:
            path = drafter.create_draft(filename, fixed_content)

            reminder = ""
            if not is_concept_file:
                reminder = (
                    "\n\n📝 **Protected Content Reminder:**\n"
                    "- 🔒 NOVELTY STATEMENT must be reflected in Introduction\n"
                    "- 🔒 KEY SELLING POINTS must be emphasized in Discussion\n"
                    "- Ask user before modifying any protected content"
                )

            # 附加 wikilink 修復報告
            if wikilink_report:
                reminder += f"\n\n{wikilink_report}"

            # 附加寫作順序建議
            if prereq_warning:
                reminder += f"\n\n{prereq_warning}"

            result = f"Draft created successfully at: {path}{reminder}"
            result = build_guidance_hint(result, next_tool="run_writing_hooks")
            log_tool_result("write_draft", result, success=True)
            return result
        except Exception as e:
            log_tool_error("write_draft", e, {"filename": filename, "content_len": len(content)})
            return f"Error creating draft: {str(e)}"

    @mcp.tool()
    def list_drafts(project: Optional[str] = None) -> str:
        """
        List all draft files in drafts/ with section and word counts.

        Args:
            project: Project slug (uses current if omitted)
        """
        log_tool_call("list_drafts", {"project": project})

        if project:
            is_valid, error_msg = validate_project_for_tool(project)
            if not is_valid:
                log_agent_misuse(
                    "list_drafts", "valid project context required", {"project": project}, error_msg
                )
                return error_msg

        drafts_dir = get_drafts_dir()
        if not drafts_dir:
            drafts_dir = "drafts"
        if not os.path.exists(drafts_dir):
            result = "📁 No drafts/ directory found. Create drafts using write_draft tool first."
            log_tool_result("list_drafts", result, success=True)
            return result

        drafts = [f for f in os.listdir(drafts_dir) if f.endswith(".md")]

        if not drafts:
            result = "📁 No draft files found in drafts/ directory."
            log_tool_result("list_drafts", result, success=True)
            return result

        output = "📄 **Available Drafts**\n\n"
        output += "| # | Filename | Sections | Total Words |\n"
        output += "|---|----------|----------|-------------|\n"

        for i, draft_file in enumerate(sorted(drafts), 1):
            draft_path = os.path.join(drafts_dir, draft_file)
            try:
                with open(draft_path, "r", encoding="utf-8") as f:
                    content = f.read()

                sections = len(re.findall(r"^#+\s+", content, re.MULTILINE))
                words = len([w for w in content.split() if w.strip()])

                output += f"| {i} | {draft_file} | {sections} | {words} |\n"
            except Exception:
                output += f"| {i} | {draft_file} | Error | - |\n"

        log_tool_result("list_drafts", f"found {len(drafts)} drafts", success=True)
        return output

    @mcp.tool()
    def read_draft(filename: str, project: Optional[str] = None) -> str:
        """
        Read a draft file's structure and content by sections.

        Args:
            filename: Draft filename (in drafts/ directory)
            project: Project slug (uses current if omitted)
        """
        log_tool_call("read_draft", {"filename": filename, "project": project})

        if project:
            is_valid, error_msg = validate_project_for_tool(project)
            if not is_valid:
                log_agent_misuse(
                    "read_draft", "valid project context required", {"project": project}, error_msg
                )
                return error_msg

        if not os.path.isabs(filename):
            drafts_dir = get_drafts_dir() or "drafts"
            filename = os.path.join(drafts_dir, filename)

        if not os.path.exists(filename):
            result = f"Error: Draft file not found: {filename}"
            log_tool_result("read_draft", result, success=False)
            return result

        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()

            sections: dict[str, str] = {}
            current_section: Optional[str] = None
            current_content: list[str] = []

            for line in content.split("\n"):
                if line.startswith("#"):
                    if current_section and current_content:
                        sections[current_section] = "\n".join(current_content)
                    section_name = re.sub(r"^#+\s*\d*\.?\s*", "", line).strip()
                    current_section = section_name if section_name else "Untitled"
                    current_content = []
                elif current_section:
                    current_content.append(line)

            if current_section and current_content:
                sections[current_section] = "\n".join(current_content)

            output = f"📝 **Draft: {os.path.basename(filename)}**\n\n"
            output += "| Section | Word Count | Preview |\n"
            output += "|---------|------------|----------|\n"

            for sec_name, sec_content in sections.items():
                words = len([w for w in sec_content.split() if w.strip()])
                preview = sec_content[:50].replace("\n", " ").strip() + "..."
                output += f"| {sec_name} | {words} | {preview} |\n"

            output += "\n---\n\n"
            output += "**Full Content by Section:**\n\n"

            for sec_name, sec_content in sections.items():
                output += f"### {sec_name}\n\n"
                output += sec_content.strip()[:500]
                if len(sec_content) > 500:
                    output += f"\n\n*... ({len(sec_content)} characters total)*"
                output += "\n\n"

            log_tool_result(
                "read_draft", f"read {len(sections)} sections from {filename}", success=True
            )
            return output
        except Exception as e:
            log_tool_error("read_draft", e, {"filename": filename})
            return f"Error reading draft: {str(e)}"

    @mcp.tool()
    def delete_draft(filename: str, confirm: bool = False, project: Optional[str] = None) -> str:
        """
        ⚠️ DESTRUCTIVE: Delete a draft file permanently.

        Args:
            filename: Draft filename (e.g., "draft.md")
            confirm: False=preview, True=actually delete
            project: Project slug (uses current if omitted)
        """
        log_tool_call(
            "delete_draft", {"filename": filename, "confirm": confirm, "project": project}
        )

        if project:
            is_valid, error_msg = validate_project_for_tool(project)
            if not is_valid:
                log_agent_misuse(
                    "delete_draft",
                    "valid project context required",
                    {"project": project},
                    error_msg,
                )
                return error_msg

        # Resolve the full path
        if not os.path.isabs(filename):
            drafts_dir = get_drafts_dir() or "drafts"
            filename = os.path.join(drafts_dir, filename)

        if not os.path.exists(filename):
            error_msg = f"❌ Draft file not found: {filename}"
            log_tool_result("delete_draft", error_msg, success=False)
            return error_msg

        # Get file info
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            word_count = len([w for w in content.split() if w.strip()])
            sections = len(re.findall(r"^#+\s+", content, re.MULTILINE))
            file_size = os.path.getsize(filename)
        except Exception as e:
            error_msg = f"❌ Error reading draft: {str(e)}"
            log_tool_error("delete_draft", e, {"filename": filename})
            return error_msg

        basename = os.path.basename(filename)

        if not confirm:
            # Preview mode
            output = "⚠️ **即將刪除草稿 (Preview)**\n\n"
            output += f"**檔案名稱**: {basename}\n"
            output += f"**路徑**: {filename}\n"
            output += f"**字數**: {word_count} words\n"
            output += f"**章節數**: {sections} sections\n"
            output += f"**檔案大小**: {file_size:,} bytes\n"
            output += "\n⚠️ 此操作無法復原！\n"
            output += f'請使用 `delete_draft(filename="{basename}", confirm=True)` 確認刪除。'
            log_tool_result("delete_draft", "preview shown", success=True)
            return output

        # Actually delete
        try:
            os.remove(filename)
            result = "✅ **已刪除草稿**\n\n"
            result += f"**檔案名稱**: {basename}\n"
            result += f"**已刪除字數**: {word_count} words\n"
            result += f"**已刪除章節數**: {sections} sections\n"
            log_tool_result("delete_draft", f"deleted {basename}", success=True)
            return result
        except Exception as e:
            error_msg = f"❌ 刪除失敗: {str(e)}"
            log_tool_error("delete_draft", e, {"filename": filename})
            return error_msg
