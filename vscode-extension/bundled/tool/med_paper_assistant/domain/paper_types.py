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


# ─── Writing Order (Section Prerequisites) ───────────────────────────
# Defines the recommended writing order for each paper type.
# Prerequisites are ADVISORY (not blocking) per CONSTITUTION §22.

WRITING_ORDER: Dict[str, Dict[str, Dict[str, Any]]] = {
    "original-research": {
        "Methods": {"prerequisites": [], "order": 1},
        "Results": {"prerequisites": ["Methods"], "order": 2},
        "Introduction": {"prerequisites": ["Methods"], "order": 3},
        "Discussion": {"prerequisites": ["Results", "Introduction"], "order": 4},
        "Conclusion": {"prerequisites": ["Discussion"], "order": 5},
        "Abstract": {
            "prerequisites": ["Introduction", "Methods", "Results", "Discussion"],
            "order": 6,
        },
    },
    "systematic-review": {
        "Methods": {"prerequisites": [], "order": 1},
        "Results": {"prerequisites": ["Methods"], "order": 2},
        "Discussion": {"prerequisites": ["Results"], "order": 3},
        "Introduction": {"prerequisites": ["Methods"], "order": 4},
        "Conclusion": {"prerequisites": ["Discussion"], "order": 5},
        "Abstract": {
            "prerequisites": ["Introduction", "Methods", "Results", "Discussion"],
            "order": 6,
        },
    },
    "meta-analysis": {
        "Methods": {"prerequisites": [], "order": 1},
        "Results": {"prerequisites": ["Methods"], "order": 2},
        "Discussion": {"prerequisites": ["Results"], "order": 3},
        "Introduction": {"prerequisites": ["Methods"], "order": 4},
        "Conclusion": {"prerequisites": ["Discussion"], "order": 5},
        "Abstract": {
            "prerequisites": ["Introduction", "Methods", "Results", "Discussion"],
            "order": 6,
        },
    },
    "case-report": {
        "Case Presentation": {"prerequisites": [], "order": 1},
        "Discussion": {"prerequisites": ["Case Presentation"], "order": 2},
        "Introduction": {"prerequisites": [], "order": 3},
        "Conclusion": {"prerequisites": ["Discussion"], "order": 4},
        "Abstract": {
            "prerequisites": ["Introduction", "Case Presentation", "Discussion"],
            "order": 5,
        },
    },
    "review-article": {
        "Introduction": {"prerequisites": [], "order": 1},
        "Body (multiple sections)": {"prerequisites": ["Introduction"], "order": 2},
        "Conclusion": {"prerequisites": ["Body (multiple sections)"], "order": 3},
        "Abstract": {"prerequisites": ["Introduction", "Conclusion"], "order": 4},
    },
    "letter": {
        "Main Text": {"prerequisites": [], "order": 1},
    },
}


def _normalize_section_name(section: str) -> str:
    """Normalize section name for matching against draft filenames."""
    return section.lower().replace(" ", "_").replace("(", "").replace(")", "")


def _find_existing_drafts(drafts_dir: str) -> List[str]:
    """Find existing draft section names from filenames in drafts directory."""
    import os

    if not os.path.isdir(drafts_dir):
        return []

    sections = []
    for f in os.listdir(drafts_dir):
        if f.endswith(".md") and f != "concept.md":
            name = f.replace(".md", "").replace("_", " ").replace("-", " ").title()
            sections.append(name)
    return sections


def check_writing_prerequisites(
    paper_type: str, target_section: str, drafts_dir: str
) -> Dict[str, Any]:
    """
    Check if prerequisite sections exist before writing a target section.

    This is ADVISORY per CONSTITUTION §22 — it warns but does not block.

    Args:
        paper_type: The paper type key
        target_section: The section about to be written
        drafts_dir: Path to the project's drafts/ directory

    Returns:
        Dictionary with:
        - can_proceed: Always True (advisory only)
        - missing_prerequisites: List of sections that should be written first
        - warning: Human-readable warning message (empty if all prerequisites met)
        - recommended_order: The full writing order for this paper type
    """
    order_map = WRITING_ORDER.get(paper_type, {})

    # Find the target section info (case-insensitive matching)
    target_info = None
    matched_key = None
    for key, info in order_map.items():
        if key.lower() == target_section.lower():
            target_info = info
            matched_key = key
            break
        # Also match partial (e.g., "intro" matches "Introduction")
        if target_section.lower() in key.lower() or key.lower() in target_section.lower():
            target_info = info
            matched_key = key
            break

    if not target_info or not matched_key:
        return {
            "can_proceed": True,
            "missing_prerequisites": [],
            "warning": "",
            "recommended_order": _format_writing_order(paper_type),
        }

    # Check which prerequisite drafts exist
    existing = _find_existing_drafts(drafts_dir)
    existing_lower = [s.lower() for s in existing]

    missing = []
    for prereq in target_info.get("prerequisites", []):
        prereq_normalized = _normalize_section_name(prereq)
        found = any(
            prereq.lower() in ex or prereq_normalized in ex.lower().replace(" ", "_")
            for ex in existing_lower
        )
        if not found:
            missing.append(prereq)

    warning = ""
    if missing:
        missing_str = ", ".join(f"**{m}**" for m in missing)
        warning = (
            f"⚠️ **寫作順序建議**（Advisory, CONSTITUTION §22 允許跳過）\n\n"
            f"撰寫 **{matched_key}** 前，建議先完成：{missing_str}\n\n"
            f"| 原因 | 說明 |\n"
            f"|------|------|\n"
        )
        for m in missing:
            reason = _get_prerequisite_reason(matched_key, m)
            warning += f"| {m} → {matched_key} | {reason} |\n"

        warning += (
            f"\n📋 **建議寫作順序**：{_format_writing_order(paper_type)}\n\n"
            f"💡 您可以選擇：\n"
            f"1. 先完成前置 section\n"
            f"2. 忽略此建議，直接撰寫（§22 允許）\n"
        )

    return {
        "can_proceed": True,
        "missing_prerequisites": missing,
        "warning": warning,
        "recommended_order": _format_writing_order(paper_type),
    }


def _format_writing_order(paper_type: str) -> str:
    """Format the writing order as a readable string."""
    order_map = WRITING_ORDER.get(paper_type, {})
    if not order_map:
        return "（無定義）"

    sorted_sections = sorted(order_map.items(), key=lambda x: x[1]["order"])
    return " → ".join(f"{s[0]}" for s in sorted_sections)


def _get_prerequisite_reason(target: str, prereq: str) -> str:
    """Get a human-readable reason why prereq should come before target."""
    reasons = {
        ("Results", "Methods"): "Results 需要描述 Methods 中定義的結局指標",
        ("Discussion", "Results"): "Discussion 需要討論 Results 中的發現",
        ("Discussion", "Introduction"): "Discussion 需要回應 Introduction 的研究問題",
        ("Introduction", "Methods"): "Introduction 的研究目的應與 Methods 一致",
        ("Conclusion", "Discussion"): "Conclusion 是 Discussion 的總結",
        ("Abstract", "Introduction"): "Abstract 需要摘錄所有 section 的精華",
        ("Abstract", "Methods"): "Abstract 需要摘錄所有 section 的精華",
        ("Abstract", "Results"): "Abstract 需要摘錄所有 section 的精華",
        ("Abstract", "Discussion"): "Abstract 需要摘錄所有 section 的精華",
        ("Discussion", "Case Presentation"): "Discussion 需要討論 Case 的特殊之處",
    }
    return reasons.get((target, prereq), f"{prereq} 的內容是 {target} 的基礎")


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
