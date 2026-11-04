"""Temporary exploration workspace operations for ProjectManager."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ....shared.constants import WORKFLOW_MODES
from ._constants import (
    TEMP_PROJECT_CREATED_MESSAGE,
    TEMP_PROJECT_DESCRIPTION,
    TEMP_PROJECT_MEMO,
    TEMP_PROJECT_SEED_MEMO,
)
from ._conversion import execute_conversion, finish_conversion, plan_conversion


def _existing_temp_project(manager: Any, temp_path: Path) -> Optional[Dict[str, Any]]:
    """Return the info of an existing exploration workspace, or None if it has no config."""
    for subdir in manager._directories_for_workflow("library-wiki"):
        (temp_path / subdir).mkdir(exist_ok=True)
    # Return existing temp project info
    config = manager._load_config(temp_path)
    if not config:
        return None

    stats = manager._get_project_stats(temp_path)
    return {
        "success": True,
        "slug": manager.TEMP_PROJECT_SLUG,
        "is_temp": True,
        "message": "Using existing exploration workspace",
        "paths": manager.get_project_paths(manager.TEMP_PROJECT_SLUG),
        "stats": stats,
        **config,
    }


def _temp_project_config(slug: str) -> Dict[str, Any]:
    """Build the minimal config of the exploration workspace."""
    return {
        "name": "Literature Exploration",
        "slug": slug,
        "description": TEMP_PROJECT_DESCRIPTION,
        "authors": [],
        "target_journal": "",
        "paper_type": "",
        "paper_type_info": {},
        "workflow_mode": "library-wiki",
        "workflow_mode_info": WORKFLOW_MODES["library-wiki"],
        "interaction_preferences": {},
        "memo": TEMP_PROJECT_MEMO,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "status": "exploration",
        "is_temp": True,
    }


def _create_temp_project(manager: Any, temp_path: Path) -> Dict[str, Any]:
    """Create the exploration workspace and make it the current project."""
    temp_path.mkdir(parents=True)
    for subdir in manager._directories_for_workflow("library-wiki"):
        (temp_path / subdir).mkdir(exist_ok=True)

    # Create minimal config
    manager._save_config(temp_path, _temp_project_config(manager.TEMP_PROJECT_SLUG))

    # Create library-oriented workspace seed
    concept_content = manager._build_library_workspace_seed(
        "Literature Exploration",
        TEMP_PROJECT_SEED_MEMO,
    )
    (temp_path / "concept.md").write_text(concept_content, encoding="utf-8")

    # Set as current project
    manager._save_current_project(manager.TEMP_PROJECT_SLUG)

    return {
        "success": True,
        "slug": manager.TEMP_PROJECT_SLUG,
        "is_temp": True,
        "message": TEMP_PROJECT_CREATED_MESSAGE,
        "paths": manager.get_project_paths(manager.TEMP_PROJECT_SLUG),
        "stats": {
            "references": 0,
            "inbox": 0,
            "concepts": 0,
            "projects": 0,
            "review": 0,
            "daily": 0,
        },
    }


class ExplorationMixin:
    """Create and convert the temporary literature-exploration workspace."""

    def get_or_create_temp_project(self) -> Dict[str, Any]:
        """
        Get or create the temporary exploration project.

        This project is for users who want to explore literature before
        committing to a formal research project. All saved references and
        notes are preserved and can be converted to a real project.

        Returns:
            Temp project info dictionary.
        """
        temp_path = self.projects_dir / self.TEMP_PROJECT_SLUG

        if temp_path.exists():
            existing = _existing_temp_project(self, temp_path)
            if existing is not None:
                return existing

        return _create_temp_project(self, temp_path)

    def is_temp_project_active(self) -> bool:
        """Check if the temp project is currently active."""
        return self.get_current_project() == self.TEMP_PROJECT_SLUG

    def convert_temp_to_project(
        self,
        name: str,
        description: str = "",
        paper_type: str = "",
        workflow_mode: str = "",
        target_journal: str = "",
        keep_temp: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert the temporary exploration project to a formal project.

        All references, drafts, data, and notes are moved to the new project.

        Args:
            name: Name for the new project (in English for slug generation).
            description: Project description.
            paper_type: Type of paper.
            workflow_mode: Workflow mode for the converted project.
            target_journal: Target journal.
            keep_temp: If True, copy instead of move (keep temp project).

        Returns:
            New project info or error.
        """
        plan = plan_conversion(self, name, paper_type, workflow_mode)
        if isinstance(plan, dict):
            return plan

        error = execute_conversion(
            self, plan, name, description, paper_type, target_journal, keep_temp
        )
        if error is not None:
            return error

        return finish_conversion(self, plan, name)

    def ensure_project_for_references(self) -> Dict[str, Any]:
        """
        Ensure there's a project available for saving references.

        If no project is active, automatically creates/activates the temp project.
        This allows users to explore literature without first creating a formal project.

        Returns:
            Current project info (either existing or newly created temp).
        """
        current = self.get_current_project()

        if current:
            # Project already active
            return self.get_project_info(current)

        # No project active - use temp project
        return self.get_or_create_temp_project()
