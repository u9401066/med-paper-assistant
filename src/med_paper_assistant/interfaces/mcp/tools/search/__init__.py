"""
Search Tools Module

Tools for literature search and search strategy.
Now uses pubmed-search-mcp submodule.
"""

from mcp.server.fastmcp import FastMCP

from pubmed_search import LiteratureSearcher
from pubmed_search.mcp import register_search_tools as register_pubmed_tools
from pubmed_search.mcp.strategy import StrategyManager


def register_search_tools(mcp: FastMCP, searcher: LiteratureSearcher, strategy_manager: StrategyManager):
    """Register all search-related tools with the MCP server.
    
    Now delegates to pubmed_search.mcp.register_search_tools from submodule.
    """
    register_pubmed_tools(mcp, searcher, strategy_manager)


__all__ = ["register_search_tools", "StrategyManager"]
