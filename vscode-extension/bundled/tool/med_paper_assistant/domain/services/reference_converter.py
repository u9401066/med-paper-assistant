"""
Reference Converter Domain Service

負責將不同來源（PubMed, Zotero）的書目格式轉換為 mdpaper 標準格式。
遵循 DDD 架構：Domain Service 處理跨 Entity 的業務邏輯。
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class StandardizedReference:
    """
    mdpaper 標準化的參考文獻格式。

    所有來源的書目資料都會轉換成這個格式，
    以確保 Foam 整合和引用格式化的一致性。
    """

    # 識別符
    unique_id: str  # 儲存用 ID (e.g., "38049909", "zot_ABC123")
    citation_key: str  # Foam wikilink 用 (e.g., "tang2023_38049909")
    source: str  # "pubmed", "zotero", "doi", "manual"

    # 原始識別符（可能多個）
    pmid: Optional[str] = None
    doi: Optional[str] = None
    zotero_key: Optional[str] = None
    pmc_id: Optional[str] = None

    # 書目資訊
    title: str = ""
    authors: Optional[List[str]] = None  # ["Last First", "Last First"]
    authors_full: Optional[List[Dict]] = (
        None  # [{"last_name": "", "first_name": "", "initials": ""}]
    )
    year: str = ""

    # 期刊資訊
    journal: str = ""
    journal_abbrev: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""

    # 內容
    abstract: str = ""
    keywords: Optional[List[str]] = None
    mesh_terms: Optional[List[str]] = None

    # 元資料
    source_metadata: Optional[Dict[str, Any]] = None  # 保留原始資料

    def __post_init__(self):
        """Initialize default list fields."""
        if self.authors is None:
            self.authors = []
        if self.authors_full is None:
            self.authors_full = []
        if self.keywords is None:
            self.keywords = []
        if self.mesh_terms is None:
            self.mesh_terms = []
        if self.source_metadata is None:
            self.source_metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
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
            "year": self.year,
            "journal": self.journal,
            "journal_abbrev": self.journal_abbrev,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "mesh_terms": self.mesh_terms,
        }


class ReferenceConverter:
    """
    Domain Service for converting reference formats.

    Converts metadata from different sources (PubMed, Zotero) to
    mdpaper's standardized format for Foam integration.
    """

    def convert(self, article: Dict[str, Any]) -> StandardizedReference:
        """
        Convert any article metadata to standardized format.

        Auto-detects source based on available fields.

        Args:
            article: Article metadata from any source.

        Returns:
            StandardizedReference with normalized fields.

        Raises:
            ValueError: If no valid identifier found.
        """
        # Detect source
        if article.get("pmid"):
            return self._from_pubmed(article)
        elif article.get("zotero_key") or article.get("key"):
            return self._from_zotero(article)
        elif article.get("doi") or article.get("DOI"):
            return self._from_doi_only(article)
        else:
            raise ValueError(
                "Article must have at least one identifier: pmid, zotero_key/key, or doi/DOI\n"
                "Received fields: " + ", ".join(article.keys())
            )

    def _from_pubmed(self, article: Dict[str, Any]) -> StandardizedReference:
        """Convert PubMed format to standard format."""
        pmid = str(article.get("pmid", ""))
        year = str(article.get("year", ""))
        author = self._extract_first_author(article)

        citation_key = self._generate_citation_key(author, year, pmid)

        return StandardizedReference(
            unique_id=pmid,
            citation_key=citation_key,
            source="pubmed",
            pmid=pmid,
            doi=article.get("doi"),
            pmc_id=article.get("pmc_id") or article.get("pmc"),
            title=article.get("title", ""),
            authors=article.get("authors", []),
            authors_full=article.get("authors_full", []),
            year=year,
            journal=article.get("journal") or article.get("source", ""),
            journal_abbrev=article.get("journal_abbrev", ""),
            volume=article.get("volume", ""),
            issue=article.get("issue", ""),
            pages=article.get("pages", ""),
            abstract=article.get("abstract", ""),
            keywords=article.get("keywords", []),
            mesh_terms=article.get("mesh_terms", []),
            source_metadata=article,
        )

    def _from_zotero(self, article: Dict[str, Any]) -> StandardizedReference:
        """
        Convert Zotero format to standard format.

        Zotero format differences:
        - key (not zotero_key)
        - creators (not authors)
        - date (not year)
        - publicationTitle (not journal)
        - DOI (uppercase)
        - abstractNote (not abstract)
        """
        zotero_key = article.get("zotero_key") or article.get("key", "")

        # Extract year from date (Zotero format: "2023-05-01" or "2023")
        date = article.get("date", "")
        year = self._extract_year(date)

        # Convert creators to authors
        authors, authors_full = self._convert_zotero_creators(article.get("creators", []))
        author = authors_full[0].get("last_name", "") if authors_full else ""

        # Generate unique ID and citation key
        # Prefer PMID if available (Zotero might have it in extra field)
        pmid = self._extract_pmid_from_zotero(article)

        if pmid:
            unique_id = pmid
            citation_key = self._generate_citation_key(author, year, pmid)
            source = "pubmed"  # Has PMID, treat as PubMed source
        else:
            unique_id = f"zot_{zotero_key}"
            citation_key = self._generate_citation_key(author, year, unique_id)
            source = "zotero"

        return StandardizedReference(
            unique_id=unique_id,
            citation_key=citation_key,
            source=source,
            pmid=pmid,
            doi=article.get("DOI") or article.get("doi"),
            zotero_key=zotero_key,
            title=article.get("title", ""),
            authors=authors,
            authors_full=authors_full,
            year=year,
            journal=article.get("publicationTitle") or article.get("journal", ""),
            journal_abbrev=article.get("journalAbbreviation", ""),
            volume=article.get("volume", ""),
            issue=article.get("issue", ""),
            pages=article.get("pages", ""),
            abstract=article.get("abstractNote") or article.get("abstract", ""),
            keywords=article.get("tags", []),
            source_metadata=article,
        )

    def _from_doi_only(self, article: Dict[str, Any]) -> StandardizedReference:
        """Convert DOI-only format to standard format."""
        doi = article.get("doi") or article.get("DOI", "")
        year = str(article.get("year", ""))
        author = self._extract_first_author(article)

        # Normalize DOI for filename use
        doi_normalized = self._normalize_doi(doi)
        unique_id = f"doi_{doi_normalized}"
        citation_key = self._generate_citation_key(author, year, unique_id)

        return StandardizedReference(
            unique_id=unique_id,
            citation_key=citation_key,
            source="doi",
            doi=doi,
            title=article.get("title", ""),
            authors=article.get("authors", []),
            authors_full=article.get("authors_full", []),
            year=year,
            journal=article.get("journal", ""),
            journal_abbrev=article.get("journal_abbrev", ""),
            volume=article.get("volume", ""),
            issue=article.get("issue", ""),
            pages=article.get("pages", ""),
            abstract=article.get("abstract", ""),
            source_metadata=article,
        )

    def _extract_first_author(self, article: Dict[str, Any]) -> str:
        """Extract first author's last name."""
        # Try authors_full (structured)
        authors_full = article.get("authors_full", [])
        if authors_full and isinstance(authors_full[0], dict):
            return authors_full[0].get("last_name", "")

        # Try creators (Zotero format)
        creators = article.get("creators", [])
        if creators and isinstance(creators[0], dict):
            return creators[0].get("lastName", "")

        # Try authors list (string format)
        authors = article.get("authors", [])
        if authors:
            first = authors[0]
            if isinstance(first, str):
                parts = first.replace(",", " ").split()
                return parts[0] if parts else ""

        return "unknown"

    def _extract_year(self, date: str) -> str:
        """Extract year from various date formats."""
        if not date:
            return ""

        # Try YYYY-MM-DD or YYYY-MM or YYYY
        match = re.match(r"(\d{4})", str(date))
        return match.group(1) if match else ""

    def _convert_zotero_creators(self, creators: List[Dict]) -> tuple:
        """
        Convert Zotero creators to standard format.

        Zotero: [{"creatorType": "author", "firstName": "John", "lastName": "Doe"}]
        Standard authors: ["Doe John", "Smith Jane"]
        Standard authors_full: [{"last_name": "Doe", "first_name": "John", "initials": "J"}]
        """
        authors = []
        authors_full = []

        for creator in creators:
            if creator.get("creatorType") != "author":
                continue

            last_name = creator.get("lastName", "")
            first_name = creator.get("firstName", "")

            # Handle "name" field (single name string)
            if not last_name and creator.get("name"):
                parts = creator["name"].split()
                last_name = parts[0] if parts else ""
                first_name = " ".join(parts[1:]) if len(parts) > 1 else ""

            # Generate initials
            initials = "".join(name[0].upper() for name in first_name.split() if name)

            authors.append(f"{last_name} {first_name}".strip())
            authors_full.append(
                {
                    "last_name": last_name,
                    "first_name": first_name,
                    "initials": initials,
                }
            )

        return authors, authors_full

    def _extract_pmid_from_zotero(self, article: Dict[str, Any]) -> Optional[str]:
        """
        Extract PMID from Zotero item if available.

        Zotero stores PMID in the 'extra' field as "PMID: 12345678"
        """
        extra = article.get("extra", "")
        if not extra:
            return None

        match = re.search(r"PMID:\s*(\d+)", extra, re.IGNORECASE)
        return match.group(1) if match else None

    def _generate_citation_key(self, author: str, year: str, unique_id: str) -> str:
        """Generate Foam-friendly citation key."""
        author_clean = re.sub(r"[^a-z0-9]", "", author.lower())
        if not author_clean:
            author_clean = "unknown"

        return f"{author_clean}{year}_{unique_id}"

    def _normalize_doi(self, doi: str) -> str:
        """Normalize DOI for use in filenames."""
        # Replace special characters with hyphens
        normalized = re.sub(r"[/.]", "-", doi)
        # Remove other special characters
        normalized = re.sub(r"[^a-zA-Z0-9\-]", "", normalized)
        return normalized.lower()


# Singleton instance for convenience
reference_converter = ReferenceConverter()
