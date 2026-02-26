"""
Save Reference Use Case.

Handles saving a reference to the local library.

Note: PubMed search functionality is now provided by pubmed-search MCP server.
This use case is kept for backward compatibility but is not used in MCP workflows.
The actual save_reference_mcp tool bypasses this class entirely.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


@dataclass
class SaveReferenceInput:
    """Input data for saving a reference."""

    pmid: str
    download_pdf: bool = True


@dataclass
class SaveReferenceOutput:
    """Output data after saving a reference."""

    pmid: str
    title: str
    has_pdf: bool
    path: str
    message: str


class SaveReferenceUseCase:
    """
    Use case for saving a reference to the local library.

    DEPRECATED: This use case relied on the removed PubMed client.
    The actual workflow now uses ``save_reference_mcp`` MCP tool which
    bypasses this class entirely.  Kept as a stub for import compatibility.
    """

    def __init__(self, repository: Any, pubmed_client: Any = None):
        self.repository = repository
        self.client = pubmed_client

    def execute(self, input_data: SaveReferenceInput) -> SaveReferenceOutput:
        """Execute the save reference use case.

        Raises:
            NotImplementedError: Always. Use save_reference_mcp instead.
        """
        raise NotImplementedError(
            "SaveReferenceUseCase is deprecated. "
            "Use save_reference_mcp (MCP-to-MCP verified) instead."
        )
