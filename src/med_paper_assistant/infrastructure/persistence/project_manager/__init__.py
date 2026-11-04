"""
Project Manager - Multi-project support for MedPaper Assistant

Manages separate workspaces for different research papers, each with its own:
- concept.md
- drafts/
- references/
- data/
- results/
"""

import json  # noqa: F401
from datetime import datetime  # noqa: F401
from pathlib import Path  # noqa: F401
from typing import Any, Dict, List, Optional  # noqa: F401

import structlog

from ....domain.paper_types import (  # noqa: F401
    PAPER_TYPES,
    get_paper_type_dict,
    is_valid_paper_type,
    list_paper_types,
)
from ....shared.constants import (  # noqa: F401
    DEFAULT_WORKFLOW_MODE,
    LIBRARY_DIRECTORIES,
    PROJECT_DIRECTORIES,
    WORKFLOW_MODES,
)
from ....shared.path_guard import normalize_relative_filename, resolve_child_path  # noqa: F401
from ....shared.slug import slugify_name  # noqa: F401
from ....shared.workspace_root import resolve_workspace_root  # noqa: F401
from ...services.concept_template_reader import ConceptTemplateReader  # noqa: F401
from ..project_memory_manager import ProjectMemoryManager  # noqa: F401
from ..project_transfer import transfer_project_tree  # noqa: F401
from ..state_io import atomic_write_text  # noqa: F401
from ._manager import ProjectManager

logger = structlog.get_logger()


# Singleton instance for global access
_project_manager: Optional[ProjectManager] = None


def get_project_manager(base_path: str | None = None) -> ProjectManager:
    """Get or create the global ProjectManager instance.

    Args:
        base_path: Base directory. When None (default), delegates to
                   ProjectManager.__init__ which reads MEDPAPER_BASE_DIR
                   env var then falls back to CWD.  Previous default of "."
                   bypassed the env-var check, causing a dual-instance
                   state bug when MEDPAPER_BASE_DIR != CWD (e.g. VSX).
    """
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager(base_path)
    return _project_manager


def _reset_project_manager() -> None:
    """Reset the singleton (for testing only)."""
    global _project_manager
    _project_manager = None
