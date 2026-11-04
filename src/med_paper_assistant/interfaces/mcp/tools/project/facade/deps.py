"""Registration-time dependencies shared by the project facade handlers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ..._binding import DepsBinding

ToolMap = Mapping[str, Callable[..., Any]]


@dataclass(frozen=True)
class FacadeDeps:
    """Tool groups the facade handlers dispatch to."""

    crud_tools: ToolMap
    settings_tools: ToolMap
    exploration_tools: ToolMap
    workspace_state_tools: ToolMap
    library_tools: ToolMap
    diagram_tools: ToolMap
    workspace_tools: ToolMap


FACADE_DEPS: DepsBinding[FacadeDeps] = DepsBinding("project_facade_deps")
