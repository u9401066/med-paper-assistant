"""
Reference Entity - Represents a literature reference.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass
class Reference:
    """
    Literature reference entity.
    
    Represents a saved reference with metadata, citations, and optional fulltext.
    """
    pmid: str
    title: str
    authors: List[str] = field(default_factory=list)
    journal: str = ""
    year: int = 0
    
    # Publication details
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    pmc_id: str = ""
    
    # Content
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    mesh_terms: List[str] = field(default_factory=list)
    
    # Pre-formatted citations
    citations: Dict[str, str] = field(default_factory=dict)
    
    # File paths (relative to reference directory)
    has_pdf: bool = False
    
    # Metadata
    saved_at: datetime = field(default_factory=datetime.now)
    
    @property
    def first_author(self) -> str:
        """Get first author's last name."""
        if self.authors:
            return self.authors[0].split()[-1]
        return ""
    
    @property
    def citation_key(self) -> str:
        """Generate citation key (e.g., Smith2024)."""
        return f"{self.first_author}{self.year}"
    
    def get_citation(self, style: str = "vancouver") -> str:
        """Get formatted citation in specified style."""
        return self.citations.get(style, self.citations.get("vancouver", ""))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pmid": self.pmid,
            "title": self.title,
            "authors": self.authors,
            "journal": self.journal,
            "year": self.year,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "doi": self.doi,
            "pmc_id": self.pmc_id,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "mesh_terms": self.mesh_terms,
            "citations": self.citations,
            "has_pdf": self.has_pdf,
            "saved_at": self.saved_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Reference":
        """Create from dictionary."""
        return cls(
            pmid=data.get("pmid", ""),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            journal=data.get("journal", data.get("source", "")),
            year=int(data.get("year", 0)),
            volume=data.get("volume", ""),
            issue=data.get("issue", ""),
            pages=data.get("pages", ""),
            doi=data.get("doi", ""),
            pmc_id=data.get("pmc_id", data.get("pmc", "")),
            abstract=data.get("abstract", ""),
            keywords=data.get("keywords", []),
            mesh_terms=data.get("mesh_terms", []),
            citations=data.get("citations", data.get("citation", {})),
            has_pdf=data.get("has_pdf", False),
            saved_at=datetime.fromisoformat(data["saved_at"]) if "saved_at" in data else datetime.now(),
        )
    
    @classmethod
    def from_pubmed(cls, article: Dict[str, Any]) -> "Reference":
        """Create from PubMed article data."""
        return cls(
            pmid=article.get("pmid", ""),
            title=article.get("title", ""),
            authors=article.get("authors", []),
            journal=article.get("source", ""),
            year=int(article.get("year", 0)),
            volume=article.get("volume", ""),
            issue=article.get("issue", ""),
            pages=article.get("pages", ""),
            doi=article.get("doi", ""),
            pmc_id=article.get("pmc", ""),
            abstract=article.get("abstract", ""),
            keywords=article.get("keywords", []),
            mesh_terms=article.get("mesh_terms", []),
        )
