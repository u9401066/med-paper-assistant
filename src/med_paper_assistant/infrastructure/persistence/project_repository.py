"""
Project Repository - Persistence for Project entities.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from med_paper_assistant.domain.entities.project import Project
from med_paper_assistant.shared.constants import PAPER_TYPES, PROJECT_DIRECTORIES, LIBRARY_DIRECTORIES, WORKFLOW_MODES
from med_paper_assistant.shared.exceptions import (
    InvalidPaperTypeError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
)

from .project_memory_manager import ProjectMemoryManager


class ProjectRepository:
    """
    Repository for Project persistence.

    Handles saving, loading, and managing projects on disk.
    """

    def __init__(self, projects_dir: Path):
        self.projects_dir = projects_dir
        self._current_project_file = projects_dir.parent / ".current_project"
        self._ensure_dir()

    def _ensure_dir(self):
        """Ensure projects directory exists."""
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def create(self, project: Project) -> Project:
        """
        Create a new project on disk.

        Args:
            project: Project entity to create.

        Returns:
            Created project with updated timestamps.

        Raises:
            ProjectAlreadyExistsError: If project already exists.
            InvalidPaperTypeError: If paper type is invalid.
        """
        if project.path.exists():
            raise ProjectAlreadyExistsError(f"Project '{project.slug}' already exists.")

        if project.paper_type and project.paper_type not in PAPER_TYPES:
            raise InvalidPaperTypeError(f"Invalid paper type '{project.paper_type}'.")

        if project.workflow_mode not in WORKFLOW_MODES:
            raise ValueError(f"Invalid workflow mode '{project.workflow_mode}'.")

        # Create directory structure
        project.path.mkdir(parents=True)
        dirs_to_create = (
            LIBRARY_DIRECTORIES 
            if project.workflow_mode == "library-wiki" 
            else PROJECT_DIRECTORIES
        )
        for subdir in dirs_to_create:
            (project.path / subdir).mkdir()

        # Save config
        self._save_config(project)

        # Create concept.md
        self._create_concept_file(project)

        # Create .memory files
        self._create_memory_files(project)

        # Set as current
        self.set_current(project.slug)

        return project

    def get(self, slug: str) -> Project:
        """
        Get a project by slug.

        Args:
            slug: Project slug.

        Returns:
            Project entity.

        Raises:
            ProjectNotFoundError: If project not found.
        """
        path = self.projects_dir / slug
        if not path.exists():
            raise ProjectNotFoundError(f"Project '{slug}' not found.")

        config_path = path / "project.json"
        if not config_path.exists():
            raise ProjectNotFoundError(f"Project '{slug}' has no configuration file.")

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Project.from_dict(data, path)

    def list_all(self) -> List[Project]:
        """List all projects."""
        projects: List[Project] = []
        if not self.projects_dir.exists():
            return projects

        for path in self.projects_dir.iterdir():
            if path.is_dir() and (path / "project.json").exists():
                try:
                    projects.append(self.get(path.name))
                except Exception:  # nosec B110 - skip corrupted projects
                    pass

        return projects

    def update(self, project: Project) -> Project:
        """Update an existing project."""
        if not project.path.exists():
            raise ProjectNotFoundError(f"Project '{project.slug}' not found.")

        project.updated_at = datetime.now()
        self._save_config(project)
        return project

    def delete(self, slug: str):
        """Delete a project."""
        import shutil

        path = self.projects_dir / slug
        if path.exists():
            shutil.rmtree(path)

    def get_current(self) -> Optional[Project]:
        """Get the currently active project."""
        if not self._current_project_file.exists():
            return None

        slug = self._current_project_file.read_text().strip()
        if not slug:
            return None

        try:
            return self.get(slug)
        except ProjectNotFoundError:
            return None

    def set_current(self, slug: str):
        """Set the current project."""
        self._current_project_file.write_text(slug)

    def _save_config(self, project: Project):
        """Save project configuration."""
        config_path = project.path / "project.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(project.to_dict(), f, indent=2, ensure_ascii=False)

    def _create_concept_file(self, project: Project):
        """Create initial concept.md file."""
        template = self._get_seed_document_template(project.paper_type, project.workflow_mode)
        concept_path = project.path / "concept.md"
        concept_path.write_text(template, encoding="utf-8")

    def _create_memory_files(self, project: Project):
        """Create .memory files."""
        memory_manager = ProjectMemoryManager(project.path)
        memory_manager.create_memory_files(
            project_name=project.name,
            paper_type=project.paper_type,
            interaction_preferences=project.interaction_preferences,
            memo=project.memo,
            workflow_mode=project.workflow_mode,
        )

    def _get_seed_document_template(self, paper_type: str, workflow_mode: str) -> str:
        """Get the initial workspace document based on workflow mode."""
        if workflow_mode == "library-wiki":
            return self._get_library_workspace_template()
        return self._get_concept_template(paper_type)

    def _get_concept_template(self, paper_type: str) -> str:
        """Get concept template based on paper type."""
        type_info = PAPER_TYPES.get(paper_type, {})

        template = (
            """# Research Concept

## 🔒 NOVELTY STATEMENT
<!-- What makes this research unique? This section is PROTECTED. -->


## 🔒 KEY SELLING POINTS
<!-- 3-5 core differentiators. This section is PROTECTED. -->
1.
2.
3.

## 📝 Background
<!-- Research background and clinical significance -->


## 📝 Research Gap
<!-- What gap in the literature does this address? -->


## 📝 Research Question
<!-- Primary and secondary research questions -->


## 📝 Methods Overview
<!-- Brief description of study design and methods -->


## 📝 Expected Outcomes
<!-- What results do you expect? -->


## 🔒 Author Notes
<!-- Private notes (will not be included in the paper) -->


---
*Template for: """
            + str(type_info.get("name", "Research Paper"))
            + """*
"""
        )
        return template

    def _get_library_workspace_template(self) -> str:
        """Get the library/wiki workspace seed document."""
        return """# Library Workspace

## Scope
<!-- What literature domain, corpus, or topic family should this workspace cover? -->

## Intake Priorities
<!-- Which papers, sources, or feeds should be ingested first? -->

## Reading Queues
- Inbox
- Active reading
- Synthesis targets

## Knowledge Threads
<!-- Themes, methods, interventions, datasets, or claims to connect across notes -->

## Open Questions
<!-- Retrieval questions the agent should answer from the library -->

## Optional Manuscript Paths
<!-- If a paper idea emerges later, outline it here before switching workflow_mode -->

## Author Notes
<!-- Private notes for curation strategy, dashboards, or follow-up tasks -->
"""
