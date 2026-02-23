"""
Reference Entity - Represents a literature reference.

Updated 2025-12: 支援多來源識別符 (PubMed, Zotero, DOI)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from med_paper_assistant.domain.services.reference_converter import StandardizedReference


@dataclass
class Reference:
    """
    Literature reference entity.

    Represents a saved reference with metadata, citations, and optional fulltext.

    識別符說明:
    - unique_id: 儲存用 ID (e.g., "38049909", "zot_ABC123", "doi_10-1234")
    - citation_key: Foam [[wikilink]] 用 (e.g., "tang2023_38049909")
    - source: 來源類型 ("pubmed", "zotero", "doi", "manual")
    """

    # 必要識別符
    unique_id: str  # 儲存用唯一識別符
    title: str

    # 來源資訊
    source: str = "pubmed"  # pubmed, zotero, doi, manual
    pmid: Optional[str] = None
    doi: Optional[str] = None
    zotero_key: Optional[str] = None
    pmc_id: Optional[str] = None

    # Citation key for Foam
    citation_key: str = ""

    # 作者資訊
    authors: List[str] = field(default_factory=list)
    authors_full: List[Dict[str, str]] = field(default_factory=list)

    # 出版資訊
    journal: str = ""
    journal_abbrev: str = ""
    year: int = 0
    volume: str = ""
    issue: str = ""
    pages: str = ""

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
        # Try authors_full first
        if self.authors_full:
            first = self.authors_full[0]
            if isinstance(first, dict):
                return first.get("last_name", "")
        # Fallback to authors list
        if self.authors:
            return self.authors[0].split()[0]
        return ""

    def get_citation_key(self) -> str:
        """
        Get citation key for Foam [[wikilink]].

        If citation_key is set, return it.
        Otherwise, generate from author + year + unique_id.
        """
        if self.citation_key:
            return self.citation_key

        import re

        author_clean = re.sub(r"[^a-z0-9]", "", self.first_author.lower())
        if not author_clean:
            author_clean = "unknown"
        return f"{author_clean}{self.year}_{self.unique_id}"

    def get_citation(self, style: str = "vancouver") -> str:
        """Get formatted citation in specified style."""
        return self.citations.get(style, self.citations.get("vancouver", ""))

    def to_csl_json(self, ref_id: str | None = None) -> Dict[str, Any]:
        """
        Convert to CSL-JSON format for citeproc processors.

        CSL-JSON is the standard interchange format for citation processors
        (citeproc-py, Pandoc citeproc, Zotero, etc.).

        Args:
            ref_id: Override the CSL-JSON "id" field. Defaults to unique_id or citation_key.

        Returns:
            Dict in CSL-JSON format.
        """
        csl_id = ref_id or self.unique_id or self.citation_key or "ref"

        # Build author list
        authors = []
        if self.authors_full:
            for au in self.authors_full:
                if isinstance(au, dict):
                    authors.append({
                        "family": au.get("last_name", ""),
                        "given": au.get("first_name", au.get("initials", "")),
                    })
        elif self.authors:
            for name in self.authors:
                parts = name.strip().split()
                if len(parts) >= 2:
                    authors.append({"family": parts[0], "given": " ".join(parts[1:])})
                elif parts:
                    authors.append({"family": parts[0]})

        # Build issued date
        issued: Dict[str, Any] = {}
        if self.year:
            issued = {"date-parts": [[int(self.year)]]}

        entry: Dict[str, Any] = {
            "id": csl_id,
            "type": "article-journal",
            "title": self.title,
            "author": authors,
            "issued": issued,
        }

        # Optional fields
        journal = self.journal_abbrev or self.journal
        if journal:
            entry["container-title"] = journal
        if self.volume:
            entry["volume"] = self.volume
        if self.issue:
            entry["issue"] = self.issue
        if self.pages:
            entry["page"] = self.pages
        if self.doi:
            entry["DOI"] = self.doi
        if self.pmid:
            entry["PMID"] = self.pmid

        return entry

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "unique_id": self.unique_id,
            "citation_key": self.citation_key,
            "source": self.source,
            "pmid": self.pmid,
            "doi": self.doi,
            "zotero_key": self.zotero_key,
            "pmc_id": self.pmc_id,
            "title": self.title,
            "authors": self.authors,
            "authors_full": self.authors_full,
            "journal": self.journal,
            "journal_abbrev": self.journal_abbrev,
            "year": self.year,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
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
        # Support both old (pmid-only) and new (unique_id) formats
        unique_id = data.get("unique_id") or data.get("pmid", "")

        return cls(
            unique_id=unique_id,
            title=data.get("title", ""),
            source=data.get("source", "pubmed"),
            pmid=data.get("pmid"),
            doi=data.get("doi"),
            zotero_key=data.get("zotero_key"),
            pmc_id=data.get("pmc_id", data.get("pmc")),
            citation_key=data.get("citation_key", ""),
            authors=data.get("authors", []),
            authors_full=data.get("authors_full", []),
            journal=data.get("journal", data.get("source", "")),
            journal_abbrev=data.get("journal_abbrev", ""),
            year=int(data.get("year", 0)),
            volume=data.get("volume", ""),
            issue=data.get("issue", ""),
            pages=data.get("pages", ""),
            abstract=data.get("abstract", ""),
            keywords=data.get("keywords", []),
            mesh_terms=data.get("mesh_terms", []),
            citations=data.get("citations", data.get("citation", {})),
            has_pdf=data.get("has_pdf", False),
            saved_at=datetime.fromisoformat(data["saved_at"])
            if "saved_at" in data
            else datetime.now(),
        )

    @classmethod
    def from_pubmed(cls, article: Dict[str, Any]) -> "Reference":
        """Create from PubMed article data."""
        pmid = article.get("pmid", "")
        return cls(
            unique_id=pmid,
            title=article.get("title", ""),
            source="pubmed",
            pmid=pmid,
            doi=article.get("doi"),
            pmc_id=article.get("pmc"),
            authors=article.get("authors", []),
            authors_full=article.get("authors_full", []),
            journal=article.get("journal") or article.get("source", ""),
            journal_abbrev=article.get("journal_abbrev", ""),
            year=int(article.get("year", 0)),
            volume=article.get("volume", ""),
            issue=article.get("issue", ""),
            pages=article.get("pages", ""),
            abstract=article.get("abstract", ""),
            keywords=article.get("keywords", []),
            mesh_terms=article.get("mesh_terms", []),
        )

    @classmethod
    def from_standardized(cls, ref: "StandardizedReference") -> "Reference":
        """
        Create from StandardizedReference (from ReferenceConverter).

        Args:
            ref: StandardizedReference from domain service.
        """
        return cls(
            unique_id=ref.unique_id,
            title=ref.title,
            source=ref.source,
            pmid=ref.pmid,
            doi=ref.doi,
            zotero_key=ref.zotero_key,
            pmc_id=ref.pmc_id,
            citation_key=ref.citation_key,
            authors=ref.authors or [],
            authors_full=ref.authors_full or [],
            journal=ref.journal,
            journal_abbrev=ref.journal_abbrev,
            year=int(ref.year) if ref.year else 0,
            volume=ref.volume,
            issue=ref.issue,
            pages=ref.pages,
            abstract=ref.abstract,
            keywords=ref.keywords or [],
            mesh_terms=ref.mesh_terms or [],
        )
