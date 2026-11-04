"""Library wiki note tools for inbox/concepts/projects workflows."""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from med_paper_assistant.infrastructure.persistence import ProjectManager

from ..._binding import register_handlers
from ..._shared import get_optional_tool_decorator
from ..._shared.path_errors import catch_path_errors
from .._deps import PROJECT_MANAGER
from .concepts import create_concept_page, materialize_concept_page
from .dashboard import build_library_dashboard
from .explain import explain_library_path
from .normalize import _resolve_note_path
from .notes import list_library_notes, move_library_note, read_library_note, write_library_note
from .search import search_library_notes, show_reading_queues
from .triage import (
    triage_library_note,
    update_library_note_metadata,
)

LIBRARY_NOTE_HANDLERS = (
    list_library_notes,
    read_library_note,
    write_library_note,
    move_library_note,
    triage_library_note,
    update_library_note_metadata,
    search_library_notes,
    show_reading_queues,
    create_concept_page,
    materialize_concept_page,
    explain_library_path,
    build_library_dashboard,
)


def register_library_note_tools(
    mcp: MCPServer,
    project_manager: ProjectManager,
    *,
    register_public_verbs: bool = True,
) -> dict[str, Any]:
    """Register markdown note tools for library-wiki projects."""

    tool = catch_path_errors(
        get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)
    )
    return register_handlers(tool, PROJECT_MANAGER.bind(project_manager, LIBRARY_NOTE_HANDLERS))


__all__ = ["register_library_note_tools", "_resolve_note_path"]
