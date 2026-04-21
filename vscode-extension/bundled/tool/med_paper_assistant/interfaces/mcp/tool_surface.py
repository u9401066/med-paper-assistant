"""Tool surface policy helpers for MCP server registration."""

from __future__ import annotations

import os
from typing import Literal, cast

ToolSurface = Literal["full", "compact"]

_SURFACE_ENV_VAR = "MEDPAPER_TOOL_SURFACE"


def resolve_tool_surface(explicit: str | None = None) -> ToolSurface:
    """Resolve the MCP tool surface from explicit input or environment."""
    candidate = (explicit or os.environ.get(_SURFACE_ENV_VAR, "full")).strip().lower()
    if candidate == "compact":
        return cast(ToolSurface, "compact")
    return cast(ToolSurface, "full")


def uses_compact_tool_surface(explicit: str | None = None) -> bool:
    """Return True when the configured surface is compact."""
    return resolve_tool_surface(explicit) == "compact"


__all__ = ["ToolSurface", "resolve_tool_surface", "uses_compact_tool_surface"]
