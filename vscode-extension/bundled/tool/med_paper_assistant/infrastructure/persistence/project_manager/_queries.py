"""Read-only project queries and content statistics for ProjectManager."""

from pathlib import Path
from typing import Any, Dict, Optional

from ....shared.constants import DEFAULT_WORKFLOW_MODE


class ProjectQueryMixin:
    """Project info, listing, and per-project content statistics."""

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
                    "error": "No project selected. Use create_project or switch_project first.",
                }

        try:
            slug, project_path = self._project_path_for_slug(slug)
        except ValueError as exc:
            return {"success": False, "error": f"Invalid project slug: {exc}"}
        config = self._load_config(project_path)

        if config is None:
            return {"success": False, "error": f"Project '{slug}' not found or corrupted."}

        # Count contents
        stats = self._get_project_stats(project_path)

        return {
            "success": True,
            "slug": slug,
            "is_current": slug == self.get_current_project(),
            **config,
            "project_path": str(project_path),
            "paths": self.get_project_paths(slug),
            "stats": stats,
        }

    def list_projects(self) -> Dict[str, Any]:
        """List all projects."""
        projects = []
        current = self.get_current_project()

        if not self.projects_dir.exists():
            return {"projects": [], "current": None, "count": 0}

        for project_dir in sorted(self.projects_dir.iterdir()):
            if not project_dir.is_dir():
                continue

            config = self._load_config(project_dir)
            if config is None:
                projects.append(
                    {
                        "slug": project_dir.name,
                        "name": project_dir.name,
                        "status": "error",
                        "is_current": project_dir.name == current,
                    }
                )
            else:
                projects.append(
                    {
                        "slug": project_dir.name,
                        "name": config.get("name", project_dir.name),
                        "status": config.get("status", "unknown"),
                        "paper_type": config.get("paper_type", ""),
                        "workflow_mode": config.get("workflow_mode", DEFAULT_WORKFLOW_MODE),
                        "created_at": config.get("created_at", ""),
                        "is_current": project_dir.name == current,
                    }
                )

        return {"projects": projects, "current": current, "count": len(projects)}

    def _get_project_stats(self, project_path: Path) -> Dict[str, int]:
        """Get project content statistics."""
        stats = {}

        # Manuscript mode stats
        if (project_path / "drafts").exists():
            stats["drafts"] = len(list((project_path / "drafts").glob("*.md")))
        if (project_path / "data").exists():
            stats["data_files"] = len(list((project_path / "data").glob("*.*")))

        # Library mode stats
        if (project_path / "inbox").exists():
            stats["inbox"] = len(list((project_path / "inbox").glob("*.md")))
        if (project_path / "concepts").exists():
            stats["concepts"] = len(list((project_path / "concepts").glob("*.md")))
        if (project_path / "projects").exists():
            stats["projects"] = len(list((project_path / "projects").glob("*.md")))
        if (project_path / "review").exists():
            stats["review"] = len(list((project_path / "review").glob("*.md")))
        if (project_path / "daily").exists():
            stats["daily"] = len(list((project_path / "daily").glob("*.md")))

        # Common stats
        if (project_path / "references").exists():
            stats["references"] = len(
                [d for d in (project_path / "references").iterdir() if d.is_dir()]
            )
        else:
            stats["references"] = 0

        return stats
