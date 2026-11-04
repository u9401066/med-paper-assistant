"""Current-project state, switching, and Foam integration for ProjectManager."""

from typing import TYPE_CHECKING, Any, Dict, Optional, cast

import structlog

if TYPE_CHECKING:
    from ._manager import ProjectManager

from ..state_io import atomic_write_text

logger = structlog.get_logger()


class ProjectSwitchMixin:
    """Track and change the active project, keeping Foam settings aligned."""

    def switch_project(self, slug: str) -> Dict[str, Any]:
        """
        Switch to an existing project.

        Also updates Foam settings to isolate this project's references
        from other projects.

        Args:
            slug: Project slug (directory name).

        Returns:
            Project info or error.
        """
        return self.set_current_project(slug, refresh_foam=True)

    def set_current_project(self, slug: str, *, refresh_foam: bool = False) -> Dict[str, Any]:
        """Set the active project and optionally refresh Foam integration."""
        try:
            slug, project_path = self._project_path_for_slug(slug)
        except ValueError as exc:
            return {"success": False, "error": f"Invalid project slug: {exc}"}

        if not project_path.exists():
            available = self.list_projects()
            return {
                "success": False,
                "error": f"Project '{slug}' not found.",
                "available_projects": [p["slug"] for p in available.get("projects", [])],
            }

        self._save_current_project(slug)

        project_info = self.get_project_info(slug)

        if not refresh_foam:
            return project_info

        # Update Foam settings for project isolation
        foam_result = self._update_foam_settings(slug)
        graph_result = self._refresh_foam_graph()

        # Add Foam update info
        if foam_result.get("success"):
            project_info["foam_isolation"] = {
                "enabled": True,
                "ignored_projects": foam_result.get("ignored_projects", []),
            }
            project_info["foam_views"] = foam_result.get("graph_views", [])

        if graph_result.get("success"):
            project_info["foam_graph"] = graph_result

        return project_info

    def get_current_project(self) -> Optional[str]:
        """Get the slug of the currently active project."""
        if not self.state_file.exists():
            return None

        try:
            return self.state_file.read_text(encoding="utf-8").strip() or None
        except Exception:
            logger.debug("Failed to read current project state", exc_info=True)
            return None

    def _save_current_project(self, slug: str) -> None:
        """Save current project to .current_project file."""
        atomic_write_text(self.state_file, slug)

    def _update_foam_settings(self, slug: str) -> Dict[str, Any]:
        """
        Update Foam VS Code settings for project isolation.

        Args:
            slug: Current project slug.

        Returns:
            Result of Foam settings update.
        """
        try:
            from ...services.foam_settings import FoamSettingsManager

            # workspace_root is parent of projects_dir
            workspace_root = self.projects_dir.parent
            foam_manager = FoamSettingsManager(workspace_root)
            return foam_manager.update_for_project(slug)
        except Exception as e:
            # Non-fatal: log but don't fail the switch
            logger.warning("Foam settings update failed", error=str(e))
            return {"success": False, "error": str(e)}

    def _refresh_foam_graph(self) -> Dict[str, Any]:
        """Refresh Foam-facing graph nodes and index for the active project."""
        try:
            from ..reference_manager import ReferenceManager

            ref_manager = ReferenceManager(project_manager=cast("ProjectManager", self))
            stats = ref_manager.refresh_foam_graph()
            return {"success": True, **stats}
        except Exception as e:
            logger.warning("Foam graph refresh failed", error=str(e))
            return {"success": False, "error": str(e)}
