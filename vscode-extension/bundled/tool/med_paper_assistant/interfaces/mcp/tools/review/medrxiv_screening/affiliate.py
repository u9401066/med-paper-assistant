"""Stage 2 medRxiv screening: affiliate checks (scope, public harm) and COI."""

import re

from .models import ScreeningReport
from .patterns import COI_PATTERNS, HARM_PATTERNS, HEALTH_TERMS


def _check_research_scope(content: str, report: ScreeningReport) -> None:
    """Verify the manuscript is health-related research with methods and data.

    medRxiv Affiliates ask: Is this health-related clinical research that
    includes methods and data?
    """
    content_lower = content.lower()

    # Must have methods and some form of data/results
    has_methods = bool(re.search(r"^#{1,3}\s+methods", content_lower, re.MULTILINE))
    has_results = bool(re.search(r"^#{1,3}\s+results", content_lower, re.MULTILINE))
    has_data = has_results or bool(
        re.search(r"(?:data\s+(?:collect|analys|extract))", content_lower)
    )

    if not has_methods:
        report.add(
            category="Research Scope",
            severity="error",
            description="No Methods section detected — medRxiv requires research with methods.",
        )
    if not has_data:
        report.add(
            category="Research Scope",
            severity="warning",
            description=(
                "No Results section or data analysis description detected. "
                "medRxiv requires clinical research with data."
            ),
        )

    health_hits = sum(1 for t in HEALTH_TERMS if re.search(t, content_lower))
    if health_hits < 2:
        report.add(
            category="Research Scope",
            severity="warning",
            description=(
                f"Only {health_hits} health-related terms detected. "
                "medRxiv is for health and clinical research only."
            ),
            suggestion="Verify the manuscript is in scope for medRxiv (not bioRxiv).",
        )


def _check_public_harm_signals(content: str, report: ScreeningReport) -> None:
    """Flag content that may raise public-harm concerns during screening.

    medRxiv screens for content that might encourage reduced compliance
    with critical public health measures, or make unsubstantiated
    therapeutic claims.

    This is a heuristic check — flags for human review, not definitive rejection.
    """
    content_lower = content.lower()

    for pattern, label in HARM_PATTERNS:
        if re.search(pattern, content_lower):
            report.add(
                category="Public Harm Screening",
                severity="warning",
                description=f"Potential concern: {label}.",
                suggestion=(
                    "This may trigger medRxiv escalation review. "
                    "Ensure claims are evidence-based and contextualized."
                ),
            )


def _check_conflict_of_interest(content: str, report: ScreeningReport) -> None:
    """Check for conflict of interest / competing interests statement.

    medRxiv requires a competing interests declaration.
    """
    found = any(re.search(p, content, re.IGNORECASE) for p in COI_PATTERNS)

    if not found:
        report.add(
            category="Conflict of Interest",
            severity="error",
            description=(
                "No conflict of interest / competing interests statement detected. "
                "medRxiv requires a competing interests declaration."
            ),
            suggestion='Add "Conflict of Interest: The authors declare no competing interests."',
        )
