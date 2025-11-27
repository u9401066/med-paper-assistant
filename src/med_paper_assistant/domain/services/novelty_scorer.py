"""
Novelty Scorer - Domain service for evaluating research novelty.

This module defines the scoring criteria and thresholds for evaluating
whether a research concept truly describes novel contributions.

The scoring system:
- Uses multiple evaluation rounds (default 3) for reliability
- Requires minimum threshold (default 75/100) to pass
- Evaluates multiple dimensions of novelty
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class NoveltyDimension(Enum):
    """Dimensions for evaluating novelty."""
    UNIQUENESS = "uniqueness"           # Is the approach/method unique?
    SIGNIFICANCE = "significance"       # Is the contribution significant?
    GAP_ALIGNMENT = "gap_alignment"     # Does it address an identified gap?
    SPECIFICITY = "specificity"         # Is the novelty claim specific?
    VERIFIABILITY = "verifiability"     # Can the claim be verified?


@dataclass
class NoveltyScore:
    """Score for a single novelty evaluation."""
    dimension: NoveltyDimension
    score: int  # 0-100
    reasoning: str
    suggestions: List[str] = field(default_factory=list)


@dataclass
class NoveltyEvaluation:
    """Complete evaluation result for one round."""
    round_number: int
    total_score: int  # 0-100 (average of dimensions)
    dimension_scores: Dict[str, NoveltyScore] = field(default_factory=dict)
    overall_assessment: str = ""
    is_novel: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "round": self.round_number,
            "total_score": self.total_score,
            "is_novel": self.is_novel,
            "dimensions": {
                k: {
                    "score": v.score,
                    "reasoning": v.reasoning,
                    "suggestions": v.suggestions
                }
                for k, v in self.dimension_scores.items()
            },
            "assessment": self.overall_assessment
        }


@dataclass
class NoveltyVerdict:
    """Final verdict after multiple evaluation rounds."""
    passed: bool
    average_score: float
    rounds: List[NoveltyEvaluation]
    confidence: str  # "high", "medium", "low"
    summary: str
    improvement_suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "average_score": self.average_score,
            "confidence": self.confidence,
            "summary": self.summary,
            "rounds": [r.to_dict() for r in self.rounds],
            "suggestions": self.improvement_suggestions
        }


# Default scoring configuration
DEFAULT_SCORING_CONFIG = {
    "min_rounds": 3,
    "passing_threshold": 75,
    "required_passing_rounds": 3,  # All rounds must pass
    "dimension_weights": {
        NoveltyDimension.UNIQUENESS: 0.25,
        NoveltyDimension.SIGNIFICANCE: 0.25,
        NoveltyDimension.GAP_ALIGNMENT: 0.20,
        NoveltyDimension.SPECIFICITY: 0.15,
        NoveltyDimension.VERIFIABILITY: 0.15,
    }
}


# Scoring prompts for LLM evaluation
NOVELTY_SCORING_PROMPT = """You are an expert research reviewer evaluating the NOVELTY of a research concept.

## Research Concept to Evaluate:
{concept_content}

## Evaluation Instructions:
Score each dimension from 0-100, where:
- 0-30: Poor/Missing - Claim is vague, generic, or not novel
- 31-50: Weak - Some novelty but not well articulated
- 51-70: Moderate - Clear novelty but could be stronger
- 71-85: Good - Well-defined novel contribution
- 86-100: Excellent - Highly innovative and clearly articulated

## Dimensions to Evaluate:

1. **UNIQUENESS** (25%): Is this approach/method/perspective unique?
   - Does it differ from existing work?
   - Is there a clear "first" or "new" element?

2. **SIGNIFICANCE** (25%): Is the contribution meaningful?
   - Will it advance the field?
   - Does it solve an important problem?

3. **GAP_ALIGNMENT** (20%): Does novelty address the identified research gap?
   - Is the gap clearly defined?
   - Does the novelty directly fill this gap?

4. **SPECIFICITY** (15%): Is the novelty claim specific and concrete?
   - Avoids vague terms like "better", "improved", "novel"?
   - States exactly what is new?

