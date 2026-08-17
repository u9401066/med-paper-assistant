"""
External Services - Third-party API integrations.

Note: PubMed search functionality is now provided by pubmed-search MCP server.
Use MCP protocol for search operations, not direct imports.
"""

from .content_integrity import C2paProvenanceAdapter, ConservativeVisibleWatermarkHeuristic

__all__ = ["C2paProvenanceAdapter", "ConservativeVisibleWatermarkHeuristic"]
