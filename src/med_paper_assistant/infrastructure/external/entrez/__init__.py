"""
Entrez Module - NCBI Entrez API Integration

This module provides a modular interface to NCBI's Entrez E-utilities.

Re-exports from pubmed-search-mcp submodule for backward compatibility.
Falls back to local implementation if submodule not installed.

Usage:
    from med_paper_assistant.infrastructure.external.entrez import LiteratureSearcher
    
    searcher = LiteratureSearcher(email="your@email.com")
    results = searcher.search("diabetes treatment", limit=10)
"""

try:
    # Try to import from the submodule first
    from pubmed_search.entrez import (
        LiteratureSearcher,
        EntrezBase,
        SearchStrategy,
        SearchMixin,
        PDFMixin,
        CitationMixin,
        BatchMixin,
        UtilsMixin,
    )
except ImportError:
    # Fallback to local implementation if submodule not installed
    from .base import EntrezBase, SearchStrategy
    from .search import SearchMixin
    from .pdf import PDFMixin
    from .citation import CitationMixin
    from .batch import BatchMixin
    from .utils import UtilsMixin

    class LiteratureSearcher(
        SearchMixin,
        PDFMixin,
        CitationMixin,
        BatchMixin,
        UtilsMixin,
        EntrezBase
    ):
        """
        Complete literature search interface combining all Entrez functionality.
        """
        pass


__all__ = [
    'LiteratureSearcher',
    'EntrezBase',
    'SearchStrategy',
    'SearchMixin',
    'PDFMixin',
    'CitationMixin',
    'BatchMixin',
    'UtilsMixin',
]
