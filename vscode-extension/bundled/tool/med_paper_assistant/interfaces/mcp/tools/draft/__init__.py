"""
Draft Tools Module

Provides tools for creating and editing paper drafts.
Split into submodules for maintainability:
- writing: write_draft, draft_section, read_draft, list_drafts
- templates: count_words, insert_citation, sync_references
- citation: suggest_citations (with claim_type), scan_draft_citations
- editing: get_available_citations, patch_draft (citation-aware partial editing)

Migrated to Skills:
- get_section_template → .claude/skills/draft-writing/SKILL.md
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import Drafter
from med_paper_assistant.infrastructure.services.citation_assistant import CitationAssistant
from med_paper_assistant.interfaces.mcp.tool_surface import ToolSurface, uses_compact_tool_surface

from .citation import register_citation_tools
from .editing import register_editing_tools
from .facade import register_draft_facade_tools
from .templates import register_template_tools
from .writing import register_writing_tools


def register_draft_tools(
    mcp: FastMCP,
    drafter: Drafter,
    *,
    tool_surface: ToolSurface = "full",
):
    """Register all draft-related tools with the MCP server."""
    register_public_verbs = not uses_compact_tool_surface(tool_surface)
    writing_tools = register_writing_tools(
        mcp,
        drafter,
        register_public_verbs=register_public_verbs,
    )
    template_tools = register_template_tools(
        mcp,
        drafter,
        register_public_verbs=register_public_verbs,
    )
    editing_tools = register_editing_tools(
        mcp,
        drafter,
        register_public_verbs=register_public_verbs,
    )

    # Initialize and register citation tools
    citation_assistant = CitationAssistant(drafter.ref_manager)
    citation_tools = register_citation_tools(
        mcp,
        citation_assistant,
        register_public_verbs=register_public_verbs,
    )

    facade_tools = register_draft_facade_tools(
        mcp,
        writing_tools=writing_tools,
        template_tools=template_tools,
        editing_tools=editing_tools,
        citation_tools=citation_tools,
    )

    return {
        **writing_tools,
        **template_tools,
        **editing_tools,
        **citation_tools,
        **facade_tools,
    }


__all__ = ["register_draft_tools"]
