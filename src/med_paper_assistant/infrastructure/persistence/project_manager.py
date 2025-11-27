"""
Project Manager - Multi-project support for MedPaper Assistant

Manages separate workspaces for different research papers, each with its own:
- concept.md
- drafts/
- references/
- data/
- results/
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime


class ProjectManager:
    """
    Manages multiple research paper projects with isolated directory structures.
    
    Each project has:
    - project.json: metadata and settings
    - concept.md: research concept
    - .memory/: project-specific AI memory (activeContext.md, progress.md)
    - drafts/: paper drafts
    - references/: saved references (by PMID)
    - data/: analysis data files
    - results/: exported documents
    """
    
    # Subdirectories for each project
    PROJECT_DIRS = ["drafts", "references", "data", "results", ".memory"]
    
    # Current project state file
    STATE_FILE = ".current_project"
    
    # Paper types and their characteristics
    PAPER_TYPES = {
        "original-research": {
            "name": "Original Research",
            "description": "Clinical trial, cohort study, cross-sectional study",
            "sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
            "typical_words": 3000
        },
        "systematic-review": {
            "name": "Systematic Review",
            "description": "Systematic literature review without meta-analysis",
            "sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
            "typical_words": 4000
        },
        "meta-analysis": {
            "name": "Meta-Analysis",
            "description": "Systematic review with quantitative synthesis",
            "sections": ["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
            "typical_words": 4500
        },
        "case-report": {
            "name": "Case Report",
            "description": "Single case or case series",
            "sections": ["Introduction", "Case Presentation", "Discussion", "Conclusion"],
            "typical_words": 1500
        },
        "review-article": {
            "name": "Review Article",
            "description": "Narrative review or invited review",
            "sections": ["Introduction", "Body (multiple sections)", "Conclusion"],
            "typical_words": 5000
        },
        "letter": {
            "name": "Letter / Correspondence",
            "description": "Brief communication or commentary",
            "sections": ["Main Text"],
            "typical_words": 500
        },
        "other": {
            "name": "Other",
            "description": "Editorial, perspective, methodology paper, etc.",
            "sections": ["Varies"],
            "typical_words": 2000
        }
    }
    
    def __init__(self, base_path: str = "."):
        """
        Initialize ProjectManager.
        
        Args:
            base_path: Base directory for the med-paper-assistant workspace.
        """
        self.base_path = Path(base_path).resolve()
        self.projects_dir = self.base_path / "projects"
        self.state_file = self.base_path / self.STATE_FILE
        
        # Ensure projects directory exists (create parent dirs if needed)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        
    def _slugify(self, name: str) -> str:
        """Convert project name to URL-safe slug."""
        import re
        # Convert to lowercase, replace spaces/underscores with hyphens
        slug = name.lower().strip()
        slug = re.sub(r'[\s_]+', '-', slug)
        # Remove non-alphanumeric characters except hyphens
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        return slug or "untitled"
    
    def create_project(
        self, 
        name: str, 
        description: str = "",
        authors: Optional[List[str]] = None,
        target_journal: str = "",
        paper_type: str = "",
        interaction_preferences: Optional[Dict[str, Any]] = None,
        memo: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new research paper project.
        
        Args:
            name: Human-readable project name.
            description: Brief description of the research.
            authors: List of author names.
            target_journal: Target journal for submission.
            paper_type: Type of paper (original-research, meta-analysis, etc.)
            interaction_preferences: User preferences for AI interaction.
            memo: Additional notes and reminders.
            
        Returns:
            Project info dictionary.
        """
        slug = self._slugify(name)
        project_path = self.projects_dir / slug
        
        if project_path.exists():
            return {
                "success": False,
                "error": f"Project '{slug}' already exists. Use switch_project to switch to it.",
                "slug": slug
            }
        
        # Validate paper type
        if paper_type and paper_type not in self.PAPER_TYPES:
            return {
                "success": False,
                "error": f"Invalid paper type '{paper_type}'. Valid types: {list(self.PAPER_TYPES.keys())}"
            }
        
        # Create project directory structure
        project_path.mkdir(parents=True)
        for subdir in self.PROJECT_DIRS:
            (project_path / subdir).mkdir()
        
        # Create project.json
        project_config = {
            "name": name,
            "slug": slug,
            "description": description,
            "authors": authors or [],
            "target_journal": target_journal,
            "paper_type": paper_type,
            "paper_type_info": self.PAPER_TYPES.get(paper_type, {}) if paper_type else {},
            "interaction_preferences": interaction_preferences or {},
            "memo": memo,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "concept"  # concept → drafting → review → submitted
        }
        
        config_path = project_path / "project.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(project_config, f, indent=2, ensure_ascii=False)
        
        # Create concept.md with type-specific template
        concept_template = self._get_concept_template(
            project_name=name, 
            paper_type=paper_type,
            target_journal=target_journal,
            memo=memo
        )
        concept_path = project_path / "concept.md"
        with open(concept_path, 'w', encoding='utf-8') as f:
            f.write(concept_template)
        
        # Create project memory files
        self._create_project_memory(project_path, name, paper_type, interaction_preferences or {}, memo)
        
        # Set as current project
        self._save_current_project(slug)
        
        return {
            "success": True,
            "message": f"Project '{name}' created successfully!",
            "slug": slug,
            "path": str(project_path),
            "structure": {
                "concept": str(concept_path),
                "memory": str(project_path / ".memory"),
                "drafts": str(project_path / "drafts"),
                "references": str(project_path / "references"),
                "data": str(project_path / "data"),
                "results": str(project_path / "results")
            }
        }
    
    def _get_concept_template(
        self, 
        project_name: str, 
        paper_type: str = "",
        target_journal: str = "",
        memo: str = ""
    ) -> str:
        """Get concept template by reading from template files.
        
        Architecture:
        - concept_base.md: Common template with shared sections
        - concept_{paper_type}.md: Paper-type specific sections
        
        Variables replaced:
        - {{PROJECT_NAME}} -> project_name
        - {{PAPER_TYPE}} -> paper type name  
        - {{CREATED_DATE}} -> current date
        - {{PAPER_TYPE_SECTIONS}} -> content from paper-type template
        - {{TARGET_JOURNAL}} -> target journal name
        - {{MEMO}} -> initial memo/notes
        """
        type_info = self.PAPER_TYPES.get(paper_type, {})
        type_name = type_info.get("name", "Research Paper")
        
        # Template directory
        templates_dir = (
            Path(__file__).parent.parent.parent 
            / "interfaces" / "mcp" / "templates"
        )
        
        # Read base template
        base_template_path = templates_dir / "concept_base.md"
        if base_template_path.exists():
            template = base_template_path.read_text(encoding="utf-8")
        else:
            # Fallback minimal template
            template = self._get_fallback_template(project_name, type_name)
            return template
        
        # Read paper-type specific sections
        paper_type_sections = self._read_paper_type_template(templates_dir, paper_type)
        
        # Replace variables
        template = template.replace("{{PROJECT_NAME}}", project_name)
        template = template.replace("{{PAPER_TYPE}}", type_name)
        template = template.replace("{{CREATED_DATE}}", datetime.now().strftime('%Y-%m-%d'))
        template = template.replace("{{PAPER_TYPE_SECTIONS}}", paper_type_sections)
        template = template.replace("{{TARGET_JOURNAL}}", target_journal or "[To be determined]")
        template = template.replace("{{MEMO}}", memo or "> [Personal notes and reminders]")
        
        return template
    
    def _read_paper_type_template(self, templates_dir: Path, paper_type: str) -> str:
        """Read paper-type specific template file.
        
        File naming convention:
        - concept_original_research.md
        - concept_meta_analysis.md
        - concept_systematic_review.md
        - concept_case_report.md
        - concept_review_article.md
        """
        # Map paper_type to filename
        type_to_file = {
            "original-research": "concept_original_research.md",
            "meta-analysis": "concept_meta_analysis.md",
            "systematic-review": "concept_systematic_review.md",
            "case-report": "concept_case_report.md",
            "review-article": "concept_review_article.md",
        }
        
        filename = type_to_file.get(paper_type)
        if not filename:
            return "## 📝 Research Question\n\n> [State your research question]\n\n## 📝 Methods Overview\n\n> [Describe your methodology]"
        
        template_path = templates_dir / filename
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        else:
            return f"<!-- Template file not found: {filename} -->"
    
    def _get_fallback_template(self, project_name: str, type_name: str) -> str:
        """Minimal fallback template when template files are missing."""
        return f"""# Research Concept: {project_name}

**Paper Type:** {type_name}
**Created:** {datetime.now().strftime('%Y-%m-%d')}

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
    
    def _create_project_memory(
        self, 
        project_path: Path, 
        project_name: str,
        paper_type: str = "",
        interaction_preferences: Dict[str, Any] = None,
        memo: str = ""
    ) -> None:
        """Create project-specific memory files."""
        memory_dir = project_path / ".memory"
        prefs = interaction_preferences or {}
        type_info = self.PAPER_TYPES.get(paper_type, {})
        
        # activeContext.md - Current research focus
        active_context = f"""# Active Context: {project_name}

