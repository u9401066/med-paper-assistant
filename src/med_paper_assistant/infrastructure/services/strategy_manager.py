"""
Strategy Manager - Re-exports from pubmed_search submodule.

This module provides backward compatibility by re-exporting the 
StrategyManager from the pubmed-search-mcp submodule.
"""

# Re-export from submodule
from pubmed_search.mcp.strategy import StrategyManager, SearchStrategy

# Alias for backward compatibility
SearchCriteria = SearchStrategy

__all__ = ["StrategyManager", "SearchStrategy", "SearchCriteria"]
