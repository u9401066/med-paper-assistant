"""Project creation and deletion for ProjectManager."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from ....domain.paper_types import is_valid_paper_type, list_paper_types
from ....shared.constants import DEFAULT_WORKFLOW_MODE, WORKFLOW_MODES
from ..project_memory_manager import ProjectMemoryManager


def _creation_input_error(paper_type: str, workflow_mode: str) -> Optional[Dict[str, Any]]:
    """Return an error result when the requested paper type or workflow mode is invalid."""
    if paper_type and not is_valid_paper_type(paper_type):
        return {
            "success": False,
            "error": f"Invalid paper type '{paper_type}'. Valid types: {list_paper_types()}",
        }

    if workflow_mode not in WORKFLOW_MODES:
        return {
            "success": False,
            "error": f"Invalid workflow mode '{workflow_mode}'. Valid modes: {list(WORKFLOW_MODES)}",
        }

    return None


def _write_project_documents(
    manager: Any,
    project_path: Path,
    name: str,
    paper_type: str,
    target_journal: str,
    memo: str,
    workflow_mode: str,
    interaction_preferences: Optional[Dict[str, Any]],
) -> None:
    """Write the seed document and memory files of a new project."""
    # Create concept.md or library workspace seed
    seed_content = manager._build_workspace_seed_document(
        project_name=name,
        paper_type=paper_type,
        target_journal=target_journal,
        memo=memo,
        workflow_mode=workflow_mode,
    )
    (project_path / "concept.md").write_text(seed_content, encoding="utf-8")

    # Create memory files
    memory_manager = ProjectMemoryManager(project_path)
    memory_manager.create_memory_files(
        project_name=name,
        paper_type=paper_type,
        workflow_mode=workflow_mode,
        interaction_preferences=interaction_preferences,
        memo=memo,
    )


def _materialize_project(
    manager: Any,
    slug: str,
    project_path: Path,
    name: str,
    description: str,
    authors: Optional[List[Any]],
    target_journal: str,
    paper_type: str,
    workflow_mode: str,
    interaction_preferences: Optional[Dict[str, Any]],
    memo: str,
) -> None:
    """Create the project on disk, make it current, and refresh Foam integration."""
    # Create directory structure
    project_path.mkdir(parents=True)
    for subdir in manager._directories_for_workflow(workflow_mode):
        (project_path / subdir).mkdir()

    # Create project config
    project_config = manager._create_project_config(
        name,
        slug,
        description,
        authors,
        target_journal,
        paper_type,
        workflow_mode,
        interaction_preferences,
        memo,
    )
    manager._save_config(project_path, project_config)

    _write_project_documents(
        manager,
        project_path,
        name,
        paper_type,
        target_journal,
        memo,
        workflow_mode,
        interaction_preferences,
    )

    # Set as current project
    manager._save_current_project(slug)

    # Update Foam settings immediately so named views and graph scope exist
    manager._update_foam_settings(slug)
    manager._refresh_foam_graph()


def _creation_result(
    manager: Any, name: str, slug: str, project_path: Path, workflow_mode: str
) -> Dict[str, Any]:
    return {
        "success": True,
        "message": f"Project '{name}' created successfully!",
        "slug": slug,
        "path": str(project_path),
        "workflow_mode": workflow_mode,
        "structure": manager._build_structure_paths(project_path, workflow_mode),
    }


class ProjectLifecycleMixin:
    """Create and delete research paper projects."""

    def create_project(
        self,
        name: str,
        description: str = "",
        authors: Optional[List[Any]] = None,
        target_journal: str = "",
        paper_type: str = "",
        workflow_mode: str = DEFAULT_WORKFLOW_MODE,
        interaction_preferences: Optional[Dict[str, Any]] = None,
        memo: str = "",
    ) -> Dict[str, Any]:
        """
        Create a new research paper project.

        Args:
            name: Human-readable project name.
            description: Brief description of the research.
            authors: List of author names.
            target_journal: Target journal for submission.
            paper_type: Type of paper (original-research, meta-analysis, etc.)
            workflow_mode: Workflow mode (manuscript or library-wiki).
            interaction_preferences: User preferences for AI interaction.
            memo: Additional notes and reminders.

        Returns:
            Project info dictionary.
        """
        slug = self._make_unique_slug(name)
        slug, project_path = self._project_path_for_slug(slug)

        error = _creation_input_error(paper_type, workflow_mode)
        if error is not None:
            return error

        _materialize_project(
            self,
            slug,
            project_path,
            name,
            description,
            authors,
            target_journal,
            paper_type,
            workflow_mode,
            interaction_preferences,
            memo,
        )
        return _creation_result(self, name, slug, project_path, workflow_mode)

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
                "error": "Deletion requires confirm=True. This will permanently delete all project data!",
            }

        try:
            slug, project_path = self._project_path_for_slug(slug)
        except ValueError as exc:
            return {"success": False, "error": f"Invalid project slug: {exc}"}

        if not project_path.exists():
            return {"success": False, "error": f"Project '{slug}' not found"}
        if not (project_path / "project.json").exists():
            return {
                "success": False,
                "error": f"Project '{slug}' is missing project.json; refusing deletion.",
            }

        import shutil

        shutil.rmtree(project_path)

        # Clear current if this was the current project
        if self.get_current_project() == slug:
            if self.state_file.exists():
                self.state_file.unlink()

        return {"success": True, "message": f"Project '{slug}' deleted permanently."}
