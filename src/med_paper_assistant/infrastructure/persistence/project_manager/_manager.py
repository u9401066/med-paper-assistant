"""ProjectManager composed from concern-specific mixins."""

from pathlib import Path

from ....shared.workspace_root import resolve_workspace_root
from ...services.concept_template_reader import ConceptTemplateReader
from ._constants import PROJECT_STATE_FILE, PROJECT_STATUSES, TEMP_EXPLORATION_SLUG
from ._exploration import ExplorationMixin
from ._layout import ProjectLayoutMixin
from ._lifecycle import ProjectLifecycleMixin
from ._queries import ProjectQueryMixin
from ._settings import ProjectSettingsMixin
from ._switching import ProjectSwitchMixin
from ._templates import WorkspaceTemplateMixin


class ProjectManager(
    ProjectLayoutMixin,
    WorkspaceTemplateMixin,
    ProjectQueryMixin,
    ProjectSwitchMixin,
    ProjectLifecycleMixin,
    ProjectSettingsMixin,
    ExplorationMixin,
):
    """
    Manages multiple research paper projects with isolated directory structures.

    Each project has:
    - project.json: metadata and settings
    - concept.md: research concept
    - .memory/: project-specific AI memory (activeContext.md, progress.md)
    - drafts/: paper drafts
    - references/: saved references (by PMID)
    - data/: analysis data files
    - results/: exported documents
    - exports/: final DOCX/PDF/submission artifacts

    Special project:
    - temp_project: A temporary workspace for literature exploration before
                    committing to a formal project. Can be converted to a
                    real project with all saved references preserved.
    """

    # Subdirectories for each project

    # Current project state file
    STATE_FILE = PROJECT_STATE_FILE

    # Valid project statuses
    VALID_STATUSES = PROJECT_STATUSES

    # Temporary project for exploration
    TEMP_PROJECT_SLUG = TEMP_EXPLORATION_SLUG

    def __init__(self, base_path: str | None = None):
        """
        Initialize ProjectManager.

        Args:
            base_path: Base directory for the med-paper-assistant workspace.
                       Falls back to ``resolve_workspace_root()``.
        """
        self.base_path = (
            Path(base_path).resolve() if base_path is not None else resolve_workspace_root()
        )
        self.projects_dir = self.base_path / "projects"
        self.state_file = self.base_path / self.STATE_FILE

        # Initialize helpers
        self.template_reader = ConceptTemplateReader()

        # Ensure projects directory exists
        self.projects_dir.mkdir(parents=True, exist_ok=True)
