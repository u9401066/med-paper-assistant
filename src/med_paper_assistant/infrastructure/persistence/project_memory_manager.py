"""
Project Memory Manager - Manages project-specific memory files.

Handles creation and updating of .memory/ files for AI context.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ...domain.paper_types import PaperTypeInfo, get_paper_type


class ProjectMemoryManager:
    """
    Manages project memory files for AI context persistence.

    Memory files:
    - activeContext.md: Current research focus, preferences, blockers
    - progress.md: Research milestones and task tracking
    """

    def __init__(self, project_path: Path):
        """
        Initialize memory manager for a project.

        Args:
            project_path: Root path of the project.
        """
        self.project_path = Path(project_path)
        self.memory_dir = self.project_path / ".memory"

    def create_memory_files(
        self,
        project_name: str,
        paper_type: str = "",
        interaction_preferences: Optional[Dict[str, Any]] = None,
        memo: str = "",
    ) -> None:
        """
        Create initial memory files for a new project.

        Args:
            project_name: Name of the project.
            paper_type: Type of paper.
            interaction_preferences: User preferences for AI interaction.
            memo: Initial memo/notes.
        """
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        type_info = get_paper_type(paper_type)
        prefs = interaction_preferences or {}

        self._write_active_context(project_name, type_info, prefs, memo)
        self._write_progress(project_name, paper_type, type_info)

    def update_preferences(self, interaction_preferences: Dict[str, Any], memo: str = "") -> None:
        """
        Update preferences and memo in activeContext.md.

        Args:
            interaction_preferences: Updated preferences.
            memo: Updated memo.
        """
        active_context_path = self.memory_dir / "activeContext.md"
        if not active_context_path.exists():
            return

        import re

        content = active_context_path.read_text(encoding="utf-8")

        # Update User Preferences section
        prefs = interaction_preferences
        new_prefs_section = f"""## User Preferences

### Interaction Style
{prefs.get("interaction_style", "- [Not specified]")}

### Language Preferences
{prefs.get("language", "- [Not specified]")}

### Writing Style Notes
{prefs.get("writing_style", "- [Not specified]")}"""

        pattern = r"## User Preferences.*?(?=\n## |\Z)"
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_prefs_section + "\n\n", content, flags=re.DOTALL)

        # Update memo section
        new_memo_section = f"""## Memo / Notes
{memo if memo else "[No memo yet]"}"""

        memo_pattern = r"## Memo / Notes.*?(?=\n---|\Z)"
        if re.search(memo_pattern, content, re.DOTALL):
            content = re.sub(memo_pattern, new_memo_section + "\n\n", content, flags=re.DOTALL)

        # Update timestamp
        content = re.sub(
            r"\*Last Updated:.*?\*",
            f"*Last Updated: {datetime.now().strftime('%Y-%m-%d')}*",
            content,
        )

        active_context_path.write_text(content, encoding="utf-8")

    def _write_active_context(
        self, project_name: str, type_info: PaperTypeInfo, prefs: Dict[str, Any], memo: str
    ) -> None:
        """Write activeContext.md file."""
        content = f"""# Active Context: {project_name}

## Project Settings

| Setting | Value |
|---------|-------|
| **Paper Type** | {type_info.name} |
| **Typical Words** | {type_info.typical_words} |
| **Sections** | {", ".join(type_info.sections)} |
| **Target Journal** | [To be determined] |

## User Preferences

### Interaction Style
{prefs.get("interaction_style", "- [Not specified - ask user how they prefer to interact]")}

### Language Preferences
{prefs.get("language", "- [Not specified]")}

### Writing Style Notes
{prefs.get("writing_style", "- [Not specified]")}

