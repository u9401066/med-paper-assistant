"""Project status, settings, authors, and paper-type access for ProjectManager."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Union

from ....domain.paper_types import (
    PAPER_TYPES,
    get_paper_type_dict,
    is_valid_paper_type,
    list_paper_types,
)
from ....shared.constants import DEFAULT_WORKFLOW_MODE, WORKFLOW_MODES
from ..project_memory_manager import ProjectMemoryManager


class _SettingsTarget(NamedTuple):
    slug: str
    project_path: Path
    config: Dict[str, Any]


def _resolve_settings_target(
    manager: Any, slug: Optional[str]
) -> Union[_SettingsTarget, Dict[str, Any]]:
    """Resolve the project to update, or return an error result."""
    if slug is None:
        slug = manager.get_current_project()
        if slug is None:
            return {"success": False, "error": "No project selected"}

    try:
        slug, project_path = manager._project_path_for_slug(slug)
    except ValueError as exc:
        return {"success": False, "error": f"Invalid project slug: {exc}"}
    config = manager._load_config(project_path)

    if config is None:
        return {"success": False, "error": f"Project '{slug}' not found"}

    return _SettingsTarget(slug, project_path, config)


def _apply_validated_fields(
    manager: Any,
    project_path: Path,
    config: Dict[str, Any],
    paper_type: Optional[str],
    workflow_mode: Optional[str],
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    """Apply paper-type/workflow-mode updates; the first element is an error result if invalid."""
    updated_fields: List[str] = []

    # Validate and update paper type
    if paper_type is not None:
        if not is_valid_paper_type(paper_type):
            return {
                "success": False,
                "error": f"Invalid paper type '{paper_type}'. Valid types: {list_paper_types()}",
            }, updated_fields
        config["paper_type"] = paper_type
        config["paper_type_info"] = get_paper_type_dict(paper_type)
        updated_fields.append("paper_type")

    if workflow_mode is not None:
        if workflow_mode not in WORKFLOW_MODES:
            return {
                "success": False,
                "error": f"Invalid workflow mode '{workflow_mode}'. Valid modes: {list(WORKFLOW_MODES)}",
            }, updated_fields
        config["workflow_mode"] = workflow_mode
        config["workflow_mode_info"] = WORKFLOW_MODES[workflow_mode]
        for subdir in manager._directories_for_workflow(workflow_mode):
            (project_path / subdir).mkdir(exist_ok=True)
        updated_fields.append("workflow_mode")

    return None, updated_fields


def _apply_plain_fields(
    config: Dict[str, Any],
    target_journal: Optional[str],
    interaction_preferences: Optional[Dict[str, Any]],
    memo: Optional[str],
    authors: Optional[List[str]],
    description: Optional[str],
    settings: Optional[Dict[str, Any]],
) -> List[str]:
    """Apply the fields that need no validation and return the names that changed."""
    updated_fields: List[str] = []

    # Update other fields
    if target_journal is not None:
        config["target_journal"] = target_journal
        updated_fields.append("target_journal")

    if interaction_preferences is not None:
        existing_prefs = config.get("interaction_preferences", {})
        existing_prefs.update(interaction_preferences)
        config["interaction_preferences"] = existing_prefs
        updated_fields.append("interaction_preferences")

    if memo is not None:
        config["memo"] = memo
        updated_fields.append("memo")

    if authors is not None:
        config["authors"] = authors
        updated_fields.append("authors")

    if description is not None:
        config["description"] = description
        updated_fields.append("description")

    # Update generic settings dict (e.g., citation_style)
    if settings is not None:
        existing_settings = config.get("settings", {})
        existing_settings.update(settings)
        config["settings"] = existing_settings
        updated_fields.append("settings")

    return updated_fields


def _sync_memory_files(
    target: _SettingsTarget,
    paper_type: Optional[str],
    workflow_mode: Optional[str],
    interaction_preferences: Optional[Dict[str, Any]],
    memo: Optional[str],
) -> None:
    """Refresh the project memory files after a settings update."""
    slug, project_path, config = target
    if workflow_mode is not None or paper_type is not None:
        memory_manager = ProjectMemoryManager(project_path)
        memory_manager.create_memory_files(
            project_name=config.get("name", slug),
            paper_type=config.get("paper_type", ""),
            workflow_mode=config.get("workflow_mode", DEFAULT_WORKFLOW_MODE),
            interaction_preferences=config.get("interaction_preferences", {}),
            memo=config.get("memo", ""),
        )
    elif interaction_preferences is not None or memo is not None:
        memory_manager = ProjectMemoryManager(project_path)
        memory_manager.update_preferences(
            config.get("interaction_preferences", {}), config.get("memo", "")
        )


def _settings_result(manager: Any, slug: str, updated_fields: List[str]) -> Dict[str, Any]:
    foam_result = None
    if slug == manager.get_current_project():
        foam_result = manager._update_foam_settings(slug)

    result = {
        "success": True,
        "message": "Project settings updated successfully",
        "slug": slug,
        "updated_fields": updated_fields,
    }
    if foam_result and foam_result.get("success"):
        result["foam_views"] = foam_result.get("graph_views", [])
    return result


def _apply_settings(
    manager: Any,
    target: _SettingsTarget,
    paper_type: Optional[str],
    workflow_mode: Optional[str],
    target_journal: Optional[str],
    interaction_preferences: Optional[Dict[str, Any]],
    memo: Optional[str],
    authors: Optional[List[str]],
    description: Optional[str],
    settings: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    slug, project_path, config = target

    error, updated_fields = _apply_validated_fields(
        manager, project_path, config, paper_type, workflow_mode
    )
    if error is not None:
        return error

    updated_fields += _apply_plain_fields(
        config, target_journal, interaction_preferences, memo, authors, description, settings
    )

    config["updated_at"] = datetime.now().isoformat()
    manager._save_config(project_path, config)

    _sync_memory_files(target, paper_type, workflow_mode, interaction_preferences, memo)
    return _settings_result(manager, slug, updated_fields)


class ProjectSettingsMixin:
    """Update project status, settings, and authors; expose paper types."""

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

        if status not in self.VALID_STATUSES:
            return {
                "success": False,
                "error": f"Invalid status. Must be one of: {self.VALID_STATUSES}",
            }

        try:
            slug, project_path = self._project_path_for_slug(slug)
        except ValueError as exc:
            return {"success": False, "error": f"Invalid project slug: {exc}"}
        config = self._load_config(project_path)

        if config is None:
            return {"success": False, "error": f"Project '{slug}' not found"}

        config["status"] = status
        config["updated_at"] = datetime.now().isoformat()
        self._save_config(project_path, config)

        return {"success": True, "message": f"Project status updated to '{status}'", "slug": slug}

    def update_project_settings(
        self,
        slug: Optional[str] = None,
        paper_type: Optional[str] = None,
        workflow_mode: Optional[str] = None,
        target_journal: Optional[str] = None,
        interaction_preferences: Optional[Dict[str, Any]] = None,
        memo: Optional[str] = None,
        authors: Optional[List[str]] = None,
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update project settings.

        Args:
            slug: Project slug. If None, uses current project.
            paper_type: Type of paper.
            workflow_mode: Project workflow mode.
            target_journal: Target journal.
            interaction_preferences: User preferences for AI interaction.
            memo: Additional notes.
            authors: Author list.
            description: Project description.
            settings: Additional settings dict (e.g., citation_style).

        Returns:
            Updated project info.
        """
        target = _resolve_settings_target(self, slug)
        if isinstance(target, dict):
            return target

        return _apply_settings(
            self,
            target,
            paper_type,
            workflow_mode,
            target_journal,
            interaction_preferences,
            memo,
            authors,
            description,
            settings,
        )

    def update_authors(self, authors: List[Any], slug: Optional[str] = None) -> Dict[str, Any]:
        """Update the authors list for a project.

        Args:
            authors: List of author dicts or strings.
            slug: Project slug (uses current if None).

        Returns:
            Success/error dict.
        """
        if slug is None:
            slug = self.get_current_project()
            if slug is None:
                return {"success": False, "error": "No project selected."}

        try:
            slug, project_path = self._project_path_for_slug(slug)
        except ValueError as exc:
            return {"success": False, "error": f"Invalid project slug: {exc}"}
        config = self._load_config(project_path)
        if config is None:
            return {"success": False, "error": f"Project '{slug}' not found."}

        config["authors"] = self._normalize_authors(authors)
        config["updated_at"] = datetime.now().isoformat()
        self._save_config(project_path, config)

        return {
            "success": True,
            "authors": config["authors"],
            "message": f"Updated {len(config['authors'])} author(s).",
        }

    def get_paper_types(self) -> Dict[str, Dict[str, Any]]:
        """Return available paper types and their info."""
        return {k: v.to_dict() for k, v in PAPER_TYPES.items()}
