"""Legacy compatibility shim for the retired analysis facade."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from mcp.server.fastmcp import FastMCP

ToolMap = Mapping[str, Callable[..., Any]]


def register_analysis_facade_tools(
    mcp: FastMCP,
    stats_tools: ToolMap,
    table_one_tools: ToolMap,
    figure_tools: ToolMap,
) -> dict[str, Callable[..., Any]]:
    """Return no public facade tools; granular analysis verbs are registered directly."""

    return {}