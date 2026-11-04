"""Project-aware state file path resolution."""

from pathlib import Path
from typing import Optional

from med_paper_assistant.shared.path_guard import resolve_child_path
from med_paper_assistant.shared.workspace_root import resolve_workspace_root

from . import _models


class ProjectPathsMixin:
    """Resolve the workspace root, current project, and state file locations."""

    STATE_FILE = _models.STATE_FILE

    def __init__(self, base_path: str | None = None):
        """
        Initialize WorkspaceStateManager.

        Args:
            base_path: Base directory for the med-paper-assistant workspace.
        """
        self.base_path = (
            Path(base_path).resolve() if base_path is not None else resolve_workspace_root()
        )
        self.projects_dir = self.base_path / "projects"

    def _project_dir(self, slug: str) -> Path:
        return resolve_child_path(self.projects_dir, slug, field_name="project slug")

    # =========================================================================
    # State File Resolution
    # =========================================================================

    @property
    def state_file(self) -> Path:
        """
        Resolve state file path for the current project.

        Returns project-specific: projects/{slug}/.mdpaper-state.json
        Falls back to root: .mdpaper-state.json (when no project is active)
        """
        slug = self._get_current_project_slug()
        if slug:
            try:
                project_dir = self._project_dir(slug)
            except ValueError:
                project_dir = None
            if project_dir is not None and project_dir.is_dir():
                return project_dir / self.STATE_FILE
        return self.base_path / self.STATE_FILE

    def state_file_for_project(self, slug: str) -> Path:
        """Get state file path for a specific project."""
        return self._project_dir(slug) / self.STATE_FILE

    def _get_current_project_slug(self) -> Optional[str]:
        """Read current project slug from .current_project file."""
        marker = self.base_path / ".current_project"
        try:
            if marker.is_file():
                return marker.read_text(encoding="utf-8").strip() or None
        except OSError:
            pass
        return None

    def get_current_project(self) -> Optional[str]:
        """Get the current project slug (reads from .current_project file)."""
        return self._get_current_project_slug()
