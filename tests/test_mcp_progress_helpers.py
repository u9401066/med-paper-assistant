"""Tests for MCP progress helper utilities."""

import pytest

from med_paper_assistant.interfaces.mcp.tools._shared.progress import report_tool_progress


class DummyContext:
    """Minimal async context stub for progress-notification tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[float, float, str]] = []

    async def report_progress(self, progress: float, total: float, message: str) -> None:
        self.calls.append((progress, total, message))


@pytest.mark.asyncio
async def test_report_tool_progress_scales_step_to_percentage() -> None:
    ctx = DummyContext()

    await report_tool_progress(ctx, 2, 4, "Halfway there")

    assert ctx.calls == [(50.0, 100.0, "Halfway there")]


@pytest.mark.asyncio
async def test_report_tool_progress_respects_custom_range() -> None:
    ctx = DummyContext()

    await report_tool_progress(ctx, 1, 4, "Warmup", start=10.0, end=90.0)

    assert ctx.calls == [(30.0, 100.0, "Warmup")]


@pytest.mark.asyncio
async def test_report_tool_progress_noops_without_context() -> None:
    await report_tool_progress(None, 1, 3, "No context available")
