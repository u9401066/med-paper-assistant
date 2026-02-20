"""
Draft Tools Module

Provides tools for creating and editing paper drafts.
Split into submodules for maintainability:
- writing: write_draft, draft_section, read_draft, list_drafts
- templates: get_section_template, count_words, insert_citation
- citation: suggest_citations, scan_draft_citations, find_citation_for_claim
- editing: get_available_citations, patch_draft (citation-aware partial editing)
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.citation_assistant import CitationAssistant

from .citation import register_citation_tools
from .editing import register_editing_tools
from .templates import register_template_tools
from .writing import register_writing_tools


def register_draft_tools(mcp: FastMCP, drafter: Drafter):
    """Register all draft-related tools with the MCP server."""
    register_writing_tools(mcp, drafter)
    register_template_tools(mcp, drafter)
    register_editing_tools(mcp, drafter)

    # Initialize and register citation tools
    citation_assistant = CitationAssistant(drafter.ref_manager)
    register_citation_tools(mcp, citation_assistant)


__all__ = ["register_draft_tools"]
