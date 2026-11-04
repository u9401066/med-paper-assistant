"""Result dataclasses for concept validation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SectionCheck:
    """Result of checking a single section."""

    name: str
    found: bool = False
    has_content: bool = False
    content: str = ""
    patterns: List[str] = field(default_factory=list)
    required: bool = False


@dataclass
class ValidationResult:
    """Complete validation result for a concept file."""

    file_path: str
    timestamp: str
    paper_type: str = "original-research"  # Track paper type
    target_section: str = ""  # Track which section validation is for

    # Structural validation
    structure_valid: bool = False
    sections: Dict[str, SectionCheck] = field(default_factory=dict)
    missing_required: List[str] = field(default_factory=list)
    missing_recommended: List[str] = field(default_factory=list)

    # Novelty evaluation
    novelty_checked: bool = False
    novelty_passed: bool = False
    novelty_scores: List[int] = field(default_factory=list)
    novelty_average: float = 0.0
    novelty_details: Dict[str, Any] = field(default_factory=dict)

    # Selling points quality
    selling_points_checked: bool = False
    selling_points_passed: bool = False
    selling_points_score: float = 0.0
    selling_points_details: Dict[str, Any] = field(default_factory=dict)

    # Consistency check
    consistency_checked: bool = False
    consistency_passed: bool = False
    consistency_score: float = 0.0
    consistency_issues: List[str] = field(default_factory=list)

    # Citation support
    citation_checked: bool = False
    citation_score: float = 0.0
    unsupported_claims: List[Dict] = field(default_factory=list)

    # Overall
    overall_passed: bool = False
    can_write_section: bool = False  # Can proceed to write target section
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "timestamp": self.timestamp,
            "paper_type": self.paper_type,
            "target_section": self.target_section,
            "structure_valid": self.structure_valid,
            "missing_required": self.missing_required,
            "missing_recommended": self.missing_recommended,
            "novelty": {
                "checked": self.novelty_checked,
                "passed": self.novelty_passed,
                "scores": self.novelty_scores,
                "average": self.novelty_average,
                "details": self.novelty_details,
            },
            "selling_points": {
                "checked": self.selling_points_checked,
                "passed": self.selling_points_passed,
                "score": self.selling_points_score,
                "details": self.selling_points_details,
            },
            "consistency": {
                "checked": self.consistency_checked,
                "passed": self.consistency_passed,
                "score": self.consistency_score,
                "issues": self.consistency_issues,
            },
            "citations": {
                "checked": self.citation_checked,
                "score": self.citation_score,
                "unsupported": self.unsupported_claims,
            },
            "overall_passed": self.overall_passed,
            "can_write_section": self.can_write_section,
            "warnings": self.warnings,
            "errors": self.errors,
            "suggestions": self.suggestions,
        }
