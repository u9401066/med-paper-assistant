"""Tool registration."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from cgu.interfaces.mcp.deps import Deps
from cgu.interfaces.mcp.tools import (
    diverge,
    evolve,
    feedback,
    frame,
    ideas,
    inquiry,
    judge,
    material,
    question_gate,
    session,
    status,
)

_MODULES = (
    status,
    session,
    frame,
    material,
    diverge,
    ideas,
    judge,
    evolve,
    feedback,
    question_gate,
    inquiry,
)


def register_all(server: MCPServer[Deps]) -> None:
    for module in _MODULES:
        module.register(server)
