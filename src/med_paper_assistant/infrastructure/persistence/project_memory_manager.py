"""Project-specific memory file generation and updates."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ...domain.paper_types import PaperTypeInfo, get_paper_type
from ...shared.constants import DEFAULT_WORKFLOW_MODE


class ProjectMemoryManager:
    """Manage .memory files for project context persistence."""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.memory_dir = self.project_path / ".memory"

    def create_memory_files(
        self,
        project_name: str,
        paper_type: str = "",
        interaction_preferences: Optional[Dict[str, Any]] = None,
        memo: str = "",
        workflow_mode: str = DEFAULT_WORKFLOW_MODE,
    ) -> None:
        """Create initial memory files for a new project."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        type_info = get_paper_type(paper_type)
        prefs = interaction_preferences or {}

        self._write_active_context(project_name, type_info, prefs, memo, workflow_mode)
        self._write_progress(project_name, paper_type, type_info, workflow_mode)

    def update_preferences(self, interaction_preferences: Dict[str, Any], memo: str = "") -> None:
        """Update preferences and memo in activeContext.md."""
        active_context_path = self.memory_dir / "activeContext.md"
        if not active_context_path.exists():
            return

        import re

        content = active_context_path.read_text(encoding="utf-8")

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

        new_memo_section = f"""## Memo / Notes
{memo if memo else "[No memo yet]"}"""

        memo_pattern = r"## Memo / Notes.*?(?=\n---|\Z)"
        if re.search(memo_pattern, content, re.DOTALL):
            content = re.sub(memo_pattern, new_memo_section + "\n\n", content, flags=re.DOTALL)

        content = re.sub(
            r"\*Last Updated:.*?\*",
            f"*Last Updated: {datetime.now().strftime('%Y-%m-%d')}*",
            content,
        )

        active_context_path.write_text(content, encoding="utf-8")

    def _write_active_context(
        self,
        project_name: str,
        type_info: PaperTypeInfo,
        prefs: Dict[str, Any],
        memo: str,
        workflow_mode: str,
    ) -> None:
        """Write activeContext.md file."""
        if workflow_mode == "library-wiki":
            content = f"""# Active Context: {project_name}

## Workspace Settings

| Setting | Value |
|---------|-------|
| **Workflow Mode** | Library Wiki Path |
| **Focus** | Agent-maintained literature library |
| **Target Journal** | Optional later |

## User Preferences

### Interaction Style
{prefs.get("interaction_style", "- [Not specified - ask user how they prefer to interact]")}

### Language Preferences
{prefs.get("language", "- [Not specified]")}

### Writing Style Notes
{prefs.get("writing_style", "- [Not specified]")}

## Current Focus
- [Capture incoming papers, notes, and questions]

## Reading Queues
- Inbox
- Active reading
- Synthesis targets

## Knowledge Threads
- [Themes, methods, or claims worth linking]

## Blockers / Questions
- [Identity resolution, missing PDFs, comparison targets]

## Memo / Notes
{memo if memo else "[No memo yet]"}

---
*Last Updated: {datetime.now().strftime("%Y-%m-%d")}*
"""
        else:
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

    def _write_progress(
        self,
        project_name: str,
        paper_type: str,
        type_info: PaperTypeInfo,
        workflow_mode: str,
    ) -> None:
        """Write progress.md based on workflow mode and paper type."""
        if workflow_mode == "library-wiki":
            content = self._get_library_progress(project_name)
        elif paper_type == "meta-analysis":
            content = self._get_meta_analysis_progress(project_name)
        elif paper_type == "case-report":
            content = self._get_case_report_progress(project_name)
        else:
            content = self._get_default_progress(project_name, type_info)

        (self.memory_dir / "progress.md").write_text(content, encoding="utf-8")

    def _get_meta_analysis_progress(self, project_name: str) -> str:
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

    def _get_library_progress(self, project_name: str) -> str:
        return f"""# Research Progress: {project_name}

**Workflow Mode:** Library Wiki Path

## Milestones

- **Ingestion** (IN PROGRESS):
  - [ ] Search and save key references
  - [ ] Import notes / markdown / web sources
  - [ ] Resolve duplicate identities

- **Organization** (NOT STARTED):
  - [ ] Link related papers, authors, and themes
  - [ ] Build reading queues
  - [ ] Tag high-value evidence

- **Analysis** (NOT STARTED):
  - [ ] Summarize methods and outcomes
  - [ ] Compare claims across papers
  - [ ] Track contradictions or open questions

- **Synthesis** (NOT STARTED):
  - [ ] Build synthesis pages
  - [ ] Refresh library dashboards
  - [ ] Materialize graph context for navigation

- **Query & Retrieval** (NOT STARTED):
  - [ ] Test key questions against the library
  - [ ] Validate source anchors and fragments
  - [ ] Prepare reusable topic overviews

- **Optional Manuscript Transition** (NOT STARTED):
  - [ ] Choose a paper direction
  - [ ] Switch workflow_mode to manuscript
  - [ ] Define concept and start drafting

---
*Created: {datetime.now().strftime("%Y-%m-%d")}*
"""
