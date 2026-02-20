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

from .concept import register_concept_validation_tools
from .idea import register_idea_validation_tools


def register_validation_tools(
    mcp: FastMCP,
    ref_manager: Optional[ReferenceManager] = None,
):
    """Register all validation tools with the MCP server."""
    register_concept_validation_tools(mcp)
    register_idea_validation_tools(mcp, ref_manager)


__all__ = ["register_validation_tools"]
