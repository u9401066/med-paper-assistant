"""
Reference ID Value Object - Unique identifier for references.

Foam 需要唯一識別符來支援 [[wikilink]] 功能。
此 Value Object 確保所有來源的參考文獻都有一致的識別方式。
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ReferenceSource(Enum):
    """Reference source type."""

    PUBMED = "pubmed"
    ZOTERO = "zotero"
    DOI = "doi"
    MANUAL = "manual"


@dataclass(frozen=True)
class ReferenceId:
    """
    Unique identifier for a reference.

    Foam 的 [[wikilink]] 需要唯一且人性化的識別符。
    格式：{first_author}{year}_{source_id}

    Examples:
        - PubMed:  tang2023_38049909
        - Zotero:  smith2024_ABC123XY
        - DOI:     jones2023_10-1016-j-bja-2023-01-001

    Attributes:
        source: Reference source (pubmed, zotero, doi, manual)
        source_id: Original ID from the source
        author: First author's last name (lowercase, alphanumeric only)
        year: Publication year
    """

    source: ReferenceSource
    source_id: str
    author: str = ""
    year: str = ""

    @property
    def storage_id(self) -> str:
        """
        ID used for directory/file storage.

        For PubMed: use PMID directly (backward compatible)
        For others: use source prefix + source_id
        """
        if self.source == ReferenceSource.PUBMED:
            return self.source_id
        elif self.source == ReferenceSource.DOI:
            # DOI has special characters, normalize them
            return f"doi_{self._normalize_doi(self.source_id)}"
        elif self.source == ReferenceSource.ZOTERO:
            return f"zot_{self.source_id}"
        else:
            return f"ref_{self.source_id}"

    @property
    def citation_key(self) -> str:
        """
        Human-friendly citation key for Foam [[wikilink]].

        Format: {author}{year}_{storage_id}
        Examples:
            - tang2023_38049909
            - smith2024_zot_ABC123XY
            - jones2023_doi_10-1016-j-bja-2023-01-001
        """
        author_clean = self._normalize_author(self.author)
        year_clean = str(self.year) if self.year else ""

        return f"{author_clean}{year_clean}_{self.storage_id}"

    @property
    def verification_url(self) -> Optional[str]:
        """URL to verify the reference in its original source."""
        if self.source == ReferenceSource.PUBMED:
            return f"https://pubmed.ncbi.nlm.nih.gov/{self.source_id}/"
        elif self.source == ReferenceSource.DOI:
            return f"https://doi.org/{self.source_id}"
        return None

    def _normalize_author(self, author: str) -> str:
        """Normalize author name: lowercase, alphanumeric only."""
        return re.sub(r"[^a-z0-9]", "", author.lower())

    def _normalize_doi(self, doi: str) -> str:
        """Normalize DOI for use in filenames."""
        # Replace special characters with hyphens
        normalized = re.sub(r"[/.]", "-", doi)
        # Remove other special characters
        normalized = re.sub(r"[^a-zA-Z0-9\-]", "", normalized)
        return normalized.lower()

    @classmethod
    def from_pubmed(cls, pmid: str, author: str = "", year: str = "") -> "ReferenceId":
        """Create from PubMed ID."""
        return cls(
            source=ReferenceSource.PUBMED, source_id=str(pmid), author=author, year=str(year)
        )

    @classmethod
    def from_zotero(cls, item_key: str, author: str = "", year: str = "") -> "ReferenceId":
        """Create from Zotero item key."""
        return cls(source=ReferenceSource.ZOTERO, source_id=item_key, author=author, year=str(year))

    @classmethod
    def from_doi(cls, doi: str, author: str = "", year: str = "") -> "ReferenceId":
        """Create from DOI."""
        return cls(source=ReferenceSource.DOI, source_id=doi, author=author, year=str(year))

    @classmethod
    def from_article(cls, article: dict) -> "ReferenceId":
        """
        Create from article metadata dictionary.

        Auto-detects source based on available fields:
        1. pmid → PubMed
        2. zotero_key → Zotero
        3. doi → DOI

        Args:
            article: Article metadata with at least one identifier.

        Returns:
            ReferenceId instance.

        Raises:
            ValueError: If no valid identifier found.
        """
        # Extract author and year
        author = cls._extract_author(article)
        year = str(article.get("year", ""))

        # Priority: PMID > Zotero key > DOI
        if article.get("pmid"):
            return cls.from_pubmed(article["pmid"], author, year)
        elif article.get("zotero_key"):
            return cls.from_zotero(article["zotero_key"], author, year)
        elif article.get("doi"):
            return cls.from_doi(article["doi"], author, year)
        else:
            raise ValueError("Article must have at least one identifier: pmid, zotero_key, or doi")

    @staticmethod
    def _extract_author(article: dict) -> str:
        """Extract first author's last name from article metadata."""
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
                # Format: "Last First" or "Last, First"
                parts = first.replace(",", " ").split()
                return parts[0] if parts else ""

        return ""

    def __str__(self) -> str:
        return self.citation_key

    def __hash__(self) -> int:
        return hash((self.source, self.source_id))

    def __eq__(self, other) -> bool:
        if not isinstance(other, ReferenceId):
            return False
        return self.source == other.source and self.source_id == other.source_id
