"""
Export Tools Module

Tools for Word document export.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import Formatter, TemplateReader, WordWriter

from .word import register_word_export_tools


def register_export_tools(
    mcp: FastMCP, 
    formatter: Formatter,
    template_reader: TemplateReader,
    word_writer: WordWriter
):
    """Register all export-related tools with the MCP server."""
    register_word_export_tools(mcp, formatter, template_reader, word_writer)


__all__ = ["register_export_tools"]
