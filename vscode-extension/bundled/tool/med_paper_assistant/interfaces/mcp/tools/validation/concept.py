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
        structure_only: bool = False,
    ) -> str:
        """
        Comprehensive validation: structure, novelty scoring (3 rounds, 75+ threshold), and consistency.

        Args:
            filename: Concept file path (e.g., "concept.md")
            project: Project slug (uses current if omitted)
            run_novelty_check: Run LLM-based novelty scoring (default: True)
            target_section: Optional section to validate for (e.g., "Introduction")
            structure_only: Quick structural check without LLM calls (default: False)
        """
        log_tool_call(
            "validate_concept",
            {
                "filename": filename,
                "project": project,
                "run_novelty_check": run_novelty_check,
                "target_section": target_section,
                "structure_only": structure_only,
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
            # Quick structural check only (no LLM calls)
            if structure_only:
                validation_result = _concept_validator.validate_structure_only(filename)
                report = _concept_validator.generate_report(validation_result)
                log_tool_result(
                    "validate_concept",
                    f"structure_only passed={validation_result.overall_passed}",
                    success=validation_result.overall_passed,
                )
                return report

            # Get paper_type from project
            from med_paper_assistant.infrastructure.persistence import get_project_manager

            pm = get_project_manager()
            current_info = pm.get_project_info()  # Returns dict with project details
            paper_type = (
                str(current_info.get("paper_type", "original-research"))
                if current_info
                else "original-research"
            )

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
    def validate_wikilinks(
        filename: str, project: Optional[str] = None, auto_fix: bool = True
    ) -> str:
        """
        Validate and auto-fix wikilink formats (correct: [[author2024_12345678]]).

        Args:
            filename: Markdown file to check
            project: Project slug (uses current if omitted)
            auto_fix: Auto-fix issues (default: True)
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
