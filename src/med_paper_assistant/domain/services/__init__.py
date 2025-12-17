"""
Domain Services

Domain services encapsulate business logic that doesn't naturally fit
within a single entity or value object.
"""

from .citation_formatter import CitationFormatter
from .novelty_scorer import (
    NoveltyDimension,
    NoveltyScore,
    NoveltyEvaluation,
    NoveltyVerdict,
    DEFAULT_SCORING_CONFIG,
    NOVELTY_SCORING_PROMPT,
    SELLING_POINTS_SCORING_PROMPT,
    CONSISTENCY_CHECK_PROMPT,
    CITATION_SUPPORT_PROMPT,
)
from .reference_converter import (
    ReferenceConverter,
    StandardizedReference,
    reference_converter,
)
from .wikilink_validator import (
    WikilinkIssue,
    WikilinkValidationResult,
    validate_wikilink,
    validate_wikilinks_in_content,
    validate_wikilinks_in_file,
    find_citation_key_for_pmid,
)
from .pre_analysis_checklist import (
    CheckStatus,
    CheckItem,
    ChecklistResult,
    PreAnalysisChecker,
    check_pre_analysis_readiness,
    check_pre_analysis_file,
)

__all__ = [
    "CitationFormatter",
    "NoveltyDimension",
    "NoveltyScore",
    "NoveltyEvaluation",
    "NoveltyVerdict",
    "DEFAULT_SCORING_CONFIG",
    "NOVELTY_SCORING_PROMPT",
    "SELLING_POINTS_SCORING_PROMPT",
    "CONSISTENCY_CHECK_PROMPT",
    "CITATION_SUPPORT_PROMPT",
    # Reference conversion
    "ReferenceConverter",
    "StandardizedReference",
    "reference_converter",
    # Wikilink validation
    "WikilinkIssue",
    "WikilinkValidationResult",
    "validate_wikilink",
    "validate_wikilinks_in_content",
    "validate_wikilinks_in_file",
    "find_citation_key_for_pmid",
    # Pre-analysis checklist
    "CheckStatus",
    "CheckItem",
    "ChecklistResult",
    "PreAnalysisChecker",
    "check_pre_analysis_readiness",
    "check_pre_analysis_file",
]
