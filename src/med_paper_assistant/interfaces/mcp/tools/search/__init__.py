"""
Search Tools Module

Tools for literature search and search strategy.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.services import StrategyManager
from pubmed_search import PubMedClient

from .pubmed import register_pubmed_tools


def register_search_tools(mcp: FastMCP, pubmed_client: PubMedClient, strategy_manager: StrategyManager):
    """Register all search-related tools with the MCP server."""
    register_pubmed_tools(mcp, pubmed_client, strategy_manager)


__all__ = ["register_search_tools"]