## Project Settings

| Setting | Value |
|---------|-------|
| **Paper Type** | {type_info.get('name', 'Not specified')} |
| **Typical Words** | {type_info.get('typical_words', 'N/A')} |
| **Sections** | {', '.join(type_info.get('sections', []))} |
| **Target Journal** | [To be determined] |

## User Preferences

### Interaction Style
{prefs.get('interaction_style', '- [Not specified - ask user how they prefer to interact]')}

### Language Preferences
{prefs.get('language', '- [Not specified]')}

### Writing Style Notes
{prefs.get('writing_style', '- [Not specified]')}

## Current Focus
- [What you're currently working on]

## Recent Decisions
- [Important decisions made]

## Key References
- [Important papers to cite]

## Blockers / Questions
- [Issues to resolve]

## Memo / Notes
{memo if memo else '[No memo yet]'}

---
*Last Updated: {datetime.now().strftime('%Y-%m-%d')}*
"""
        with open(memory_dir / "activeContext.md", 'w', encoding='utf-8') as f:
            f.write(active_context)
        
        # progress.md - Research milestones (varies by paper type)
        if paper_type == "meta-analysis":
            progress = f"""# Research Progress: {project_name}

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
*Created: {datetime.now().strftime('%Y-%m-%d')}*
"""
        elif paper_type == "case-report":
            progress = f"""# Research Progress: {project_name}

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
*Created: {datetime.now().strftime('%Y-%m-%d')}*
"""
        else:  # original-research, review-article, or other
            progress = f"""# Research Progress: {project_name}

**Paper Type:** {type_info.get('name', 'Research Paper')}

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
*Created: {datetime.now().strftime('%Y-%m-%d')}*
"""
        with open(memory_dir / "progress.md", 'w', encoding='utf-8') as f:
            f.write(progress)
    
    def switch_project(self, slug: str) -> Dict[str, Any]:
        """
        Switch to an existing project.
        
        Args:
            slug: Project slug (directory name).
            
        Returns:
            Project info or error.
        """
        project_path = self.projects_dir / slug
        
        if not project_path.exists():
            available = self.list_projects()
            return {
                "success": False,
                "error": f"Project '{slug}' not found.",
                "available_projects": [p["slug"] for p in available.get("projects", [])]
            }
        
        self._save_current_project(slug)
        
        return self.get_project_info(slug)
    
    def get_current_project(self) -> Optional[str]:
        """
        Get the slug of the currently active project.
        
        Returns:
            Current project slug or None if not set.
        """
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r') as f:
                return f.read().strip() or None
        except Exception:
            return None
    
    def _save_current_project(self, slug: str) -> None:
        """Save current project to state file."""
        with open(self.state_file, 'w') as f:
            f.write(slug)
    
    def get_project_info(self, slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed info about a project.
        
        Args:
            slug: Project slug. If None, uses current project.
            
        Returns:
            Project info dictionary.
        """
        if slug is None:
            slug = self.get_current_project()
            if slug is None:
                return {
                    "success": False,
                    "error": "No project selected. Use create_project or switch_project first."
                }
        
        project_path = self.projects_dir / slug
        config_path = project_path / "project.json"
        
        if not config_path.exists():
            return {
                "success": False,
                "error": f"Project '{slug}' not found or corrupted."
            }
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Count contents
        drafts_count = len(list((project_path / "drafts").glob("*.md")))
        refs_count = len([d for d in (project_path / "references").iterdir() if d.is_dir()])
        data_count = len(list((project_path / "data").glob("*.*")))
        
        return {
            "success": True,
            "slug": slug,
            "is_current": slug == self.get_current_project(),
            **config,
            "paths": self.get_project_paths(slug),
            "stats": {
                "drafts": drafts_count,
                "references": refs_count,
                "data_files": data_count
            }
        }
    
    def get_project_paths(self, slug: Optional[str] = None) -> Dict[str, str]:
        """
        Get all paths for a project.
        
        Args:
            slug: Project slug. If None, uses current project.
            
        Returns:
            Dictionary of path names to absolute paths.
        """
        if slug is None:
            slug = self.get_current_project()
            if slug is None:
                raise ValueError("No project selected")
        
        project_path = self.projects_dir / slug
        
        return {
            "root": str(project_path),
            "concept": str(project_path / "concept.md"),
            "memory": str(project_path / ".memory"),
            "drafts": str(project_path / "drafts"),
            "references": str(project_path / "references"),
            "data": str(project_path / "data"),
            "results": str(project_path / "results"),
            "config": str(project_path / "project.json")
        }
    
    def list_projects(self) -> Dict[str, Any]:
        """
        List all projects.
        
        Returns:
            Dictionary with list of projects and current project.
        """
        projects = []
        current = self.get_current_project()
        
        if not self.projects_dir.exists():
            return {"projects": [], "current": None}
        
        for project_dir in sorted(self.projects_dir.iterdir()):
            if not project_dir.is_dir():
                continue
            
            config_path = project_dir / "project.json"
            if not config_path.exists():
                continue
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                projects.append({
                    "slug": project_dir.name,
                    "name": config.get("name", project_dir.name),
                    "status": config.get("status", "unknown"),
                    "created_at": config.get("created_at", ""),
                    "is_current": project_dir.name == current
                })
            except Exception:
                projects.append({
                    "slug": project_dir.name,
                    "name": project_dir.name,
                    "status": "error",
                    "is_current": project_dir.name == current
                })
        
        return {
            "projects": projects,
            "current": current,
            "count": len(projects)
        }
    
    def update_project_status(self, status: str, slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Update project status.
        
        Args:
            status: New status (concept, drafting, review, submitted, published).
            slug: Project slug. If None, uses current project.
            
        Returns:
            Updated project info.
        """
        if slug is None:
            slug = self.get_current_project()
            if slug is None:
                return {"success": False, "error": "No project selected"}
        
        config_path = self.projects_dir / slug / "project.json"
        
        if not config_path.exists():
            return {"success": False, "error": f"Project '{slug}' not found"}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        valid_statuses = ["concept", "drafting", "review", "submitted", "published"]
        if status not in valid_statuses:
            return {
                "success": False,
                "error": f"Invalid status. Must be one of: {valid_statuses}"
            }
        
        config["status"] = status
        config["updated_at"] = datetime.now().isoformat()
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "message": f"Project status updated to '{status}'",
            "slug": slug
        }
    
    def update_project_settings(
        self,
        slug: Optional[str] = None,
        paper_type: Optional[str] = None,
        target_journal: Optional[str] = None,
        interaction_preferences: Optional[Dict[str, Any]] = None,
        memo: Optional[str] = None,
        authors: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update project settings.
        
        Args:
            slug: Project slug. If None, uses current project.
            paper_type: Type of paper.
            target_journal: Target journal.
            interaction_preferences: User preferences for AI interaction.
            memo: Additional notes.
            authors: Author list.
            description: Project description.
            
        Returns:
            Updated project info.
        """
        if slug is None:
            slug = self.get_current_project()
            if slug is None:
                return {"success": False, "error": "No project selected"}
        
        project_path = self.projects_dir / slug
        config_path = project_path / "project.json"
        
        if not config_path.exists():
            return {"success": False, "error": f"Project '{slug}' not found"}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate paper type if provided
        if paper_type is not None:
            if paper_type not in self.PAPER_TYPES:
                return {
                    "success": False,
                    "error": f"Invalid paper type '{paper_type}'. Valid types: {list(self.PAPER_TYPES.keys())}"
                }
            config["paper_type"] = paper_type
            config["paper_type_info"] = self.PAPER_TYPES[paper_type]
        
        # Update other fields if provided
        if target_journal is not None:
            config["target_journal"] = target_journal
        if interaction_preferences is not None:
            # Merge with existing preferences
            existing_prefs = config.get("interaction_preferences", {})
            existing_prefs.update(interaction_preferences)
            config["interaction_preferences"] = existing_prefs
        if memo is not None:
            config["memo"] = memo
        if authors is not None:
            config["authors"] = authors
        if description is not None:
            config["description"] = description
        
        config["updated_at"] = datetime.now().isoformat()
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # Also update memory files if interaction_preferences or memo changed
        if interaction_preferences is not None or memo is not None:
            self._update_project_memory(project_path, config)
        
        return {
            "success": True,
            "message": "Project settings updated successfully",
            "slug": slug,
            "updated_fields": [
                k for k, v in {
                    "paper_type": paper_type,
                    "target_journal": target_journal,
                    "interaction_preferences": interaction_preferences,
                    "memo": memo,
                    "authors": authors,
                    "description": description
                }.items() if v is not None
            ]
        }
    
    def _update_project_memory(self, project_path: Path, config: Dict[str, Any]) -> None:
        """Update project memory files with new settings."""
        memory_path = project_path / ".memory" / "activeContext.md"
        if not memory_path.exists():
            return
        
        prefs = config.get("interaction_preferences", {})
        memo = config.get("memo", "")
        type_info = config.get("paper_type_info", {})
        
        # Read existing content
        content = memory_path.read_text(encoding='utf-8')
        
        # Update User Preferences section
        new_prefs_section = f"""## User Preferences

### Interaction Style
{prefs.get('interaction_style', '- [Not specified]')}

### Language Preferences
{prefs.get('language', '- [Not specified]')}

### Writing Style Notes
{prefs.get('writing_style', '- [Not specified]')}"""

        # Try to replace existing preferences section
        import re
        pattern = r'## User Preferences.*?(?=\n## |\Z)'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_prefs_section + '\n\n', content, flags=re.DOTALL)
        
        # Update memo section
        new_memo_section = f"""## Memo / Notes
{memo if memo else '[No memo yet]'}"""
        
        memo_pattern = r'## Memo / Notes.*?(?=\n---|\Z)'
        if re.search(memo_pattern, content, re.DOTALL):
            content = re.sub(memo_pattern, new_memo_section + '\n\n', content, flags=re.DOTALL)
        
        # Update timestamp
        content = re.sub(
            r'\*Last Updated:.*?\*',
            f"*Last Updated: {datetime.now().strftime('%Y-%m-%d')}*",
            content
        )
        
        memory_path.write_text(content, encoding='utf-8')
    
    def get_paper_types(self) -> Dict[str, Dict[str, Any]]:
        """Return available paper types and their info."""
        return self.PAPER_TYPES
    
    def delete_project(self, slug: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete a project (requires confirmation).
        
        Args:
            slug: Project slug to delete.
            confirm: Must be True to actually delete.
            
        Returns:
            Result of deletion.
        """
        if not confirm:
            return {
                "success": False,
                "error": "Deletion requires confirm=True. This will permanently delete all project data!"
            }
        
        project_path = self.projects_dir / slug
        
        if not project_path.exists():
            return {"success": False, "error": f"Project '{slug}' not found"}
        
        import shutil
        shutil.rmtree(project_path)
        
        # Clear current if this was the current project
        if self.get_current_project() == slug:
            if self.state_file.exists():
                self.state_file.unlink()
        
        return {
            "success": True,
            "message": f"Project '{slug}' deleted permanently."
        }


# Singleton instance for global access
_project_manager: Optional[ProjectManager] = None


def get_project_manager(base_path: str = ".") -> ProjectManager:
    """Get or create the global ProjectManager instance."""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager(base_path)
    return _project_manager
