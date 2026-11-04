"""Project resolution shared by the library note handlers."""

from __future__ import annotations

from typing import Any, Optional

from ..._shared import (
    log_agent_misuse,
    resolve_project_context,
)
from .._deps import PROJECT_MANAGER


def _resolve_library_project(project: Optional[str]) -> tuple[Optional[dict[str, Any]], str]:
    info, error_msg = resolve_project_context(
        project,
        required_mode="library-wiki",
        project_manager=PROJECT_MANAGER.get(),
    )
    return info, error_msg or ""


def _require_library_project(
    tool_name: str, project: Optional[str]
) -> tuple[Optional[dict[str, Any]], str]:
    """Resolve the library project, logging agent misuse when it is not available."""
    info, error_msg = _resolve_library_project(project)
    if info is None:
        log_agent_misuse(
            tool_name,
            "library-wiki project required",
            {"project": project},
            error_msg,
        )
    return info, error_msg
