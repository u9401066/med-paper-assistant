"""
Concept Template Reader - Reads and processes concept templates.

Handles the base + paper-type template architecture.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from ...domain.paper_types import get_paper_type


class ConceptTemplateReader:
    """
    Reads and processes concept templates for research projects.

    Template Architecture:
    - concept_base.md: Common sections (NOVELTY, SELLING POINTS, etc.)
    - concept_{paper_type}.md: Paper-type specific sections

    Variables:
    - {{PROJECT_NAME}} -> project name
    - {{PAPER_TYPE}} -> paper type display name
    - {{CREATED_DATE}} -> creation date
    - {{PAPER_TYPE_SECTIONS}} -> content from paper-type template
    - {{TARGET_JOURNAL}} -> target journal
    - {{MEMO}} -> initial memo/notes
    """

    # Template filename mappings
    PAPER_TYPE_TEMPLATES = {
        "original-research": "concept_original_research.md",
        "meta-analysis": "concept_meta_analysis.md",
        "systematic-review": "concept_systematic_review.md",
        "case-report": "concept_case_report.md",
        "review-article": "concept_review_article.md",
    }

    # These profiles have a different concept contract from the journal-paper
    # base template, so they are complete documents rather than inserted
    # fragments. In particular, novelty is not falsely required for proposals,
    # closeout reports, student work, or theses.
    FULL_DOCUMENT_TEMPLATES = {
        "research-proposal": "concept_research_proposal.md",
        "project-closeout-report": "concept_project_closeout_report.md",
        "student-paper": "concept_student_paper.md",
        "conference-paper": "concept_conference_paper.md",
        "thesis-dissertation": "concept_thesis_dissertation.md",
        "arxiv-preprint": "concept_arxiv_preprint.md",
    }

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize template reader.

        Args:
            templates_dir: Directory containing templates.
                          If None, uses default location.
        """
        if templates_dir is None:
            # Default: interfaces/mcp/templates relative to this file
            self.templates_dir = (
                Path(__file__).parent.parent.parent / "interfaces" / "mcp" / "templates"
            )
        else:
            self.templates_dir = Path(templates_dir)

    def get_concept_template(
        self, project_name: str, paper_type: str = "", target_journal: str = "", memo: str = ""
    ) -> str:
        """
        Get processed concept template.

        Args:
            project_name: Name of the project.
            paper_type: Type of paper (e.g., "meta-analysis").
            target_journal: Target journal name.
            memo: Initial memo/notes.

        Returns:
            Processed template string.
        """
        type_info = get_paper_type(paper_type)
        type_name = type_info.name

        full_template_filename = self.FULL_DOCUMENT_TEMPLATES.get(paper_type)
        if full_template_filename:
            full_template_path = self.templates_dir / full_template_filename
            if full_template_path.exists():
                return self._replace_variables(
                    full_template_path.read_text(encoding="utf-8"),
                    project_name=project_name,
                    type_name=type_name,
                    target_journal=target_journal,
                    memo=memo,
                )

        # Read base template
        base_template = self._read_base_template()
        if base_template is None:
            return self._get_fallback_template(project_name, type_name)

        # Read paper-type specific sections
        paper_type_sections = self._read_paper_type_sections(paper_type)

        return self._replace_variables(
            base_template,
            project_name=project_name,
            type_name=type_name,
            target_journal=target_journal,
            memo=memo,
            paper_type_sections=paper_type_sections,
        )

    def _replace_variables(
        self,
        template: str,
        *,
        project_name: str,
        type_name: str,
        target_journal: str,
        memo: str,
        paper_type_sections: str = "",
    ) -> str:
        """Replace variables shared by base and full-document templates."""
        replacements = {
            "{{PROJECT_NAME}}": project_name,
            "{{PAPER_TYPE}}": type_name,
            "{{CREATED_DATE}}": datetime.now().strftime("%Y-%m-%d"),
            "{{PAPER_TYPE_SECTIONS}}": paper_type_sections,
            "{{TARGET_JOURNAL}}": target_journal or "[To be determined]",
            "{{MEMO}}": memo or "> [Personal notes and reminders]",
        }
        for variable, value in replacements.items():
            template = template.replace(variable, value)
        return template

    def _read_base_template(self) -> Optional[str]:
        """Read the base concept template."""
        base_path = self.templates_dir / "concept_base.md"
        if base_path.exists():
            return base_path.read_text(encoding="utf-8")
        return None

    def _read_paper_type_sections(self, paper_type: str) -> str:
        """Read paper-type specific template sections."""
        filename = self.PAPER_TYPE_TEMPLATES.get(paper_type)

        if not filename:
            return self._get_default_sections()

        template_path = self.templates_dir / filename
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")

        return f"<!-- Template file not found: {filename} -->"

    def _get_default_sections(self) -> str:
        """Get default sections when no paper type specified."""
        return """## 📝 Research Question

> [State your research question]

## 📝 Methods Overview

> [Describe your methodology]"""

    def _get_fallback_template(self, project_name: str, type_name: str) -> str:
        """Minimal fallback template when template files are missing."""
        return f"""# Research Concept: {project_name}

**Paper Type:** {type_name}
**Created:** {datetime.now().strftime("%Y-%m-%d")}

---

## 🔒 NOVELTY STATEMENT ⚠️ REQUIRED

**What is new?**
> [Describe the novel aspect]

**Why hasn't this been done before?**
> [Explain the gap]

**What will this change?**
> [Describe the impact]

---

## 🔒 KEY SELLING POINTS ⚠️ REQUIRED

1.
2.
3.

---

## 📝 Background

> [Research background]

## 📝 Research Question

> [Primary research question]

## 📝 Methods Overview

> [Brief methods]

## 📝 Expected Outcomes

> [Expected results]

---

## 🔒 Author Notes

> [Personal notes]

---
"""
