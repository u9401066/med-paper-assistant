"""
Draft Writing Tools

write_draft, draft_section, read_draft, list_drafts
"""

import os
import re
from typing import Optional
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.concept_validator import ConceptValidator
from med_paper_assistant.domain.services.wikilink_validator import validate_wikilinks_in_content
from .._shared import ensure_project_context, get_project_list_for_prompt, log_tool_call, log_tool_result, log_agent_misuse, log_tool_error


# Global validator instance
_concept_validator = ConceptValidator()


def _get_concept_path() -> str:
    """Get the path to the current project's concept.md file."""
    from med_paper_assistant.infrastructure.persistence import get_project_manager
    pm = get_project_manager()
    current = pm.get_current_project()
    
    if current.get("project_path"):
        return os.path.join(current["project_path"], "concept.md")
    return None


def _enforce_concept_validation(require_novelty: bool = True) -> tuple:
    """
    Enforce concept validation before draft operations.
    
    Returns:
        Tuple of (can_proceed: bool, message: str, protected_content: dict)
    """
    concept_path = _get_concept_path()
    
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
            "Draft writing is blocked until concept validation passes.",
            {}
        )
    
    result = _concept_validator.validate(
        concept_path,
        run_novelty_check=require_novelty,
        run_consistency_check=True,
        force_refresh=False
    )
    
    if not result.overall_passed:
        report = _concept_validator.generate_report(result)
        return (
            False,
            f"❌ **CONCEPT VALIDATION FAILED**\n\n"
            f"You must fix the following issues before writing drafts:\n\n"
            f"{report}\n\n"
            f"**Draft writing is blocked until validation passes.**",
            {}
        )
    
    novelty_section = result.sections.get("novelty_statement")
    selling_section = result.sections.get("selling_points")
    
    protected_content = {
        "novelty_statement": novelty_section.content if novelty_section else "",
        "selling_points": selling_section.content if selling_section else "",
        "novelty_score": result.novelty_average
    }
    
    return (
        True,
        f"✅ Concept validation passed (Novelty score: {result.novelty_average:.1f}/100)",
        protected_content
    )


def _validate_wikilinks_in_content(content: str, references_dir: Optional[str] = None) -> tuple:
    """
    驗證內容中的 wikilinks 並自動修復。
    
    Returns:
        Tuple of (fixed_content: str, report: str or None)
    """
    result, fixed_content = validate_wikilinks_in_content(
        content,
        references_dir=references_dir,
        auto_fix=True
    )
    
    report = None
    if result.auto_fixed > 0:
        report = f"🔧 自動修復 {result.auto_fixed} 個 wikilink 格式錯誤"
    elif result.issues:
        report = result.to_report()
    
    return fixed_content, report


def _validate_project_context(project: Optional[str]) -> tuple:
    """Validate project context before draft operations."""
    is_valid, msg, project_info = ensure_project_context(project)
    if not is_valid:
        return False, f"❌ {msg}\n\n{get_project_list_for_prompt()}"
    return True, None


