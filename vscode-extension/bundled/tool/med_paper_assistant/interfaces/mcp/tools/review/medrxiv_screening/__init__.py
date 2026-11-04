"""
medRxiv Pre-Submission Screening Checks

Automated checks that mirror medRxiv's two-stage screening process:
1. In-house screening (article type, ethics, patient privacy, clinical trial ID)
2. Affiliate screening (health-related research scope, public harm potential)

Called from formatting.py when journal == "medrxiv".
No MCP tools registered here — all checks are called from formatting.py.

Reference: https://www.medrxiv.org/content/about-medrxiv (Screening Process)
"""

from .affiliate import (
    _check_conflict_of_interest,
    _check_public_harm_signals,
    _check_research_scope,
)
from .inhouse import (
    _check_article_type,
    _check_clinical_trial_registration,
    _check_ethics_declaration,
    _check_patient_identification,
)
from .models import ScreeningIssue, ScreeningReport

# ── Public API ───────────────────────────────────────────────────────────


def run_medrxiv_screening(content: str) -> ScreeningReport:
    """Run all medRxiv screening checks on manuscript content.

    Args:
        content: Full manuscript text (Markdown).

    Returns:
        ScreeningReport with all issues found.
    """
    report = ScreeningReport()

    # Stage 1: In-house screening
    _check_article_type(content, report)
    _check_ethics_declaration(content, report)
    _check_patient_identification(content, report)
    _check_clinical_trial_registration(content, report)

    # Stage 2: Affiliate screening
    _check_research_scope(content, report)
    _check_public_harm_signals(content, report)

    # Always required
    _check_conflict_of_interest(content, report)

    return report


__all__ = [
    "ScreeningIssue",
    "ScreeningReport",
    "_check_article_type",
    "_check_clinical_trial_registration",
    "_check_conflict_of_interest",
    "_check_ethics_declaration",
    "_check_patient_identification",
    "_check_public_harm_signals",
    "_check_research_scope",
    "run_medrxiv_screening",
]
