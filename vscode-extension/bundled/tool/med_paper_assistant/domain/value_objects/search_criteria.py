"""
Search Criteria Value Object - Immutable search parameters.
"""

from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel


class SearchCriteria(BaseModel):
    """
    Literature search criteria.

    Value object defining search parameters for PubMed queries.
    Uses Pydantic for validation and serialization.
    """

    keywords: List[str] = []
    exclusions: List[str] = []
    article_types: List[str] = []
    min_sample_size: Optional[int] = None
    date_range: Optional[str] = None  # e.g., "2020:2025"

    # Advanced options
    mesh_terms: List[str] = []
    languages: List[str] = ["English"]
    humans_only: bool = True

    def to_pubmed_query(self) -> str:
        """Convert to PubMed query string."""
        parts = []

        # Keywords with OR
        if self.keywords:
            keyword_part = " AND ".join(f"({kw})" for kw in self.keywords)
            parts.append(f"({keyword_part})")

        # MeSH terms
        if self.mesh_terms:
            mesh_part = " OR ".join(f'"{term}"[MeSH]' for term in self.mesh_terms)
            parts.append(f"({mesh_part})")

        # Exclusions
        if self.exclusions:
            for excl in self.exclusions:
                parts.append(f"NOT ({excl})")

        # Article types
        if self.article_types:
            type_part = " OR ".join(f'"{atype}"[pt]' for atype in self.article_types)
            parts.append(f"({type_part})")

        # Date range
        if self.date_range:
            parts.append(f"{self.date_range}[dp]")

        # Humans only
        if self.humans_only:
            parts.append('"humans"[MeSH Terms]')

        return " AND ".join(parts) if parts else ""

    class Config:
        frozen = True  # Make immutable


@dataclass(frozen=True)
class SearchResult:
    """
    Immutable search result summary.
    """

    pmid: str
    title: str
    authors: str
    journal: str
    year: int
    abstract: str = ""
    doi: str = ""
    pmc_id: str = ""
    relevance_score: float = 0.0
