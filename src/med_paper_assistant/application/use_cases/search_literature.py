"""
Search Literature Use Case.

Handles searching for literature on PubMed.
"""

from dataclasses import dataclass, field
from typing import Optional, List

from med_paper_assistant.infrastructure.external.pubmed import PubMedClient
from med_paper_assistant.infrastructure.external.pubmed.client import SearchStrategy, SearchResult


@dataclass
class SearchLiteratureInput:
    """Input data for literature search."""
    query: str
    limit: int = 5
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    article_type: Optional[str] = None
    strategy: str = "relevance"


@dataclass
class SearchLiteratureOutput:
    """Output data from literature search."""
    results: List[SearchResult]
    count: int
    query: str
    message: str


class SearchLiteratureUseCase:
    """
    Use case for searching literature on PubMed.
    
    This use case:
    1. Validates search parameters
    2. Executes search on PubMed
    3. Returns formatted results
    """
    
    def __init__(self, pubmed_client: PubMedClient):
        self.client = pubmed_client
    
    def execute(self, input_data: SearchLiteratureInput) -> SearchLiteratureOutput:
        """
        Execute the search literature use case.
        
        Args:
            input_data: Search parameters.
            
        Returns:
            SearchLiteratureOutput with results.
        """
        # Map strategy string to enum
        try:
            strategy = SearchStrategy(input_data.strategy)
        except ValueError:
            strategy = SearchStrategy.RELEVANCE
        
        # Execute search
        results = self.client.search(
            query=input_data.query,
            limit=input_data.limit,
            min_year=input_data.min_year,
            max_year=input_data.max_year,
            article_type=input_data.article_type,
            strategy=strategy,
        )
        
        return SearchLiteratureOutput(
            results=results,
            count=len(results),
            query=input_data.query,
            message=f"Found {len(results)} results for '{input_data.query}'."
        )
