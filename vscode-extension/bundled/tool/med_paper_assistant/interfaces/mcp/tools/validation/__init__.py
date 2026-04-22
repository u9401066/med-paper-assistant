"""
Validation Tools Module

Provides tools for validating concepts, ideas, and wikilink formats.
Split into submodules:
- concept: validate_concept (with structure_only), validate_wikilinks
- idea: (future) validate_hypothesis, check_feasibility
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ReferenceManager
from med_paper_assistant.interfaces.mcp.tool_surface import ToolSurface, uses_compact_tool_surface

from .concept import register_concept_validation_tools
from .facade import register_validation_facade_tools
from .idea import register_idea_validation_tools


def register_validation_tools(
    mcp: FastMCP,
    ref_manager: Optional[ReferenceManager] = None,
    *,
    tool_surface: ToolSurface = "full",
):
    """Register all validation tools with the MCP server."""
    register_public_verbs = not uses_compact_tool_surface(tool_surface)
    concept_tools = register_concept_validation_tools(
        mcp,
        register_public_verbs=register_public_verbs,
    )
    idea_tools = register_idea_validation_tools(
        mcp,
        ref_manager,
        register_public_verbs=register_public_verbs,
    )

    if uses_compact_tool_surface(tool_surface):
        register_validation_facade_tools(
            mcp,
            concept_tools=concept_tools,
            idea_tools=idea_tools,
        )


__all__ = ["register_validation_tools"]
