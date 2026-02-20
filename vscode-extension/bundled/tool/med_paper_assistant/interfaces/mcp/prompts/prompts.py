"""
MCP Prompts Module - DEPRECATED

NOTE: MCP Prompts have been removed in favor of VS Code Local Prompts.
Use `.github/prompts/*.prompt.md` for guided workflows.

This module is kept for potential future completion handler support,
but all @mcp.prompt decorators have been removed.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import TemplateReader


def register_prompts(mcp: FastMCP, template_reader: TemplateReader):
    """
    Register prompts with the MCP server.

    DEPRECATED: MCP Prompts removed. Use VS Code Local Prompts instead:
    - `.github/prompts/mdpaper.search.prompt.md`
    - `.github/prompts/mdpaper.concept.prompt.md`
    - `.github/prompts/mdpaper.draft.prompt.md`
    - etc.

    This function is kept as a no-op for backward compatibility.
    """
    # No MCP prompts registered - use VS Code Local Prompts instead
    pass
