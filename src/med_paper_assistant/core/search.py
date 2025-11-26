"""
Literature Search Module - Backward Compatibility Facade

This module provides backward compatibility with the original search.py interface.
The actual implementation has been refactored into the `entrez` package for better
modularity and maintainability.

New Module Structure:
    entrez/
    ├── __init__.py     - Package entry point
    ├── base.py         - Base configuration and shared utilities
    ├── search.py       - Core search functionality (esearch, efetch)
    ├── pdf.py          - PDF download from PMC Open Access
    ├── citation.py     - Citation network (related, citing, references)
    ├── batch.py        - Batch processing with History Server
    └── utils.py        - Utility functions (spell check, MeSH, export)

Usage (both work):
    # New way (recommended)
    from med_paper_assistant.core.entrez import LiteratureSearcher
    
    # Old way (backward compatible)
    from med_paper_assistant.core.search import LiteratureSearcher

For new code, prefer importing from `med_paper_assistant.core.entrez`.
"""

# Re-export from the new entrez package for backward compatibility
from med_paper_assistant.core.entrez import (
    LiteratureSearcher,
    SearchStrategy,
    EntrezBase,
    SearchMixin,
    PDFMixin,
    CitationMixin,
    BatchMixin,
    UtilsMixin,
)

__all__ = [
    'LiteratureSearcher',
    'SearchStrategy',
    'EntrezBase',
    'SearchMixin',
    'PDFMixin',
    'CitationMixin',
    'BatchMixin',
    'UtilsMixin',
]

