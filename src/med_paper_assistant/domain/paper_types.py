"""
Paper Types - Domain definitions for medical paper types.

This module defines the available paper types and their characteristics.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class ConceptRequirements:
    """
    Concept validation requirements per paper type.

    Attributes:
        core_required: Always required (e.g., NOVELTY STATEMENT)
        intro_required: Required to write Introduction
        methods_required: Required to write Methods (RECOMMENDED, not blocking)
        special_sections: Type-specific requirements
    """

    core_required: List[str] = field(default_factory=list)
    intro_required: List[str] = field(default_factory=list)
    methods_required: List[str] = field(default_factory=list)  # RECOMMENDED
    special_sections: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "core_required": list(self.core_required),
            "intro_required": list(self.intro_required),
            "methods_required": list(self.methods_required),
            "special_sections": list(self.special_sections),
        }


@dataclass(frozen=True)
class PaperTypeInfo:
    """Immutable paper type information."""

    name: str
    description: str
    sections: List[str]
    typical_words: int
    concept_requirements: ConceptRequirements = field(default_factory=ConceptRequirements)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "sections": list(self.sections),
            "typical_words": self.typical_words,
            "concept_requirements": self.concept_requirements.to_dict(),
        }


# Paper type definitions with concept requirements
PAPER_TYPES: Dict[str, PaperTypeInfo] = {
    "original-research": PaperTypeInfo(
        name="Original Research",
        description="Clinical trial, cohort study, cross-sectional study",
        sections=["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
        typical_words=3000,
        concept_requirements=ConceptRequirements(
            core_required=["novelty_statement", "selling_points"],
            intro_required=["background", "research_gap", "research_question"],
            methods_required=["study_design", "participants", "outcomes"],  # RECOMMENDED
            special_sections=["pre_analysis_checklist"],
        ),
    ),
    "systematic-review": PaperTypeInfo(
        name="Systematic Review",
        description="Systematic literature review without meta-analysis",
        sections=["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
        typical_words=4000,
        concept_requirements=ConceptRequirements(
            core_required=["novelty_statement", "selling_points"],
            intro_required=["background", "research_gap", "research_question"],
            methods_required=["prisma_protocol", "search_strategy", "eligibility_criteria"],
            special_sections=["prisma_checklist"],
        ),
    ),
    "meta-analysis": PaperTypeInfo(
        name="Meta-Analysis",
        description="Systematic review with quantitative synthesis",
        sections=["Introduction", "Methods", "Results", "Discussion", "Conclusion"],
        typical_words=4500,
        concept_requirements=ConceptRequirements(
            core_required=["novelty_statement", "selling_points"],
            intro_required=["background", "research_gap", "research_question"],
            methods_required=["prisma_protocol", "search_strategy", "statistical_analysis"],
            special_sections=["prisma_checklist", "forest_plot_plan"],
        ),
    ),
    "case-report": PaperTypeInfo(
        name="Case Report",
        description="Single case or case series",
        sections=["Introduction", "Case Presentation", "Discussion", "Conclusion"],
        typical_words=1500,
        concept_requirements=ConceptRequirements(
            core_required=["novelty_statement", "selling_points"],
            intro_required=["background"],
            methods_required=[],  # Not required for case reports
            special_sections=["case_timeline", "care_checklist"],
        ),
    ),
    "review-article": PaperTypeInfo(
        name="Review Article",
        description="Narrative review or invited review",
        sections=["Introduction", "Body (multiple sections)", "Conclusion"],
        typical_words=5000,
        concept_requirements=ConceptRequirements(
            core_required=["novelty_statement", "selling_points"],
            intro_required=["background", "scope"],
            methods_required=[],  # Not required for narrative reviews
            special_sections=["topic_outline"],
        ),
    ),
    "letter": PaperTypeInfo(
        name="Letter / Correspondence",
        description="Brief communication or commentary",
        sections=["Main Text"],
        typical_words=500,
        concept_requirements=ConceptRequirements(
            core_required=["novelty_statement"],  # Only novelty required
            intro_required=[],
            methods_required=[],
            special_sections=[],
        ),
    ),
    "other": PaperTypeInfo(
        name="Other",
        description="Editorial, perspective, methodology paper, etc.",
        sections=["Varies"],
        typical_words=2000,
        concept_requirements=ConceptRequirements(
            core_required=["novelty_statement"],
            intro_required=["background"],
            methods_required=[],
            special_sections=[],
        ),
    ),
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


def get_concept_requirements(paper_type: str) -> ConceptRequirements:
    """Get concept validation requirements for a paper type."""
    return get_paper_type(paper_type).concept_requirements


def get_section_requirements(paper_type: str, section: str) -> Dict[str, Any]:
    """
    Get the concept requirements needed to write a specific section.

    This enables section-specific validation:
    - Introduction: needs core + intro_required
    - Methods: needs core + intro + methods_required (RECOMMENDED)
    - Results: needs Methods completed + actual data
    - Discussion: needs core + Results completed

    Args:
        paper_type: The paper type key
        section: The section to write (Introduction, Methods, etc.)

    Returns:
        Dictionary with 'required' (must have) and 'recommended' (should have) sections
    """
    reqs = get_concept_requirements(paper_type)
    section_lower = section.lower()

    required_list: List[str] = list(reqs.core_required)
    recommended_list: List[str] = []
    blocking = True

    if section_lower in ["introduction", "intro"]:
        required_list.extend(reqs.intro_required)

    elif section_lower in ["methods", "materials and methods"]:
        required_list.extend(reqs.intro_required)
        recommended_list = list(reqs.methods_required)
        blocking = False

    elif section_lower in ["results"]:
        required_list.extend(reqs.intro_required)
        recommended_list = list(reqs.methods_required)
        recommended_list.append("data_analysis_completed")

    elif section_lower in ["discussion"]:
        required_list.extend(reqs.intro_required)
        recommended_list.append("results_completed")

    elif section_lower in ["conclusion", "conclusions"]:
        # Conclusion just needs core
        pass

    return {
        "required": required_list,
        "recommended": recommended_list,
        "blocking": blocking,
    }
