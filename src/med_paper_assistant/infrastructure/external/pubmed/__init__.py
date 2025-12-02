"""
PubMed API Client.

Re-exports from pubmed-search-mcp submodule.
The submodule must be installed: pip install -e integrations/pubmed-search-mcp
"""

from pubmed_search import PubMedClient, SearchResult, SearchStrategy

# Keep parser for any local usage (e.g., reference management)
from .parser import PubMedParser

__all__ = ["PubMedClient", "PubMedParser", "SearchResult", "SearchStrategy"]