5. **VERIFIABILITY** (15%): Can the novelty claim be verified?
   - Can it be tested or demonstrated?
   - Are there measurable outcomes?

## Response Format (JSON):
{{
    "uniqueness": {{"score": <0-100>, "reasoning": "<why>", "suggestions": ["<improvement>"]}},
    "significance": {{"score": <0-100>, "reasoning": "<why>", "suggestions": ["<improvement>"]}},
    "gap_alignment": {{"score": <0-100>, "reasoning": "<why>", "suggestions": ["<improvement>"]}},
    "specificity": {{"score": <0-100>, "reasoning": "<why>", "suggestions": ["<improvement>"]}},
    "verifiability": {{"score": <0-100>, "reasoning": "<why>", "suggestions": ["<improvement>"]}},
    "overall_assessment": "<1-2 sentence summary>",
    "total_score": <weighted average 0-100>
}}
"""


SELLING_POINTS_SCORING_PROMPT = """You are evaluating the QUALITY of KEY SELLING POINTS in a research concept.

## Selling Points to Evaluate:
{selling_points}

## Criteria for Good Selling Points:
1. **Specific** - Not vague ("improves outcomes" → "reduces complication rate by 20%")
2. **Measurable** - Has quantifiable elements
3. **Unique** - Differentiates from existing work
4. **Impactful** - Matters to the target audience
5. **Supported** - Can be backed by evidence

## Score each selling point (0-100):
- 0-30: Vague, generic, or weak
- 31-50: Some merit but needs improvement
- 51-70: Acceptable with minor issues
- 71-85: Strong and well-articulated
- 86-100: Excellent, compelling, and specific

## Response Format (JSON):
{{
    "selling_points": [
        {{"text": "<point>", "score": <0-100>, "issues": ["<problem>"], "improved": "<better version>"}},
        ...
    ],
    "average_score": <0-100>,
    "overall_quality": "<assessment>",
    "recommendations": ["<suggestion>"]
}}
"""


CONSISTENCY_CHECK_PROMPT = """You are checking the CONSISTENCY between different sections of a research concept.

## Sections to Check:

### NOVELTY STATEMENT:
{novelty_statement}

### RESEARCH GAP:
{research_gap}

### KEY SELLING POINTS:
{selling_points}

### EXPECTED OUTCOMES:
{expected_outcomes}

## Consistency Checks:

1. **Gap-Novelty Alignment**: Does the novelty address the identified gap?
2. **Novelty-Selling Points**: Do selling points reflect the novelty claim?
3. **Selling Points-Outcomes**: Do expected outcomes support the selling points?
4. **Internal Coherence**: No contradictions between sections?

## Response Format (JSON):
{{
    "gap_novelty_alignment": {{"score": <0-100>, "issues": ["<problem>"], "suggestion": "<fix>"}},
    "novelty_selling_alignment": {{"score": <0-100>, "issues": ["<problem>"], "suggestion": "<fix>"}},
    "selling_outcomes_alignment": {{"score": <0-100>, "issues": ["<problem>"], "suggestion": "<fix>"}},
    "internal_coherence": {{"score": <0-100>, "issues": ["<problem>"], "suggestion": "<fix>"}},
    "overall_consistency_score": <0-100>,
    "is_consistent": <true/false>,
    "critical_issues": ["<issue>"],
    "recommendations": ["<fix>"]
}}
"""


CITATION_SUPPORT_PROMPT = """You are checking if research claims are properly SUPPORTED by citations.

## Content to Check:
{content}

## Available References:
{references}

## Check for:
1. Claims about "current knowledge" - should have citations
2. Claims about "gaps in literature" - should reference what's missing
3. Statistical claims - should be cited
4. Comparisons to existing methods - should cite those methods

## Response Format (JSON):
{{
    "unsupported_claims": [
        {{"claim": "<text>", "location": "<section>", "severity": "high|medium|low", "suggestion": "<how to support>"}}
    ],
    "well_supported_claims": ["<claim>"],
    "citation_coverage_score": <0-100>,
    "recommendations": ["<suggestion>"]
}}
"""
