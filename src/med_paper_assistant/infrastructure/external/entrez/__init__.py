"""
Entrez Module - NCBI Entrez API Integration

Re-exports from pubmed-search-mcp submodule.
The submodule must be installed: pip install -e integrations/pubmed-search-mcp

Usage:
    from med_paper_assistant.infrastructure.external.entrez import LiteratureSearcher
    
    searcher = LiteratureSearcher(email="your@email.com")
    results = searcher.search("diabetes treatment", limit=10)
"""

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
