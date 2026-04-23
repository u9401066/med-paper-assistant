"""
Project Repository - Persistence for Project entities.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from med_paper_assistant.domain.entities.project import Project
from med_paper_assistant.shared.exceptions import (
    InvalidPaperTypeError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
)
from med_paper_assistant.shared.path_guard import resolve_child_path

from .project_manager import ProjectManager


class ProjectRepository:
    """
    Repository for Project persistence.

    Handles saving, loading, and managing projects on disk.
    """

    def __init__(self, projects_dir: Path):
        self.projects_dir = projects_dir
        self._current_project_file = projects_dir.parent / ".current_project"
        self._project_manager: Optional[ProjectManager] = None
        self._ensure_dir()

    def _get_project_manager(self) -> ProjectManager:
        """Return the shared lifecycle owner for project mutations."""
        if self._project_manager is None:
            manager = ProjectManager(base_path=str(self.projects_dir.parent))
            manager.projects_dir = self.projects_dir
            manager.state_file = self._current_project_file
            self._project_manager = manager
        return self._project_manager

    @staticmethod
    def _raise_create_error(error: str):
        message = error or "Project creation failed."
        lowered = message.lower()

        if "already exists" in lowered:
            raise ProjectAlreadyExistsError(message)
        if "invalid paper type" in lowered:
            raise InvalidPaperTypeError(message)
        raise ValueError(message)

    def _ensure_dir(self):
        """Ensure projects directory exists."""
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def _project_path(self, slug: str) -> Path:
        return resolve_child_path(self.projects_dir, slug, field_name="project slug")

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
        result = self._get_project_manager().create_project(
            name=project.name,
            description=project.description,
            authors=project.authors,
            target_journal=project.target_journal,
            paper_type=project.paper_type,
            workflow_mode=project.workflow_mode,
            interaction_preferences=project.interaction_preferences,
            memo=project.memo,
        )
        if not result.get("success"):
            self._raise_create_error(str(result.get("error", "Project creation failed.")))

        return self.get(str(result["slug"]))

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
        path = self._project_path(slug)
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

        path = self._project_path(slug)
        if path.exists():
            if not (path / "project.json").exists():
                raise ProjectNotFoundError(f"Project '{slug}' has no configuration file.")
            shutil.rmtree(path)

    def get_current(self) -> Optional[Project]:
        """Get the currently active project."""
        slug = self._get_project_manager().get_current_project()
        if not slug:
            return None

        try:
            return self.get(slug)
        except ProjectNotFoundError:
            return None

    def set_current(self, slug: str):
        """Set the current project."""
        result = self._get_project_manager().set_current_project(
            slug,
            refresh_foam=False,
        )
        if not result.get("success"):
            raise ProjectNotFoundError(f"Project '{slug}' not found.")

    def _save_config(self, project: Project):
        """Save project configuration."""
        config_path = project.path / "project.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(project.to_dict(), f, indent=2, ensure_ascii=False)
