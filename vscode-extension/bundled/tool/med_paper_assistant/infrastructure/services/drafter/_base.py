"""Drafter state: collaborators, lazy snapshot/git helpers, and citation-style configuration."""

import os
from typing import TYPE_CHECKING, Optional

import structlog

from med_paper_assistant.infrastructure.persistence.draft_snapshot_manager import (
    DraftSnapshotManager,
)
from med_paper_assistant.infrastructure.persistence.git_auto_committer import GitAutoCommitter
from med_paper_assistant.infrastructure.persistence.reference_manager import ReferenceManager

from ._models import CitationStyle

if TYPE_CHECKING:
    from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager

logger = structlog.get_logger(__package__)


class DrafterBase:
    def __init__(
        self,
        reference_manager: ReferenceManager,
        drafts_dir: str = "drafts",
        citation_style: str = CitationStyle.VANCOUVER.value,
        project_manager: Optional["ProjectManager"] = None,
    ):
        """
        Initialize the Drafter.

        Args:
            reference_manager: Instance of ReferenceManager to retrieve citation info.
            drafts_dir: Default directory to store drafts (used if no project active).
            citation_style: Default citation style.
            project_manager: Optional ProjectManager for multi-project support.
        """
        self.ref_manager = reference_manager
        self._default_drafts_dir = drafts_dir
        self.citation_style = citation_style
        self._project_manager = project_manager
        self._snapshot_manager: Optional[DraftSnapshotManager] = None
        self._git_committer: Optional[GitAutoCommitter] = None
        self._git_committer_root: Optional[str] = None
        # Note: Directory is created on-demand when writing drafts,
        # not at initialization to avoid polluting root directory

    @property
    def drafts_dir(self) -> str:
        """
        Get the current drafts directory.
        Uses project directory if a project is active, otherwise default.
        """
        if self._project_manager:
            try:
                paths = self._project_manager.get_project_paths()
                return paths.get("drafts", self._default_drafts_dir)
            except (ValueError, KeyError):
                logger.debug("Project paths unavailable, using default drafts dir")
        return self._default_drafts_dir

    @property
    def snapshot_manager(self) -> DraftSnapshotManager:
        """Lazy-initialized snapshot manager tied to current drafts_dir."""
        drafts = self.drafts_dir
        if self._snapshot_manager is None or str(self._snapshot_manager._drafts_dir) != drafts:
            self._snapshot_manager = DraftSnapshotManager(drafts)
        return self._snapshot_manager

    @property
    def git_committer(self) -> GitAutoCommitter:
        """Lazy-initialized git auto-committer tied to project root."""
        # Use parent of drafts_dir (project root) as the repo dir.
        # This must refresh when the active project changes.
        project_root = os.path.dirname(self.drafts_dir)
        if self._git_committer is None or self._git_committer_root != project_root:
            self._git_committer = GitAutoCommitter(project_root)
            self._git_committer_root = project_root
        return self._git_committer

    def set_citation_style(self, style: str):
        """Set the citation style."""
        # Validate style
        valid_styles = [s.value for s in CitationStyle]
        if style not in valid_styles:
            raise ValueError(f"Invalid style: {style}. Valid options: {valid_styles}")
        self.citation_style = style
