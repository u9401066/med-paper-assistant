"""Novelty evaluation: heuristic round scoring combined with reviewer scores."""

import re
from typing import Dict, List

from ._models import SectionCheck, ValidationResult
from ._novelty_feedback import NoveltyFeedbackMixin

_NOVELTY_KEYWORDS = [
    "first",
    "novel",
    "unique",
    "new",
    "innovative",
    "original",
    "unprecedented",
    "pioneering",
    "breakthrough",
    "首次",
    "創新",
    "獨特",
]
_SPECIFICITY_PATTERNS = [
    r"\d+%",
    r"\d+\s*(patients|subjects|cases|participants)",
    r"compared to",
    r"unlike",
    r"in contrast",
]
_VAGUE_PHRASES = ["improved", "better", "enhanced", "optimized", "更好", "改善", "提升"]
# Only penalize actual unfilled placeholders like [INSERT HERE], [TODO]
_PLACEHOLDER_PATTERN = r"\[(?!\[)[A-Z][A-Z\s_]{2,}\]"


def _positive_novelty_points(content: str, content_lower: str) -> int:
    """Bonus for novelty keywords, specificity and an answered "What is new?"."""
    points = 0

    # Check novelty keywords
    for keyword in _NOVELTY_KEYWORDS:
        if keyword.lower() in content_lower:
            points += 5

    # Check specificity
    for pattern in _SPECIFICITY_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            points += 8

    # Check for "What is new?" answer quality
    if "what is new" in content_lower or "這項研究的新穎之處" in content:
        # Has the question, check if answered
        points += 10

    return points


def _negative_novelty_points(content: str, content_lower: str) -> int:
    """Penalty for unquantified vague phrases and unfilled placeholders."""
    points = 0

    for phrase in _VAGUE_PHRASES:
        if phrase.lower() in content_lower and not any(
            re.search(rf"{phrase}\s+\d+", content, re.IGNORECASE) for _ in [1]
        ):
            # Vague without quantification
            points += 5

    # Check for placeholder text still present
    if re.search(_PLACEHOLDER_PATTERN, content):
        points += 20

    return points


class NoveltyMixin(NoveltyFeedbackMixin):
    """Heuristic (LLM-placeholder) novelty scoring."""

    NOVELTY_CONFIG: Dict[str, int]

    def _evaluate_novelty(self, content: str, result: ValidationResult) -> ValidationResult:
        """
        Evaluate novelty using LLM scoring.

        Note: This is a placeholder for LLM integration.
        In production, this would call the LLM API 3 times.
        For now, it performs heuristic-based scoring.
        """
        result.novelty_checked = True

        # Extract novelty statement
        novelty_content = result.sections.get(
            "novelty_statement", SectionCheck(name="", found=False, has_content=False)
        ).content

        if not novelty_content:
            result.novelty_passed = False
            result.novelty_average = 0
            result.errors.append("Cannot evaluate novelty: NOVELTY STATEMENT is empty")
            return result

        # Heuristic scoring (placeholder for LLM)
        # In production, this would be replaced with actual LLM calls
        scores = []
        for round_num in range(self.NOVELTY_CONFIG["rounds"]):
            score = self._heuristic_novelty_score(novelty_content, round_num)
            scores.append(score)

        result.novelty_scores = scores
        heuristic_avg = sum(scores) / len(scores)
        result.novelty_average = self._combined_novelty_average(result, scores, heuristic_avg)

        # Check if combined score passes threshold
        result.novelty_passed = result.novelty_average >= self.NOVELTY_CONFIG["threshold"]

        # Generate suggestions if not passed
        if not result.novelty_passed:
            result.suggestions.extend(self._generate_novelty_suggestions(novelty_content, scores))
            result.warnings.append(
                f"Novelty check: combined score {result.novelty_average:.1f} "
                f"(threshold: {self.NOVELTY_CONFIG['threshold']})"
            )

        return result

    def _combined_novelty_average(
        self, result: ValidationResult, scores: List[int], heuristic_avg: float
    ) -> float:
        """Blend heuristic and reviewer scores.

        Reviewer scores provide semantic analysis; heuristic provides keyword analysis.
        Use weighted combination: 40% heuristic + 60% reviewer average.
        """
        novelty_content = result.sections.get(
            "novelty_statement", SectionCheck(name="", found=False, has_content=False)
        ).content
        if not novelty_content:
            return heuristic_avg

        feedback = self._generate_novelty_feedback(novelty_content, scores)
        reviewer_scores = [
            feedback["reviewers"]["skeptic"]["score"],
            feedback["reviewers"]["methodologist"]["score"],
            feedback["reviewers"]["clinical_expert"]["score"],
        ]
        reviewer_avg = sum(reviewer_scores) / len(reviewer_scores)
        return 0.4 * heuristic_avg + 0.6 * reviewer_avg

    def _heuristic_novelty_score(self, content: str, round_num: int) -> int:
        """
        Heuristic-based novelty scoring.

        This is a placeholder that will be replaced with LLM scoring.
        It checks for key novelty indicators.
        """
        score = 50  # Base score

        content_lower = content.lower()

        score += _positive_novelty_points(content, content_lower)
        score -= _negative_novelty_points(content, content_lower)

        # Add some variance for different rounds (simulating LLM variance)
        variance = [-3, 0, 3][round_num % 3]
        score += variance

        # Clamp score
        return max(0, min(100, score))
