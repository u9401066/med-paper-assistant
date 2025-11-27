"""
Citation Value Objects - Immutable citation-related types.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any


class CitationStyle(Enum):
    """Supported citation styles."""
    VANCOUVER = "vancouver"
    APA = "apa"
    HARVARD = "harvard"
    NATURE = "nature"
    AMA = "ama"
    NLM = "nlm"
    MDPI = "mdpi"
    
    @classmethod
    def from_string(cls, value: str) -> "CitationStyle":
        """Create from string value."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.VANCOUVER  # Default


@dataclass(frozen=True)
class CitationFormat:
    """
    Citation format configuration for a journal.
    
    Immutable value object defining how citations should be formatted.
    """
    style: CitationStyle
    in_text_format: str = "[{n}]"  # e.g., "[1]", "(Author, Year)"
    superscript: bool = False
    author_format: str = "last_first"  # last_first, first_last
    max_authors: int = 6
    et_al_threshold: int = 3
    
    # Journal-specific overrides
    journal_name: str = ""
    
    def format_in_text(self, number: int) -> str:
        """Format an in-text citation."""
        return self.in_text_format.format(n=number)


# Pre-defined journal citation configurations
JOURNAL_CITATION_CONFIGS: Dict[str, CitationFormat] = {
    "bja": CitationFormat(
        style=CitationStyle.VANCOUVER,
        journal_name="British Journal of Anaesthesia",
        in_text_format="[{n}]",
        superscript=True,
    ),
    "anesthesiology": CitationFormat(
        style=CitationStyle.VANCOUVER,
        journal_name="Anesthesiology",
        in_text_format="({n})",
    ),
    "lancet": CitationFormat(
        style=CitationStyle.VANCOUVER,
        journal_name="The Lancet",
        in_text_format="[{n}]",
        superscript=True,
    ),
    "nejm": CitationFormat(
        style=CitationStyle.VANCOUVER,
        journal_name="New England Journal of Medicine",
        in_text_format="[{n}]",
        superscript=True,
    ),
    "sensors": CitationFormat(
        style=CitationStyle.MDPI,
        journal_name="Sensors",
        in_text_format="[{n}]",
    ),
}
