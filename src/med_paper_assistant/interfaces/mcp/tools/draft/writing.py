"""
Draft Writing Tools

write_draft, draft_section, read_draft, list_drafts
"""

import os
import re
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.domain.paper_types import check_writing_prerequisites
from med_paper_assistant.domain.services.wikilink_validator import validate_wikilinks_in_content
from med_paper_assistant.infrastructure.persistence.writing_hooks._constants import (
    DEFAULT_MIN_REFERENCES,
    DEFAULT_MINIMUM_REFERENCES,
)
from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.concept_validator import ConceptValidator
from med_paper_assistant.infrastructure.services.prompts import SECTION_PROMPTS

from .._shared import (
    auto_checkpoint_writing,
    get_concept_path,
    get_drafts_dir,
    get_optional_tool_decorator,
    get_project_path,
    log_agent_misuse,
    log_tool_call,
    log_tool_error,
    log_tool_result,
    resolve_project_context,
    validate_project_for_tool,
)

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


def _enforce_reference_sufficiency() -> tuple[bool, str]:
    """
    Hard gate: Block writing when saved references are below paper-type minimum.

    Cross-MCP enforcement: mdpaper cannot invoke pubmed-search directly,
    so this returns structured REMEDIATION_REQUIRED directives with exact
    tool calls the agent MUST execute before retrying.

    Returns:
        Tuple of (can_proceed: bool, message: str).
        When can_proceed is False, message contains blocking error + remediation steps.
        When can_proceed is True, message is empty or informational.
    """
    from med_paper_assistant.infrastructure.persistence import get_project_manager

    pm = get_project_manager()
    current_info = pm.get_project_info()
    if not current_info or not current_info.get("project_path"):
        # No project context — let other validators handle this
        return True, ""

    project_dir = Path(str(current_info["project_path"]))
    refs_dir = project_dir / "references"

    # Count references (same logic as A7 hook and pipeline gate)
    ref_count = 0
    if refs_dir.is_dir():
        ref_count = len(list(refs_dir.glob("*/metadata.json")))
        if ref_count == 0:
            ref_count = len(list(refs_dir.glob("*.md")))

    # Determine paper type and minimum
    paper_type = current_info.get("paper_type", "original-research")

    # Check journal-profile.yaml override first
    min_refs = None
    jp_path = project_dir / "journal-profile.yaml"
    if jp_path.is_file():
        try:
            import yaml

            with open(jp_path, encoding="utf-8") as f:
                profile = yaml.safe_load(f) or {}
            paper_type_from_profile = profile.get("paper", {}).get("type")
            if paper_type_from_profile:
                paper_type = paper_type_from_profile
            min_limits = profile.get("references", {}).get("minimum_reference_limits", {})
            if isinstance(min_limits, dict):
                val = min_limits.get(paper_type)
                if val is not None:
                    min_refs = int(val)
        except Exception:  # nosec B110 - fallback to defaults below
            pass

    if min_refs is None:
        min_refs = DEFAULT_MINIMUM_REFERENCES.get(paper_type, DEFAULT_MIN_REFERENCES)

    if ref_count >= min_refs:
        return True, ""

    deficit = min_refs - ref_count
    project_name = current_info.get("name", "")

    # Extract research topic from concept.md for search query suggestion
    topic_hint = ""
    concept_path = get_concept_path()
    if concept_path and os.path.exists(concept_path):
        try:
            with open(concept_path, "r", encoding="utf-8") as f:
                concept_text = f.read(2000)  # Read first 2000 chars for topic extraction
            # Look for title or first heading
            title_match = re.search(r"^#\s+(.+)$", concept_text, re.MULTILINE)
            if title_match:
                topic_hint = title_match.group(1).strip()
        except Exception:  # nosec B110 - topic hint is optional
            pass

    search_query_example = topic_hint if topic_hint else project_name

    return (
        False,
        f"❌ **WRITING BLOCKED — Insufficient References (Hook A7)**\n\n"
        f"📊 Current: **{ref_count}/{min_refs}** references "
        f"(paper type: {paper_type}, need **{deficit}** more)\n\n"
        f"---\n\n"
        f"## 🔧 REMEDIATION REQUIRED\n\n"
        f"Complete these steps before retrying `write_draft` or `draft_section`:\n\n"
        f"### Step 1: Search for more literature\n"
        f"```\n"
        f'unified_search(query="{search_query_example}", limit=20)\n'
        f"```\n\n"
        f"### Step 2: Save at least {deficit} references\n"
        f"```\n"
        f'save_reference_mcp(pmid="<PMID from search results>")\n'
        f"```\n"
        f"Repeat for each relevant article until you have ≥{min_refs} references.\n\n"
        f"### Step 3: Retry writing\n"
        f"Call `write_draft` or `draft_section` again after saving enough references.\n\n"
        f"---\n"
        f"⚠️ This is a **Code-Enforced** hard gate. Writing cannot proceed "
        f"until reference count ≥ {min_refs}.",
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


def _run_embedded_post_write_hooks(content: str, section_name: str = "manuscript") -> str:
    """
    Run post-write hooks automatically after write_draft/patch_draft.

    Non-blocking: returns a report string (never raises). Agent cannot skip
    this because it's embedded in the write path, not a separate tool call.

    Returns:
        Formatted report string, or empty string if no issues or on error.
    """
    project_path = get_project_path()
    if not project_path:
        return ""

    try:
        from med_paper_assistant.infrastructure.persistence.writing_hooks import (
            WritingHooksEngine,
        )

        engine = WritingHooksEngine(project_path)
        results = engine.run_post_write_hooks(content, section=section_name)

        criticals: list[str] = []
        warnings: list[str] = []

        for hook_id, hook_result in results.items():
            for issue in hook_result.issues:
                line = f"[{hook_id}] {issue.message}"
                if issue.severity == "CRITICAL":
                    criticals.append(f"❌ {line}")
                elif issue.severity == "WARNING":
                    warnings.append(f"⚠️  {line}")

        if not criticals and not warnings:
            return "\n\n✅ **Post-write hooks**: All checks passed."

        parts = ["\n\n📋 **Post-write hooks (auto-run)**:"]
        if criticals:
            parts.append(f"\n**CRITICAL ({len(criticals)}):**")
            parts.extend(f"\n- {c}" for c in criticals)
        if warnings:
            parts.append(f"\n**Warnings ({len(warnings)}):**")
            parts.extend(f"\n- {w}" for w in warnings[:10])  # Cap at 10 to avoid token bloat
            if len(warnings) > 10:
                parts.append(f"\n- ... and {len(warnings) - 10} more")

        return "".join(parts)
    except Exception:
        return ""  # Silently fail — don't block writing due to hook errors


def register_writing_tools(
    mcp: FastMCP,
    drafter: Drafter,
    *,
    register_public_verbs: bool = True,
):
    """Register draft writing tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    @tool()
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

        _, workflow_error = resolve_project_context(
            project,
            required_mode="manuscript",
        )
        if workflow_error:
            log_agent_misuse(
                "check_writing_order",
                "manuscript workflow required",
                {"project": project},
                workflow_error,
            )
            return workflow_error

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

    @tool()
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

        _, workflow_error = resolve_project_context(
            project,
            required_mode="manuscript",
        )
        if workflow_error:
            log_agent_misuse(
                "draft_section",
                "manuscript workflow required",
                {"project": project},
                workflow_error,
            )
            return workflow_error

        # 1. Enforce Concept Validation
        if not skip_validation:
            can_proceed, message, protected = _enforce_concept_validation()
            if not can_proceed:
                log_tool_result("draft_section", "concept validation failed", success=False)
                return message
        else:
            protected = {}

        # 1.1 Enforce Reference Sufficiency (A7 hard gate)
        if not skip_validation:
            refs_ok, refs_msg = _enforce_reference_sufficiency()
            if not refs_ok:
                log_tool_result("draft_section", "reference sufficiency failed", success=False)
                return refs_msg

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

    @tool()
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

        _, workflow_error = resolve_project_context(
            project,
            required_mode="manuscript",
        )
        if workflow_error:
            log_agent_misuse(
                "write_draft",
                "manuscript workflow required",
                {"project": project},
                workflow_error,
            )
            return workflow_error

        is_concept_file = "concept" in filename.lower()

        if not skip_validation and not is_concept_file:
            can_proceed, message, protected = _enforce_concept_validation()
            if not can_proceed:
                log_tool_result("write_draft", "concept validation failed", success=False)
                return message

        # Enforce Reference Sufficiency (A7 hard gate)
        if not skip_validation and not is_concept_file:
            refs_ok, refs_msg = _enforce_reference_sufficiency()
            if not refs_ok:
                log_tool_result("write_draft", "reference sufficiency failed", success=False)
                return refs_msg

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

            # Auto-checkpoint writing session for compaction recovery
            auto_checkpoint_writing(filename, fixed_content, "write")

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

            # 🔒 Embedded post-write hooks (auto-run, agent cannot skip)
            if not is_concept_file:
                section_for_hooks = (
                    os.path.splitext(os.path.basename(filename))[0]
                    .replace("_", " ")
                    .replace("-", " ")
                    .title()
                )
                hook_report = _run_embedded_post_write_hooks(fixed_content, section_for_hooks)
                result += hook_report

            log_tool_result("write_draft", result, success=True)
            return result
        except Exception as e:
            log_tool_error("write_draft", e, {"filename": filename, "content_len": len(content)})
            return f"Error creating draft: {str(e)}"

    @tool()
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

        _, workflow_error = resolve_project_context(
            project,
            required_mode="manuscript",
        )
        if workflow_error:
            log_agent_misuse(
                "list_drafts",
                "manuscript workflow required",
                {"project": project},
                workflow_error,
            )
            return workflow_error

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

    @tool()
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

        _, workflow_error = resolve_project_context(
            project,
            required_mode="manuscript",
        )
        if workflow_error:
            log_agent_misuse(
                "read_draft",
                "manuscript workflow required",
                {"project": project},
                workflow_error,
            )
            return workflow_error

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

    @tool()
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

        _, workflow_error = resolve_project_context(
            project,
            required_mode="manuscript",
        )
        if workflow_error:
            log_agent_misuse(
                "delete_draft",
                "manuscript workflow required",
                {"project": project},
                workflow_error,
            )
            return workflow_error

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

    return {
        "check_writing_order": check_writing_order,
        "draft_section": draft_section,
        "write_draft": write_draft,
        "list_drafts": list_drafts,
        "read_draft": read_draft,
        "delete_draft": delete_draft,
    }
