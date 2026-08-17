"""
Reference Entity - Represents a literature reference.

Updated 2025-12: 支援多來源識別符 (PubMed, Zotero, DOI)
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import urlparse

if TYPE_CHECKING:
    from med_paper_assistant.domain.services.reference_converter import StandardizedReference


def has_verified_pubmed_provenance(payload: Dict[str, Any]) -> bool:
    """Return whether metadata satisfies the domain's PubMed trust invariant."""
    if payload.get("verified") is not True:
        return False

    pmid = str(payload.get("pmid") or "").strip()
    retrieved_at = str(payload.get("retrieved_at") or "")
    source_url = str(payload.get("source_url") or "")
    payload_hash = str(payload.get("payload_hash") or "")
    provenance = payload.get("provenance", [])

    try:
        retrieval_time = datetime.fromisoformat(retrieved_at)
        parsed_source_url = urlparse(source_url)
    except (TypeError, ValueError):
        return False

    if (
        payload.get("data_source") != "pubmed_mcp_api"
        or not pmid.isdigit()
        or retrieval_time.tzinfo is None
        or parsed_source_url.scheme not in {"http", "https"}
        or not parsed_source_url.hostname
        or re.fullmatch(r"[0-9a-f]{64}", payload_hash) is None
        or not isinstance(provenance, (list, tuple))
    ):
        return False

    return any(
        isinstance(entry, dict)
        and entry.get("event") == "pubmed_mcp_fetch"
        and entry.get("source") == "pubmed"
        and entry.get("data_source") == "pubmed_mcp_api"
        and str(entry.get("requested_pmid") or "") == pmid
        and entry.get("retrieved_at") == retrieved_at
        and entry.get("source_url") == source_url
        and entry.get("payload_hash") == payload_hash
        for entry in provenance
    )


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

    # Layered trust and transport provenance
    verified: bool = False
    data_source: str = ""
    retrieved_at: str = ""
    source_url: str = ""
    payload_hash: str = ""
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    agent_notes: str = ""
    trust_level: str = "agent"

    # File paths (relative to reference directory)
    has_pdf: bool = False

    # Fulltext ingestion tracking (Phase 2.1)
    fulltext_ingested: bool = False
    fulltext_unavailable_reason: str = ""  # e.g., "not_open_access", "pdf_parse_error"
    asset_aware_doc_id: Optional[str] = None
    fulltext_sections: List[str] = field(default_factory=list)  # e.g., ["Methods", "Results"]

    # Per-reference analysis (Phase 2.1 subagent output)
    analysis_completed: bool = False
    analysis_summary: str = ""  # Structured summary from subagent
    usage_sections: List[str] = field(
        default_factory=list
    )  # Where this ref can be used: ["Introduction", "Discussion"]

    # Metadata
    saved_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Enforce that VERIFIED is inseparable from complete PubMed provenance."""
        self.verified = has_verified_pubmed_provenance(
            {
                "verified": self.verified,
                "pmid": self.pmid,
                "data_source": self.data_source,
                "retrieved_at": self.retrieved_at,
                "source_url": self.source_url,
                "payload_hash": self.payload_hash,
                "provenance": self.provenance,
            }
        )
        if self.verified:
            self.trust_level = "verified"
        elif self.trust_level == "verified":
            self.trust_level = "agent"

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
                    authors.append(
                        {
                            "family": au.get("last_name", ""),
                            "given": au.get("first_name", au.get("initials", "")),
                        }
                    )
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
            "verified": self.verified,
            "data_source": self.data_source,
            "retrieved_at": self.retrieved_at,
            "source_url": self.source_url,
            "payload_hash": self.payload_hash,
            "provenance": self.provenance,
            "agent_notes": self.agent_notes,
            "trust_level": self.trust_level,
            "has_pdf": self.has_pdf,
            "fulltext_ingested": self.fulltext_ingested,
            "fulltext_unavailable_reason": self.fulltext_unavailable_reason,
            "asset_aware_doc_id": self.asset_aware_doc_id,
            "fulltext_sections": self.fulltext_sections,
            "analysis_completed": self.analysis_completed,
            "analysis_summary": self.analysis_summary,
            "usage_sections": self.usage_sections,
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
            verified=data.get("verified") is True,
            data_source=str(data.get("data_source") or ""),
            retrieved_at=str(data.get("retrieved_at") or ""),
            source_url=str(data.get("source_url") or ""),
            payload_hash=str(data.get("payload_hash") or ""),
            provenance=[entry for entry in data.get("provenance", []) if isinstance(entry, dict)]
            if isinstance(data.get("provenance", []), list)
            else [],
            agent_notes=str(data.get("agent_notes") or ""),
            trust_level=str(data.get("trust_level") or "agent"),
            has_pdf=data.get("has_pdf", False),
            fulltext_ingested=data.get("fulltext_ingested", False),
            fulltext_unavailable_reason=data.get("fulltext_unavailable_reason", ""),
            asset_aware_doc_id=data.get("asset_aware_doc_id"),
            fulltext_sections=data.get("fulltext_sections", []),
            analysis_completed=data.get("analysis_completed", False),
            analysis_summary=data.get("analysis_summary", ""),
            usage_sections=data.get("usage_sections", []),
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
            verified=article.get("verified") is True,
            data_source=str(article.get("data_source") or ""),
            retrieved_at=str(article.get("retrieved_at") or ""),
            source_url=str(article.get("source_url") or ""),
            payload_hash=str(article.get("payload_hash") or ""),
            provenance=[entry for entry in article.get("provenance", []) if isinstance(entry, dict)]
            if isinstance(article.get("provenance", []), list)
            else [],
            agent_notes=str(article.get("agent_notes") or ""),
            trust_level="verified"
            if article.get("verified") is True
            else str(article.get("trust_level") or "agent"),
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
            verified=ref.verified,
            data_source=ref.data_source,
            retrieved_at=ref.retrieved_at,
            source_url=ref.source_url,
            payload_hash=ref.payload_hash,
            provenance=ref.provenance or [],
            agent_notes=ref.agent_notes,
            trust_level=ref.trust_level,
        )
