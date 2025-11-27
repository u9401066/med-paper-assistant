"""
Paper Types - Domain definitions for medical paper types.

This module defines the available paper types and their characteristics.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PaperTypeInfo:
    """Immutable paper type information."""
    name: str
    description: str
    sections: List[str]
    typical_words: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "sections": list(self.sections),
            "typical_words": self.typical_words
        }


# Paper type definitions
PAPER_TYPES: Dict[str, PaperTypeInfo] = {
    "original-research": PaperTypeInfo(
        name="Original Research",
        description="Clinical trial, cohort study, cross-sectional study",
        sections=["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
        typical_words=3000
    ),
    "systematic-review": PaperTypeInfo(
        name="Systematic Review",
        description="Systematic literature review without meta-analysis",
        sections=["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
        typical_words=4000
    ),
    "meta-analysis": PaperTypeInfo(
        name="Meta-Analysis",
        description="Systematic review with quantitative synthesis",
        sections=["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
        typical_words=4500
    ),
    "case-report": PaperTypeInfo(
        name="Case Report",
        description="Single case or case series",
        sections=["Introduction", "Case Presentation", "Discussion", "Conclusion"],
        typical_words=1500
    ),
    "review-article": PaperTypeInfo(
        name="Review Article",
        description="Narrative review or invited review",
        sections=["Introduction", "Body (multiple sections)", "Conclusion"],
        typical_words=5000
    ),
    "letter": PaperTypeInfo(
        name="Letter / Correspondence",
        description="Brief communication or commentary",
        sections=["Main Text"],
        typical_words=500
    ),
    "other": PaperTypeInfo(
        name="Other",
        description="Editorial, perspective, methodology paper, etc.",
        sections=["Varies"],
        typical_words=2000
    )
}


def get_paper_type(paper_type: str) -> PaperTypeInfo:
    """Get paper type info, returns 'other' if not found."""
    return PAPER_TYPES.get(paper_type, PAPER_TYPES["other"])


def get_paper_type_dict(paper_type: str) -> Dict[str, Any]:
    """Get paper type info as dictionary."""
    return get_paper_type(paper_type).to_dict()


def is_valid_paper_type(paper_type: str) -> bool:
    """Check if paper type is valid."""
    return paper_type in PAPER_TYPES


def list_paper_types() -> List[str]:
    """List all valid paper type keys."""
    return list(PAPER_TYPES.keys())
