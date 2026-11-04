"""Directory layout, slug handling, and ``project.json`` I/O for ProjectManager."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from ....shared.constants import (
    DEFAULT_WORKFLOW_MODE,
    LIBRARY_DIRECTORIES,
    PROJECT_DIRECTORIES,
)
from ....shared.path_guard import normalize_relative_filename, resolve_child_path
from ....shared.slug import slugify_name
from ..state_io import atomic_write_text

logger = structlog.get_logger()


class ProjectLayoutMixin:
    """Mode-aware directory layout, slug resolution, and config file access."""

    def _directories_for_workflow(self, workflow_mode: str) -> List[str]:
        """Return the directory layout for a workflow mode."""
        return LIBRARY_DIRECTORIES if workflow_mode == "library-wiki" else PROJECT_DIRECTORIES

    def _build_structure_paths(self, project_path: Path, workflow_mode: str) -> Dict[str, str]:
        """Build mode-aware path mappings for a project."""
        paths = {
            "root": str(project_path),
            "concept": str(project_path / "concept.md"),
            "audit": str(project_path / ".audit"),
            "memory": str(project_path / ".memory"),
            "references": str(project_path / "references"),
            "config": str(project_path / "project.json"),
        }

        if workflow_mode == "library-wiki":
            paths.update(
                {
                    "inbox": str(project_path / "inbox"),
                    "concepts": str(project_path / "concepts"),
                    "projects": str(project_path / "projects"),
                    "review": str(project_path / "review"),
                    "daily": str(project_path / "daily"),
                }
            )
        else:
            paths.update(
                {
                    "drafts": str(project_path / "drafts"),
                    "data": str(project_path / "data"),
                    "results": str(project_path / "results"),
                    "exports": str(project_path / "exports"),
                }
            )

        return paths

    def _normalize_project_slug(self, slug: str) -> str:
        return normalize_relative_filename(slug, field_name="project slug")

    def _project_path_for_slug(self, slug: str) -> tuple[str, Path]:
        safe_slug = self._normalize_project_slug(slug)
        return safe_slug, resolve_child_path(
            self.projects_dir, safe_slug, field_name="project slug"
        )

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

        slug, project_path = self._project_path_for_slug(slug)
        config = self._load_config(project_path) or {}
        workflow_mode = config.get("workflow_mode", DEFAULT_WORKFLOW_MODE)

        return self._build_structure_paths(project_path, workflow_mode)

    def _slugify(self, name: str) -> str:
        """Convert project name to URL-safe slug."""
        return slugify_name(name)

    def _make_unique_slug(self, name: str) -> str:
        """Generate a unique slug by appending a counter when needed."""
        slug = self._slugify(name)
        candidate = slug
        counter = 1

        while (self.projects_dir / candidate).exists():
            candidate = f"{slug}-{counter}"
            counter += 1

        return candidate

    def _save_config(self, project_path: Path, config: Dict[str, Any]) -> None:
        """Save project config to JSON file."""
        atomic_write_text(
            project_path / "project.json", json.dumps(config, indent=2, ensure_ascii=False)
        )

    def _load_config(self, project_path: Path) -> Optional[Dict[str, Any]]:
        """Load project config from JSON file."""
        config_path = project_path / "project.json"
        if not config_path.exists():
            return None

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.debug("Failed to load config: %s", config_path, exc_info=True)
            return None
