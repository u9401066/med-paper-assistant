"""
Draft Tools Module

Provides tools for creating and editing paper drafts.
Split into submodules for maintainability:
- writing: write_draft, draft_section, read_draft, list_drafts
- templates: get_section_template, count_words, insert_citation
"""

from mcp.server.fastmcp import FastMCP
from med_paper_assistant.infrastructure.services import Drafter

from .writing import register_writing_tools
from .templates import register_template_tools


def register_draft_tools(mcp: FastMCP, drafter: Drafter):
    """Register all draft-related tools with the MCP server."""
    register_writing_tools(mcp, drafter)
    register_template_tools(mcp, drafter)


__all__ = ["register_draft_tools"]
