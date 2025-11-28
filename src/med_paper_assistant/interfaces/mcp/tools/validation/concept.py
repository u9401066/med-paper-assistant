"""
Concept Validation Tools

validate_concept, validate_concept_quick
"""

import os
from typing import Optional
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services.concept_validator import ConceptValidator
from .._shared import ensure_project_context, get_project_list_for_prompt


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
        run_novelty_check: bool = True
    ) -> str:
        """
        Validate a concept file before proceeding to draft writing.
        
        This tool performs comprehensive validation including:
        1. Structural validation - Required sections present
        2. Novelty evaluation - LLM-based scoring (3 rounds, 75+ threshold)
        3. Consistency check - Alignment between sections
        
        The novelty check uses 3 evaluation rounds. All rounds must score
        75+ out of 100 for the concept to pass. This ensures the NOVELTY
        STATEMENT truly describes novel contributions.
        
        Args:
            filename: Path to the concept file (e.g., "concept.md").
            project: Project slug. Agent should confirm with user before calling.
            run_novelty_check: Whether to run LLM-based novelty scoring (default: True).
        
        Returns:
            Validation report with checklist status, novelty scores, and suggestions.
        """
        is_valid, error_msg = _validate_project_context(project)
        if not is_valid:
            return error_msg
        
        # Resolve path
        if not os.path.isabs(filename):
            from med_paper_assistant.infrastructure.persistence import get_project_manager
            pm = get_project_manager()
            current = pm.get_current_project()
            
            if current.get("project_path"):
                project_concept = os.path.join(current["project_path"], "concept.md")
                if os.path.exists(project_concept) and filename in ["concept.md", project_concept]:
                    filename = project_concept
                else:
                    filename = os.path.join("drafts", filename)
            else:
                filename = os.path.join("drafts", filename)
        
        if not os.path.exists(filename):
            return f"❌ Error: Concept file not found: {filename}\n\n" \
                   f"Use `/mdpaper.concept` to create a concept file first."
        
        try:
            result = _concept_validator.validate(
                filename,
                run_novelty_check=run_novelty_check,
                run_consistency_check=True,
                run_citation_check=False,
                force_refresh=True
            )
            
            return _concept_validator.generate_report(result)
            
        except Exception as e:
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
        if project:
            is_valid, error_msg = _validate_project_context(project)
            if not is_valid:
                return error_msg
        
        if not os.path.isabs(filename):
            from med_paper_assistant.infrastructure.persistence import get_project_manager
            pm = get_project_manager()
            current = pm.get_current_project()
            
            if current.get("project_path"):
                project_concept = os.path.join(current["project_path"], "concept.md")
                if os.path.exists(project_concept) and filename in ["concept.md", project_concept]:
                    filename = project_concept
                else:
                    filename = os.path.join("drafts", filename)
            else:
                filename = os.path.join("drafts", filename)
        
        if not os.path.exists(filename):
            return f"❌ Error: Concept file not found: {filename}"
        
        try:
            result = _concept_validator.validate_structure_only(filename)
            return _concept_validator.generate_report(result)
        except Exception as e:
            return f"❌ Error: {str(e)}"
