"""Shared plumbing for the tool modules."""

from __future__ import annotations

import logging
from collections.abc import Awaitable
from typing import Any, TypeAlias

from mcp.server.mcpserver import Context

from cgu.application.ports import ProgressFn
from cgu.domain.common import CGUError, ToolResult
from cgu.interfaces.mcp.deps import Deps

logger = logging.getLogger("cgu.tools")

Ctx: TypeAlias = Context[Deps, Any]

TOOL_MATURITY: dict[str, str] = {
    "cgu_status": "stable",
    "cgu_session": "stable",
    "cgu_frame": "heuristic",
    "cgu_material": "stable",
    "cgu_diverge": "heuristic",
    "cgu_ideas": "stable",
    "cgu_judge": "experimental",
    "cgu_evolve": "experimental",
    "cgu_feedback": "stable",
    "cgu_question_gate": "experimental",
    "cgu_inquiry": "heuristic",
}


def deps_of(ctx: Ctx) -> Deps:
    deps: Deps = ctx.request_context.lifespan_context
    return deps


async def guarded(call: Awaitable[ToolResult]) -> ToolResult:
    """Domain errors become ToolResult(ok=False); anything else is a bug and is left to the SDK."""
    try:
        return await call
    except CGUError as error:
        return ToolResult.failure(error.code, error.message, error.hint)


def progress_of(ctx: Ctx) -> ProgressFn:
    async def report(progress: float, total: float | None, message: str | None) -> None:
        logger.info("progress %s/%s %s", progress, total, message or "")
        await ctx.report_progress(progress, total, message)

    return report
