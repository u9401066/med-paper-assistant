"""Consolidated review/pipeline facade tools."""

from __future__ import annotations

from mcp.server import MCPServer

from ._types import QualityTools, ToolMap
from .pipeline import PipelineActionTool
from .quality import QualityChecksTool


def register_review_facade_tools(
    mcp: MCPServer,
    audit_tools: ToolMap,
    pipeline_tools: ToolMap,
    formatting_tools: ToolMap | None = None,
    health_tools: ToolMap | None = None,
    constraint_tools: ToolMap | None = None,
):
    """Register stable facade verbs for review quality and pipeline control."""

    quality = QualityChecksTool(
        QualityTools(
            audit_tools=audit_tools,
            formatting_tools=formatting_tools or {},
            health_tools=health_tools or {},
            constraint_tools=constraint_tools or {},
        )
    )
    pipeline = PipelineActionTool(pipeline_tools)

    return {
        "run_quality_checks": mcp.tool()(quality.run_quality_checks),
        "pipeline_action": mcp.tool()(pipeline.pipeline_action),
    }


__all__ = ["ToolMap", "register_review_facade_tools"]
