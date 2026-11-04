"""Workspace directories, project root resolution and path normalisation."""

import os
from pathlib import Path

from med_paper_assistant.shared.path_guard import (
    normalize_relative_filename,
    resolve_child_path,
)


class PathsMixin:
    """Workspace directories, project root resolution and path normalisation."""

    def _project_root_dir(self) -> str:
        """Get the current project root or best-effort workspace root."""
        if self._project_manager:
            try:
                paths = self._project_manager.get_project_paths()
                return paths.get("root", os.path.dirname(self.base_dir))
            except (ValueError, KeyError):
                pass

        base_path = Path(self.base_dir).resolve()
        return str(base_path.parent)

    def _normalize_reference_id(
        self, reference_id: str, *, field_name: str = "reference id"
    ) -> str:
        return normalize_relative_filename(reference_id, field_name=field_name)

    def _reference_dir(self, reference_id: str, *, field_name: str = "reference id") -> Path:
        safe_id = self._normalize_reference_id(reference_id, field_name=field_name)
        return resolve_child_path(self.base_dir, safe_id, field_name=field_name)

    def _normalize_citation_key(self, citation_key: str) -> str:
        return normalize_relative_filename(citation_key, field_name="citation key")

    def _citation_note_filename(self, citation_key: str) -> str:
        safe_key = self._normalize_citation_key(citation_key)
        return normalize_relative_filename(
            f"{safe_key}.md",
            field_name="citation filename",
            allowed_suffixes={".md"},
        )

    def _notes_dir(self) -> str:
        return os.path.join(self._project_root_dir(), "notes")

    def _knowledge_maps_dir(self) -> str:
        return os.path.join(self._notes_dir(), "knowledge-maps")

    def _synthesis_pages_dir(self) -> str:
        return os.path.join(self._notes_dir(), "synthesis-pages")

    def _draft_section_notes_dir(self) -> str:
        return os.path.join(self._notes_dir(), "draft-sections")

    def _figure_notes_dir(self) -> str:
        return os.path.join(self._notes_dir(), "figures")

    def _table_notes_dir(self) -> str:
        return os.path.join(self._notes_dir(), "tables")

    def _context_notes_dir(self) -> str:
        return os.path.join(self._notes_dir(), "context")

    def _library_pages_dir(self) -> str:
        return os.path.join(self._notes_dir(), "library")

    def _publish_notes_dir(self) -> str:
        return os.path.join(self._notes_dir(), "publish")

    def _current_project_slug(self) -> str:
        if self._project_manager:
            try:
                slug = self._project_manager.get_current_project()
                if slug:
                    return str(slug)
            except Exception:  # nosec B110
                pass
        return Path(self._project_root_dir()).name

    def _registry_dir(self) -> str:
        return os.path.join(self._project_root_dir(), "registry")

    def _hash_registry_path(self) -> str:
        return os.path.join(self._registry_dir(), "by-hash.json")

    def _pmid_registry_path(self) -> str:
        return os.path.join(self._registry_dir(), "by-pmid.json")

    def _doi_registry_path(self) -> str:
        return os.path.join(self._registry_dir(), "by-doi.json")

    def _ensure_workspace_scaffolding(self) -> None:
        """Create the minimal directories needed for notes and registries."""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self._notes_dir(), exist_ok=True)
        os.makedirs(self._knowledge_maps_dir(), exist_ok=True)
        os.makedirs(self._synthesis_pages_dir(), exist_ok=True)
        os.makedirs(self._draft_section_notes_dir(), exist_ok=True)
        os.makedirs(self._figure_notes_dir(), exist_ok=True)
        os.makedirs(self._table_notes_dir(), exist_ok=True)
        os.makedirs(self._context_notes_dir(), exist_ok=True)
        os.makedirs(self._library_pages_dir(), exist_ok=True)
        os.makedirs(self._publish_notes_dir(), exist_ok=True)
        os.makedirs(self._registry_dir(), exist_ok=True)

    @property
    def base_dir(self) -> str:
        """
        Get the current references directory.
        Uses project directory if a project is active, otherwise default.
        """
        if self._project_manager:
            try:
                paths = self._project_manager.get_project_paths()
                return paths.get("references", self._default_base_dir)
            except (ValueError, KeyError):
                pass
        return self._default_base_dir
