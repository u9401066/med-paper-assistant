"""
Validation Tools Module

Provides tools for validating concepts and ideas.
Split into submodules:
- concept: validate_concept, validate_concept_quick
- idea: (future) validate_hypothesis, check_feasibility
"""

from mcp.server.fastmcp import FastMCP

from .concept import register_concept_validation_tools


def register_validation_tools(mcp: FastMCP):
    """Register all validation tools with the MCP server."""
    register_concept_validation_tools(mcp)
    # Future: register_idea_validation_tools(mcp)


__all__ = ["register_validation_tools"]
