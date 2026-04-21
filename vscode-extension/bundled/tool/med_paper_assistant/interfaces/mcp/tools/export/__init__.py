"""
Export Tools Module

Tools for Word document export and Pandoc-based citation export.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import Formatter, TemplateReader, WordWriter
from med_paper_assistant.interfaces.mcp.tool_surface import ToolSurface, uses_compact_tool_surface

from .facade import register_export_facade_tools
from .pandoc_export import register_pandoc_export_tools
from .word import register_word_export_tools


def register_export_tools(
    mcp: FastMCP,
    formatter: Formatter,
    template_reader: TemplateReader,
    word_writer: WordWriter,
    *,
    tool_surface: ToolSurface = "full",
):
    """Register all export-related tools with the MCP server."""
    register_public_verbs = not uses_compact_tool_surface(tool_surface)
    word_tools = register_word_export_tools(
        mcp,
        formatter,
        template_reader,
        word_writer,
        register_public_verbs=register_public_verbs,
    )
    pandoc_tools = register_pandoc_export_tools(
        mcp,
        register_public_verbs=register_public_verbs,
    )
    register_export_facade_tools(mcp, word_tools=word_tools, pandoc_tools=pandoc_tools)


__all__ = ["register_export_tools"]
