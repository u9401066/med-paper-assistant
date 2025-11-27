"""
Citation Formatter Domain Service.

Handles formatting of citations according to different styles.
"""

from typing import List, Dict, Any
from ..entities.reference import Reference
from ..value_objects.citation import CitationStyle, CitationFormat


class CitationFormatter:
    """
    Domain service for formatting citations.
    
    This is a pure domain service with no external dependencies.
    """
    
    def format_reference(
        self, 
        reference: Reference, 
        style: CitationStyle = CitationStyle.VANCOUVER,
        number: int = 1
    ) -> str:
        """Format a single reference."""
        formatters = {
            CitationStyle.VANCOUVER: self._format_vancouver,
            CitationStyle.APA: self._format_apa,
            CitationStyle.NATURE: self._format_nature,
            CitationStyle.HARVARD: self._format_harvard,
        }
        
        formatter = formatters.get(style, self._format_vancouver)
        return formatter(reference, number)
    
    def format_reference_list(
        self,
        references: List[Reference],
        style: CitationStyle = CitationStyle.VANCOUVER
    ) -> str:
        """Format a list of references."""
        lines = []
        for i, ref in enumerate(references, 1):
            lines.append(self.format_reference(ref, style, i))
        return "\n\n".join(lines)
    
    def _format_vancouver(self, ref: Reference, number: int) -> str:
        """Vancouver style: numbered list."""
        authors = self._format_authors_vancouver(ref.authors)
        return (
            f"{number}. {authors}. {ref.title}. "
            f"{ref.journal}. {ref.year};{ref.volume}"
            f"({ref.issue}):{ref.pages}."
            + (f" doi:{ref.doi}" if ref.doi else "")
        )
    
    def _format_apa(self, ref: Reference, number: int) -> str:
        """APA style: Author (Year)."""
        authors = self._format_authors_apa(ref.authors)
        return (
            f"{authors} ({ref.year}). {ref.title}. "
            f"*{ref.journal}*, *{ref.volume}*"
            f"({ref.issue}), {ref.pages}."
            + (f" https://doi.org/{ref.doi}" if ref.doi else "")
        )
    
    def _format_nature(self, ref: Reference, number: int) -> str:
        """Nature style."""
        authors = self._format_authors_nature(ref.authors)
        return (
            f"{number}. {authors} {ref.title}. "
            f"*{ref.journal}* **{ref.volume}**, {ref.pages} ({ref.year})."
        )
    
    def _format_harvard(self, ref: Reference, number: int) -> str:
        """Harvard style."""
        authors = self._format_authors_harvard(ref.authors)
        return (
            f"{authors} ({ref.year}) '{ref.title}', "
            f"*{ref.journal}*, {ref.volume}({ref.issue}), pp. {ref.pages}."
        )
    
    def _format_authors_vancouver(self, authors: List[str], max_authors: int = 6) -> str:
        """Format authors for Vancouver style."""
        if not authors:
            return ""
        if len(authors) > max_authors:
            return ", ".join(authors[:max_authors]) + ", et al"
        return ", ".join(authors)
    
    def _format_authors_apa(self, authors: List[str], max_authors: int = 7) -> str:
        """Format authors for APA style."""
        if not authors:
            return ""
        if len(authors) == 1:
            return authors[0]
        if len(authors) == 2:
            return f"{authors[0]} & {authors[1]}"
        if len(authors) > max_authors:
            return f"{authors[0]} et al."
        return ", ".join(authors[:-1]) + f", & {authors[-1]}"
    
    def _format_authors_nature(self, authors: List[str], max_authors: int = 5) -> str:
        """Format authors for Nature style."""
        if not authors:
            return ""
        if len(authors) > max_authors:
            return f"{authors[0]} et al."
        return ", ".join(authors) + "."
    
    def _format_authors_harvard(self, authors: List[str]) -> str:
        """Format authors for Harvard style."""
        if not authors:
            return ""
        if len(authors) == 1:
            return authors[0]
        if len(authors) == 2:
            return f"{authors[0]} and {authors[1]}"
        return f"{authors[0]} et al."
    
    def generate_in_text_citation(
        self,
        reference: Reference,
        style: CitationStyle = CitationStyle.VANCOUVER,
        number: int = 1
    ) -> str:
        """Generate in-text citation marker."""
        if style in [CitationStyle.VANCOUVER, CitationStyle.NATURE]:
            return f"[{number}]"
        elif style == CitationStyle.APA:
            return f"({reference.first_author}, {reference.year})"
        elif style == CitationStyle.HARVARD:
            return f"({reference.first_author} {reference.year})"
        return f"[{number}]"