def register_writing_tools(mcp: FastMCP, drafter: Drafter):
    """Register draft writing tools."""

    @mcp.tool()
    def draft_section(
        topic: str, 
        notes: str, 
        project: Optional[str] = None,
        skip_validation: bool = False
    ) -> str:
        """
        Draft a section of a medical paper based on notes.
        
        ⚠️ REQUIRES: Valid concept.md with novelty check passed.
        
        This tool enforces concept validation before drafting. The draft must:
        - Preserve 🔒 NOVELTY STATEMENT in Introduction
        - Preserve 🔒 KEY SELLING POINTS in Discussion
        - Not weaken or remove protected content
        
        Args:
            topic: The topic of the section (e.g., "Introduction").
            notes: Raw notes or bullet points to convert into text.
            project: Project slug. Agent should confirm with user before calling.
            skip_validation: For internal use only. Do not set to True.
        """
        log_tool_call("draft_section", {
            "topic": topic, 
            "notes_len": len(notes), 
            "project": project, 
            "skip_validation": skip_validation
        })
        
        is_valid, error_msg = _validate_project_context(project)
        if not is_valid:
            log_agent_misuse("draft_section", "valid project context required", {"project": project}, error_msg)
            return error_msg
        
        if not skip_validation:
            can_proceed, message, protected = _enforce_concept_validation()
            if not can_proceed:
                log_tool_result("draft_section", "concept validation failed", success=False)
                return message
        
        reminder = ""
        if topic.lower() == "introduction":
            reminder = "\n\n⚠️ **REMINDER**: Introduction must reflect the 🔒 NOVELTY STATEMENT."
        elif topic.lower() == "discussion":
            reminder = "\n\n⚠️ **REMINDER**: Discussion must emphasize 🔒 KEY SELLING POINTS."
        
        result = f"Drafting section '{topic}' based on notes...{reminder}"
        log_tool_result("draft_section", result, success=True)
        return result

    @mcp.tool()
    def write_draft(
        filename: str, 
        content: str, 
        project: Optional[str] = None,
        skip_validation: bool = False
    ) -> str:
        """
        Create a draft file with automatic citation formatting.
        Use (PMID:123456) or [PMID:123456] in content to insert citations.
        
        ⚠️ REQUIRES: Valid concept.md with novelty check passed.
        
        Exception: Writing to concept.md itself does not require validation.
        
        Args:
            filename: Name of the file (e.g., "draft.md").
            content: The text content with citation placeholders.
            project: Project slug. Agent should confirm with user before calling.
            skip_validation: For internal use only. Do not set to True.
        """
        log_tool_call("write_draft", {
            "filename": filename,
            "content_len": len(content),
            "project": project,
            "skip_validation": skip_validation
        })
        
        is_valid, error_msg = _validate_project_context(project)
        if not is_valid:
            log_agent_misuse("write_draft", "valid project context required", {"project": project}, error_msg)
            return error_msg
        
        is_concept_file = "concept" in filename.lower()
        
        if not skip_validation and not is_concept_file:
            can_proceed, message, protected = _enforce_concept_validation()
            if not can_proceed:
                log_tool_result("write_draft", "concept validation failed", success=False)
                return message
        
        # 🔧 Pre-check: 驗證並修復 wikilink 格式
        references_dir = None
        from med_paper_assistant.infrastructure.persistence import get_project_manager
        pm = get_project_manager()
        current = pm.get_current_project()
        if current.get("project_path"):
            references_dir = os.path.join(current["project_path"], "references")
        
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
            
            result = f"Draft created successfully at: {path}{reminder}"
            log_tool_result("write_draft", result, success=True)
            return result
        except Exception as e:
            log_tool_error("write_draft", e, {"filename": filename, "content_len": len(content)})
            return f"Error creating draft: {str(e)}"

    @mcp.tool()
    def list_drafts(project: Optional[str] = None) -> str:
        """
        List all available draft files in the drafts/ directory.
        
        Args:
            project: Project slug. If not specified, uses current project.
        
        Returns:
            List of draft files with their word counts.
        """
        log_tool_call("list_drafts", {"project": project})
        
        if project:
            is_valid, error_msg = _validate_project_context(project)
            if not is_valid:
                log_agent_misuse("list_drafts", "valid project context required", {"project": project}, error_msg)
                return error_msg
        
        drafts_dir = "drafts"
        if not os.path.exists(drafts_dir):
            result = "📁 No drafts/ directory found. Create drafts using write_draft tool first."
            log_tool_result("list_drafts", result, success=True)
            return result
        
        drafts = [f for f in os.listdir(drafts_dir) if f.endswith('.md')]
        
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
                with open(draft_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                sections = len(re.findall(r'^#+\s+', content, re.MULTILINE))
                words = len([w for w in content.split() if w.strip()])
                
                output += f"| {i} | {draft_file} | {sections} | {words} |\n"
            except Exception:
                output += f"| {i} | {draft_file} | Error | - |\n"
        
        log_tool_result("list_drafts", f"found {len(drafts)} drafts", success=True)
        return output

    @mcp.tool()
    def read_draft(filename: str, project: Optional[str] = None) -> str:
        """
        Read a draft file and return its structure and content.
        
        Args:
            filename: Path to the markdown draft file.
            project: Project slug. If not specified, uses current project.
            
        Returns:
            Draft content organized by sections with word counts.
        """
        log_tool_call("read_draft", {"filename": filename, "project": project})
        
        if project:
            is_valid, error_msg = _validate_project_context(project)
            if not is_valid:
                log_agent_misuse("read_draft", "valid project context required", {"project": project}, error_msg)
                return error_msg
        
        if not os.path.isabs(filename):
            filename = os.path.join("drafts", filename)
        
        if not os.path.exists(filename):
            result = f"Error: Draft file not found: {filename}"
            log_tool_result("read_draft", result, success=False)
            return result
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            sections = {}
            current_section = None
            current_content = []
            
            for line in content.split('\n'):
                if line.startswith('#'):
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content)
                    section_name = re.sub(r'^#+\s*\d*\.?\s*', '', line).strip()
                    current_section = section_name if section_name else "Untitled"
                    current_content = []
                elif current_section:
                    current_content.append(line)
            
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)
            
            output = f"📝 **Draft: {os.path.basename(filename)}**\n\n"
            output += "| Section | Word Count | Preview |\n"
            output += "|---------|------------|----------|\n"
            
            for sec_name, sec_content in sections.items():
                words = len([w for w in sec_content.split() if w.strip()])
                preview = sec_content[:50].replace('\n', ' ').strip() + "..."
                output += f"| {sec_name} | {words} | {preview} |\n"
            
            output += "\n---\n\n"
            output += "**Full Content by Section:**\n\n"
            
            for sec_name, sec_content in sections.items():
                output += f"### {sec_name}\n\n"
                output += sec_content.strip()[:500]
                if len(sec_content) > 500:
                    output += f"\n\n*... ({len(sec_content)} characters total)*"
                output += "\n\n"
            
            log_tool_result("read_draft", f"read {len(sections)} sections from {filename}", success=True)
            return output
        except Exception as e:
            log_tool_error("read_draft", e, {"filename": filename})
            return f"Error reading draft: {str(e)}"
