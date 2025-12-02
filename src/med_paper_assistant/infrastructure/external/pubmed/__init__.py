"""
PubMed API Client.

Re-exports from pubmed-search-mcp submodule for backward compatibility.
"""

try:
    # Try to import from the submodule first
    from pubmed_search import PubMedClient, SearchResult, SearchStrategy
    from pubmed_search.entrez import LiteratureSearcher
except ImportError:
    # Fallback to local implementation if submodule not installed
    from .client import PubMedClient
    from .client import SearchResult, SearchStrategy

# Keep parser for any local usage
from .parser import PubMedParser

__all__ = ["PubMedClient", "PubMedParser", "SearchResult", "SearchStrategy"]
