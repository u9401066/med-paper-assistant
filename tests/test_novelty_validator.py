"""Contract tests for ConceptValidator novelty scoring.

Validates that:
1. Wikilinks [[...]] and PubMed syntax [pt] do NOT trigger placeholder penalty
2. Actual placeholders [INSERT HERE] DO trigger penalty
3. Overall score incorporates reviewer scores (not heuristic only)
4. Methodologist detects limitation patterns beyond just "but"
5. Scores are consistent (reviewer avg vs overall are not wildly divergent)
"""

import re
import pytest
import sys

sys.path.insert(0, "src")

from med_paper_assistant.infrastructure.services.concept_validator import ConceptValidator


@pytest.fixture
def validator():
    return ConceptValidator()


@pytest.fixture
def strong_novelty_content():
    """Content with citations, limitation analysis, PubMed evidence."""
    return """This review is the first to:
1. Systematically compare diagnostic accuracy across three paradigms
2. Propose a hierarchical prediction framework

### Explicit Differentiation
- **Detsky 2019** [[detsky2019_30721300]]: *Limitation* — Only covers bedside tests.
  Does not include AI/ML or ultrasound. *Our addition* — We extend to include 12+ AI studies.
- **Carsetti 2022** [[carsetti2022_34914641]]: *Limitation* — Restricted to ultrasound only.
  *Our addition* — We place ultrasound in direct comparison with clinical and AI methods.

### Search Evidence
PubMed search (2026-02-23): 112 results, 0 multi-paradigm reviews found."""


@pytest.fixture
def weak_novelty_content():
    """Content with no citations, no evidence."""
    return "We present a new approach that is better and improved."


@pytest.fixture
def placeholder_content():
    """Content with actual unfilled placeholders."""
    return "This is [INSERT METHODOLOGY HERE] and [TODO ADD REFS]"


class TestHeuristicScoring:
    """Bug #1: Wikilinks should not be penalized as placeholders."""

    def test_wikilinks_not_penalized(self, validator, strong_novelty_content):
        """[[wikilinks]] should NOT trigger the -20 placeholder penalty."""
        score = validator._heuristic_novelty_score(strong_novelty_content, 0)
        # With wikilinks, score should be >= 50 base (no penalty applied)
        assert score >= 50, f"Wikilinks triggered false penalty: score={score}"

    def test_pubmed_syntax_not_penalized(self, validator):
        """PubMed search syntax [pt] should NOT trigger placeholder penalty."""
        content = 'PubMed search: "airway"[pt] AND "prediction"[MeSH]'
        score = validator._heuristic_novelty_score(content, 0)
        assert score >= 45, f"PubMed syntax triggered false penalty: score={score}"

    def test_actual_placeholders_penalized(self, validator, placeholder_content):
        """Real placeholders like [INSERT HERE] SHOULD be penalized."""
        score = validator._heuristic_novelty_score(placeholder_content, 0)
        assert score < 40, f"Placeholders not penalized: score={score}"

    def test_novelty_keywords_add_score(self, validator):
        """Presence of 'first', 'novel' etc. should increase score."""
        base = validator._heuristic_novelty_score("Some generic text about methods", 0)
        with_keywords = validator._heuristic_novelty_score(
            "This is the first novel approach", 0
        )
        assert with_keywords > base

    def test_score_clamped_0_100(self, validator):
        """Score should always be between 0 and 100."""
        for i in range(3):
            score = validator._heuristic_novelty_score("", i)
            assert 0 <= score <= 100


class TestMethodologistScoring:
    """Bug #3: Methodologist should detect limitation analysis, not just 'but'."""

    def test_limitation_patterns_detected(self, validator, strong_novelty_content):
        """Content with Limitation/Our addition should score high."""
        fb = validator._generate_novelty_feedback(strong_novelty_content, [70, 70, 70])
        meth_score = fb["reviewers"]["methodologist"]["score"]
        assert meth_score >= 75, (
            f"Methodologist failed to detect limitation analysis: {meth_score}, "
            f"comment: {fb['reviewers']['methodologist']['comment']}"
        )

    def test_no_citations_scores_low(self, validator, weak_novelty_content):
        """Content without citations should score low."""
        fb = validator._generate_novelty_feedback(weak_novelty_content, [40, 40, 40])
        meth_score = fb["reviewers"]["methodologist"]["score"]
        assert meth_score <= 60

    def test_citations_but_no_analysis_scores_medium(self, validator):
        """Content with citations but no limitation discussion."""
        content = "We build on [[some_ref_123]] and [[another_456]]."
        fb = validator._generate_novelty_feedback(content, [60, 60, 60])
        meth_score = fb["reviewers"]["methodologist"]["score"]
        assert 55 <= meth_score <= 70

    def test_does_not_keyword_counts_as_limitation(self, validator):
        """'Does not' should be detected as limitation language."""
        content = "[[ref1_123]]: Does not compare with AI. Our addition: We compare all three."
        fb = validator._generate_novelty_feedback(content, [60, 60, 60])
        meth_score = fb["reviewers"]["methodologist"]["score"]
        assert meth_score >= 75


class TestCombinedScoring:
    """Bug #2: Overall score should incorporate reviewer scores."""

    def test_overall_reflects_reviewer_scores(self, validator, strong_novelty_content):
        """When reviewers give high scores, overall should not be stuck at ~48."""
        fb = validator._generate_novelty_feedback(strong_novelty_content, [65, 65, 65])
        r_scores = [
            fb["reviewers"]["skeptic"]["score"],
            fb["reviewers"]["methodologist"]["score"],
            fb["reviewers"]["clinical_expert"]["score"],
        ]
        r_avg = sum(r_scores) / len(r_scores)
        h_avg = sum(
            validator._heuristic_novelty_score(strong_novelty_content, i) for i in range(3)
        ) / 3

        combined = 0.4 * h_avg + 0.6 * r_avg

        # Combined should be higher than pure heuristic when reviewers score well
        assert combined > h_avg, (
            f"Combined ({combined:.1f}) should exceed heuristic ({h_avg:.1f}) "
            f"when reviewer avg is {r_avg:.1f}"
        )

    def test_overall_not_wildly_divergent_from_reviewers(
        self, validator, strong_novelty_content
    ):
        """Overall score should not differ from reviewer avg by more than 30 points."""
        fb = validator._generate_novelty_feedback(strong_novelty_content, [70, 70, 70])
        r_scores = [
            fb["reviewers"]["skeptic"]["score"],
            fb["reviewers"]["methodologist"]["score"],
            fb["reviewers"]["clinical_expert"]["score"],
        ]
        r_avg = sum(r_scores) / len(r_scores)
        h_avg = sum(
            validator._heuristic_novelty_score(strong_novelty_content, i) for i in range(3)
        ) / 3
        combined = 0.4 * h_avg + 0.6 * r_avg

        assert abs(combined - r_avg) <= 30, (
            f"Combined ({combined:.1f}) diverges too much from reviewer avg ({r_avg:.1f})"
        )


class TestSkepticScoring:
    """Skeptic should correctly detect PubMed evidence."""

    def test_pubmed_evidence_gives_high_score(self, validator, strong_novelty_content):
        fb = validator._generate_novelty_feedback(strong_novelty_content, [70, 70, 70])
        assert fb["reviewers"]["skeptic"]["score"] >= 75

    def test_no_pubmed_with_first_claim_gives_low_score(self, validator):
        content = "This is the first study to do X."
        fb = validator._generate_novelty_feedback(content, [50, 50, 50])
        assert fb["reviewers"]["skeptic"]["score"] <= 55