## Current Focus
- [What you're currently working on]

## Recent Decisions
- [Important decisions made]

## Key References
- [Important papers to cite]

## Blockers / Questions
- [Issues to resolve]

## Memo / Notes
{memo if memo else "[No memo yet]"}

---
*Last Updated: {datetime.now().strftime("%Y-%m-%d")}*
"""
        (self.memory_dir / "activeContext.md").write_text(content, encoding="utf-8")

    def _write_progress(self, project_name: str, paper_type: str, type_info: PaperTypeInfo) -> None:
        """Write progress.md file based on paper type."""
        if paper_type == "meta-analysis":
            content = self._get_meta_analysis_progress(project_name)
        elif paper_type == "case-report":
            content = self._get_case_report_progress(project_name)
        else:
            content = self._get_default_progress(project_name, type_info)

        (self.memory_dir / "progress.md").write_text(content, encoding="utf-8")

    def _get_meta_analysis_progress(self, project_name: str) -> str:
        """Get progress template for meta-analysis."""
        return f"""# Research Progress: {project_name}

**Paper Type:** Meta-Analysis

## Milestones

- **Protocol Development** (IN PROGRESS):
  - [ ] Define PICO question
  - [ ] Register on PROSPERO
  - [ ] Develop search strategy
  - [ ] Define eligibility criteria

- **Literature Search** (NOT STARTED):
  - [ ] Search all databases
  - [ ] Remove duplicates
  - [ ] Title/abstract screening
  - [ ] Full-text screening
  - [ ] Create PRISMA flowchart

- **Data Extraction** (NOT STARTED):
  - [ ] Create extraction form
  - [ ] Extract data from included studies
  - [ ] Verify extraction accuracy

- **Risk of Bias Assessment** (NOT STARTED):
  - [ ] Assess each study
  - [ ] Create summary table
  - [ ] Generate risk of bias plots

- **Statistical Analysis** (NOT STARTED):
  - [ ] Calculate effect sizes
  - [ ] Pool results (forest plot)
  - [ ] Assess heterogeneity
  - [ ] Subgroup analyses
  - [ ] Sensitivity analyses
  - [ ] Publication bias (funnel plot)

- **Writing** (NOT STARTED):
  - [ ] Draft Introduction
  - [ ] Draft Methods
  - [ ] Draft Results (with figures/tables)
  - [ ] Draft Discussion
  - [ ] Write Abstract
  - [ ] Prepare PRISMA checklist

- **Submission** (NOT STARTED):
  - [ ] Format for target journal
  - [ ] Co-author review
  - [ ] Submit manuscript

---
*Created: {datetime.now().strftime("%Y-%m-%d")}*
"""

    def _get_case_report_progress(self, project_name: str) -> str:
        """Get progress template for case report."""
        return f"""# Research Progress: {project_name}

**Paper Type:** Case Report

## Milestones

- **Case Documentation** (IN PROGRESS):
  - [ ] Collect patient information
  - [ ] Obtain patient consent
  - [ ] Document timeline of events
  - [ ] Gather images/investigations

- **Literature Review** (NOT STARTED):
  - [ ] Search for similar cases
  - [ ] Identify what makes this unique
  - [ ] Find relevant background literature

- **Writing** (NOT STARTED):
  - [ ] Draft Introduction
  - [ ] Write Case Presentation
  - [ ] Draft Discussion
  - [ ] Write Conclusion
  - [ ] Prepare teaching points

- **Submission** (NOT STARTED):
  - [ ] Format for target journal
  - [ ] Prepare figures
  - [ ] Co-author review
  - [ ] Submit manuscript

---
*Created: {datetime.now().strftime("%Y-%m-%d")}*
"""

    def _get_default_progress(self, project_name: str, type_info: PaperTypeInfo) -> str:
        """Get default progress template."""
        return f"""# Research Progress: {project_name}

**Paper Type:** {type_info.name}

## Milestones

- **Concept Development** (IN PROGRESS):
  - [ ] Define research question
  - [ ] Literature review
  - [ ] Identify research gap
  - [ ] Define methodology

- **Data Collection** (NOT STARTED):
  - [ ] Prepare data collection tools
  - [ ] Collect data
  - [ ] Data cleaning

- **Analysis** (NOT STARTED):
  - [ ] Statistical analysis
  - [ ] Generate figures/tables
  - [ ] Interpret results

- **Writing** (NOT STARTED):
  - [ ] Draft Introduction
  - [ ] Draft Methods
  - [ ] Draft Results
  - [ ] Draft Discussion
  - [ ] Write Abstract

- **Submission** (NOT STARTED):
  - [ ] Format for target journal
  - [ ] Co-author review
  - [ ] Submit manuscript

---
*Created: {datetime.now().strftime("%Y-%m-%d")}*
"""
