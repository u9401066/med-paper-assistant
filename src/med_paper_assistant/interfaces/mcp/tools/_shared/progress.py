"""Progress-notification helpers for MCP tools.

These helpers wrap FastMCP's Context.report_progress so long-running tools can
send incremental progress updates when the client provides a progress token.
When no progress token exists, FastMCP already no-ops internally, so callers do
not need separate capability checks.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context


async def report_tool_progress(
    ctx: Context | None,
    step: int,
    total_steps: int,
    message: str,
    *,
    start: float = 0.0,
    end: float = 100.0,
) -> None:
    """Report a coarse-grained tool progress milestone.

    Args:
        ctx: FastMCP request context, or ``None`` when unavailable.
        step: Current completed step count.
        total_steps: Total number of planned steps.
        message: Human-readable progress message.
        start: Progress value representing step ``0``.
        end: Progress value representing ``total_steps`` completion.
    """
    if ctx is None or total_steps <= 0:
        return

    bounded_step = max(0, min(step, total_steps))
    span = max(end - start, 0.0)
    progress = start + (span * bounded_step / total_steps)
    await ctx.report_progress(progress=progress, total=100.0, message=message)
