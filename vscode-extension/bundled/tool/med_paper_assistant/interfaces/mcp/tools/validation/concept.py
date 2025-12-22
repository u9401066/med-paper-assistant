"""
Concept Validation Tools

validate_concept, validate_concept_quick, validate_wikilinks
"""

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.domain.services.wikilink_validator import (
    validate_wikilinks_in_file,
)
from med_paper_assistant.infrastructure.services.concept_validator import ConceptValidator

from .._shared import (
    ensure_project_context,
    get_project_list_for_prompt,
    log_agent_misuse,
    log_tool_call,
    log_tool_error,
    log_tool_result,
)

# Global validator instance
_concept_validator = ConceptValidator()


def _validate_project_context(project: Optional[str]) -> tuple:
    """Validate project context."""
    is_valid, msg, project_info = ensure_project_context(project)
    if not is_valid:
        return False, f"❌ {msg}\n\n{get_project_list_for_prompt()}"
    return True, None


def register_concept_validation_tools(mcp: FastMCP):
    """Register concept validation tools."""

    @mcp.tool()
    def validate_concept(
        filename: str,
        project: Optional[str] = None,
        run_novelty_check: bool = True,
        target_section: Optional[str] = None,
    ) -> str:
        """
        Validate a concept file before proceeding to draft writing.

        This tool performs comprehensive validation including:
        1. Structural validation - Required sections present
        2. Novelty evaluation - LLM-based scoring (3 rounds, 75+ threshold)
        3. Consistency check - Alignment between sections

        **Section-Specific Validation:**
        If `target_section` is specified, validation checks only the sections
        required for writing that specific section. For example:
        - Introduction: Needs NOVELTY + Background + Research Gap
        - Methods: Recommended to have Study Design but won't block

        Different paper types have different requirements:
        - original-research: Full IMRAD structure
        - systematic-review/meta-analysis: + PRISMA checklist
        - case-report: + Case timeline
        - letter: Minimal structure

        Args:
            filename: Path to the concept file (e.g., "concept.md").
            project: Project slug. Agent should confirm with user before calling.
            run_novelty_check: Whether to run LLM-based novelty scoring (default: True).
            target_section: Optional target section to validate for (e.g., "Introduction", "Methods").
                           If specified, uses section-specific validation rules.

        Returns:
            Validation report with checklist status, novelty scores, and suggestions.
        """
        log_tool_call(
            "validate_concept",
            {
                "filename": filename,
                "project": project,
                "run_novelty_check": run_novelty_check,
                "target_section": target_section,
            },
        )

        is_valid, error_msg = _validate_project_context(project)
        if not is_valid:
            log_agent_misuse(
                "validate_concept",
                "valid project context required",
                {"project": project},
                error_msg,
            )
            return error_msg

        # Resolve path
        if not os.path.isabs(filename):
            from med_paper_assistant.infrastructure.persistence import get_project_manager

            pm = get_project_manager()
            current_info = pm.get_project_info()  # Returns dict with project details

            if current_info.get("project_path"):
                project_concept = os.path.join(current_info["project_path"], "concept.md")
                if os.path.exists(project_concept) and filename in ["concept.md", project_concept]:
                    filename = project_concept
                else:
                    filename = os.path.join("drafts", filename)
            else:
                filename = os.path.join("drafts", filename)

        if not os.path.exists(filename):
            error_result = (
                f"❌ Error: Concept file not found: {filename}\n\n"
                f"Use `/mdpaper.concept` to create a concept file first."
            )
            log_tool_result("validate_concept", "concept file not found", success=False)
            return error_result

        try:
            # Get paper_type from project
            from med_paper_assistant.infrastructure.persistence import get_project_manager

            pm = get_project_manager()
            current_info = pm.get_project_info()  # Returns dict with project details
            paper_type = str(current_info.get("paper_type", "original-research")) if current_info else "original-research"

            # 1. Wikilink 格式驗證（自動修復）
            references_dir = None
            if current_info and current_info.get("project_path"):
                references_dir = os.path.join(str(current_info["project_path"]), "references")

            wikilink_result = validate_wikilinks_in_file(
                filename, references_dir=references_dir, auto_fix=True, save_if_fixed=True
            )

            # 2. Concept 結構與新穎性驗證
            validation_result = _concept_validator.validate(
                filename,
                paper_type=paper_type,
                target_section=target_section or "",
                run_novelty_check=run_novelty_check,
                run_consistency_check=True,
                run_citation_check=False,
                force_refresh=True,
            )

            report = _concept_validator.generate_report(validation_result)

            # 3. 附加 wikilink 驗證結果
            if wikilink_result.auto_fixed > 0:
                report += "\n\n---\n\n🔧 **Wikilink 自動修復**\n"
                report += f"已自動修復 {wikilink_result.auto_fixed} 個格式錯誤\n"
            elif wikilink_result.issues:
                report += f"\n\n---\n\n{wikilink_result.to_report()}"

            log_tool_result(
                "validate_concept",
                f"overall_passed={validation_result.overall_passed}, can_write_section={validation_result.can_write_section}, novelty_avg={validation_result.novelty_average}, wikilink_fixed={wikilink_result.auto_fixed}",
                success=validation_result.overall_passed or validation_result.can_write_section,
            )
            return report

        except Exception as e:
            log_tool_error("validate_concept", e, {"filename": filename})
            return f"❌ Error validating concept: {str(e)}"

    @mcp.tool()
    def validate_concept_quick(filename: str, project: Optional[str] = None) -> str:
        """
        Quick structural validation without LLM calls.

        Use this for fast checks when you just need to verify sections exist.
        For full validation with novelty scoring, use validate_concept.

        Args:
            filename: Path to the concept file.
            project: Project slug. If not specified, uses current project.

        Returns:
            Quick validation report (structure only).
        """
        log_tool_call("validate_concept_quick", {"filename": filename, "project": project})

        if project:
            is_valid, error_msg = _validate_project_context(project)
            if not is_valid:
                log_agent_misuse(
                    "validate_concept_quick",
                    "valid project context required",
                    {"project": project},
                    error_msg,
                )
                return error_msg

        if not os.path.isabs(filename):
            from med_paper_assistant.infrastructure.persistence import get_project_manager

            pm = get_project_manager()
            current_info = pm.get_project_info()

            if current_info and current_info.get("project_path"):
                project_concept = os.path.join(str(current_info["project_path"]), "concept.md")
                if os.path.exists(project_concept) and filename in ["concept.md", project_concept]:
                    filename = project_concept
                else:
                    filename = os.path.join("drafts", filename)
            else:
                filename = os.path.join("drafts", filename)

        if not os.path.exists(filename):
            error_result = f"❌ Error: Concept file not found: {filename}"
            log_tool_result("validate_concept_quick", "concept file not found", success=False)
            return error_result

        try:
            validation_result = _concept_validator.validate_structure_only(filename)
            report = _concept_validator.generate_report(validation_result)
            log_tool_result(
                "validate_concept_quick",
                f"passed={validation_result.overall_passed}",
                success=validation_result.overall_passed,
            )
            return report
        except Exception as e:
            log_tool_error("validate_concept_quick", e, {"filename": filename})
            return f"❌ Error: {str(e)}"

    @mcp.tool()
    def validate_for_section(section: str, project: Optional[str] = None) -> str:
        """
        Check if a specific section can be written based on concept.md.

        This is the RECOMMENDED way to validate before writing a draft section.
        It only checks requirements for the specific section, not the full concept.

        Section-specific requirements:
        - **Introduction**: NOVELTY + Background + Research Gap (Methods NOT required)
        - **Methods**: Study Design recommended but not blocking
        - **Results**: Basic structure only
        - **Discussion**: KEY SELLING POINTS required

        Different paper types have different rules:
        - original-research: Standard IMRAD
        - systematic-review: + PRISMA requirements
        - case-report: + Case timeline
        - letter: Minimal requirements

        Args:
            section: Target section to write (e.g., "Introduction", "Methods", "Discussion").
            project: Project slug. Agent should confirm with user before calling.

        Returns:
            - ✅ CAN WRITE: Proceed with draft writing
            - ❌ CANNOT WRITE: Missing required sections (with list of what's missing)
            - 💡 RECOMMENDATIONS: Optional sections to consider filling

        Example:
            validate_for_section(section="Introduction", project="my-project")
        """
        log_tool_call("validate_for_section", {"section": section, "project": project})

        is_valid, error_msg = _validate_project_context(project)
        if not is_valid:
            log_agent_misuse(
                "validate_for_section",
                "valid project context required",
                {"project": project},
                error_msg,
            )
            return error_msg

        # Resolve concept.md path
        from med_paper_assistant.infrastructure.persistence import get_project_manager

        pm = get_project_manager()
        current_info = pm.get_project_info()

        if not current_info or not current_info.get("project_path"):
            error_result = "❌ No active project. Use `switch_project` first."
            log_tool_result("validate_for_section", "no active project", success=False)
            return error_result

        filename = os.path.join(str(current_info["project_path"]), "concept.md")
        if not os.path.exists(filename):
            error_result = (
                f"❌ Concept file not found: {filename}\n\nUse `/mdpaper.concept` to create one."
            )
            log_tool_result("validate_for_section", "concept file not found", success=False)
            return error_result

        paper_type = str(current_info.get("paper_type", "original-research"))

        try:
            validation_result = _concept_validator.validate(
                filename,
                paper_type=paper_type,
                target_section=section,
                run_novelty_check=True,  # Still check NOVELTY score
                run_consistency_check=False,  # Skip for speed
                run_citation_check=False,
                force_refresh=False,  # Use cache if available
            )

            report = _concept_validator.generate_report(validation_result)

            log_tool_result(
                "validate_for_section",
                f"section={section}, can_write={validation_result.can_write_section}, paper_type={paper_type}",
                success=validation_result.can_write_section,
            )
            return report

        except Exception as e:
            log_tool_error("validate_for_section", e, {"section": section, "project": project})
            return f"❌ Error: {str(e)}"

    @mcp.tool()
    def validate_wikilinks(
        filename: str, project: Optional[str] = None, auto_fix: bool = True
    ) -> str:
        """
        Validate and optionally fix wikilink formats in a markdown file.

        Correct format: [[author2024_12345678]]

        Common issues detected and fixed:
        - [[12345678]] → Missing author_year prefix
        - Author 2024 [[12345678]] → Messy format
        - [[PMID:12345678]] → Old format

        Args:
            filename: The markdown file to check (e.g., "concept.md", "drafts/intro.md").
            project: Project slug. If not specified, uses current project.
            auto_fix: Whether to automatically fix issues (default: True).

        Returns:
            Validation report with issues found and fixes applied.
        """
        log_tool_call(
            "validate_wikilinks", {"filename": filename, "project": project, "auto_fix": auto_fix}
        )

        # Get project context
        references_dir = None
        if project:
            is_valid, error_msg = _validate_project_context(project)
            if not is_valid:
                log_agent_misuse(
                    "validate_wikilinks",
                    "valid project context required",
                    {"project": project},
                    error_msg,
                )
                return error_msg

        # Resolve path
        if not os.path.isabs(filename):
            from med_paper_assistant.infrastructure.persistence import get_project_manager

            pm = get_project_manager()
            current_info = pm.get_project_info()

            if current_info and current_info.get("project_path"):
                project_path = str(current_info["project_path"])
                # Try project root first
                project_file = os.path.join(project_path, filename)
                if os.path.exists(project_file):
                    filename = project_file
                else:
                    # Try drafts folder
                    drafts_file = os.path.join(project_path, "drafts", filename)
                    if os.path.exists(drafts_file):
                        filename = drafts_file

                references_dir = os.path.join(project_path, "references")

        if not os.path.exists(filename):
            error_result = f"❌ File not found: {filename}"
            log_tool_result("validate_wikilinks", "file not found", success=False)
            return error_result

        try:
            wikilink_result = validate_wikilinks_in_file(
                filename, references_dir=references_dir, auto_fix=auto_fix, save_if_fixed=True
            )

            report = wikilink_result.to_report()

            if wikilink_result.auto_fixed > 0:
                report += f"\n\n✅ 檔案已更新: `{filename}`"

            log_tool_result(
                "validate_wikilinks",
                f"valid={wikilink_result.is_valid}, fixed={wikilink_result.auto_fixed}",
                success=wikilink_result.is_valid,
            )
            return report

        except Exception as e:
            log_tool_error("validate_wikilinks", e, {"filename": filename})
            return f"❌ Error: {str(e)}"
