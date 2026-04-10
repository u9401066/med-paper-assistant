"""
Export Tools Module

Tools for Word document export and Pandoc-based citation export.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import Formatter, TemplateReader, WordWriter

from .facade import register_export_facade_tools
from .pandoc_export import register_pandoc_export_tools
from .word import register_word_export_tools


def register_export_tools(
    mcp: FastMCP, formatter: Formatter, template_reader: TemplateReader, word_writer: WordWriter
):
    """Register all export-related tools with the MCP server."""
    word_tools = register_word_export_tools(mcp, formatter, template_reader, word_writer)
    pandoc_tools = register_pandoc_export_tools(mcp)
    register_export_facade_tools(mcp, word_tools=word_tools, pandoc_tools=pandoc_tools)


__all__ = ["register_export_tools"]
