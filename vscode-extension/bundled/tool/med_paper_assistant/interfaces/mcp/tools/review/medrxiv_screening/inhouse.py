"""Stage 1 medRxiv screening: in-house checks (article type, ethics, privacy, trial ID)."""

import re

from .models import ScreeningReport
from .patterns import (
    DISALLOWED_ARTICLE_PATTERNS,
    ETHICS_PATTERNS,
    INTERVENTION_SIGNALS,
    PATIENT_ID_PATTERNS,
    TRIAL_ID_PATTERNS,
)


def _check_article_type(content: str, report: ScreeningReport) -> None:
    """Check that the manuscript is an acceptable article type for medRxiv.

    Acceptable: research manuscript, clinical research design protocol.
    Not acceptable: narrative review, commentary, opinion, case report/series,
                    editorial, letter to editor.
    """
    content_lower = content.lower()

    # Positive signals: has Methods + Results sections → research manuscript
    has_methods = bool(re.search(r"^#{1,3}\s+methods", content_lower, re.MULTILINE))
    has_results = bool(re.search(r"^#{1,3}\s+results", content_lower, re.MULTILINE))

    if not has_methods or not has_results:
        report.add(
            category="Article Type",
            severity="error",
            description=(
                "Missing Methods and/or Results sections. "
                "medRxiv only accepts research manuscripts or clinical protocols."
            ),
            suggestion="Ensure the manuscript has both Methods and Results sections.",
        )
        return

    for pattern, label in DISALLOWED_ARTICLE_PATTERNS:
        if re.search(pattern, content_lower, re.MULTILINE):
            report.add(
                category="Article Type",
                severity="warning",
                description=(
                    f"Manuscript may be a {label}. medRxiv does not accept this article type."
                ),
                suggestion="Verify this is a research manuscript with original data.",
            )
            return

    # Protocol detection: acceptable but flag for awareness
    if re.search(r"(?:study|trial|research)\s+protocol", content_lower):
        report.add(
            category="Article Type",
            severity="info",
            description="Manuscript appears to be a research protocol (acceptable for medRxiv).",
        )


def _check_ethics_declaration(content: str, report: ScreeningReport) -> None:
    """Check for ethics/IRB approval or exemption statement.

    medRxiv requires appropriate details of ethical oversight approval/exemption.
    """
    found = any(re.search(p, content, re.IGNORECASE) for p in ETHICS_PATTERNS)

    if not found:
        report.add(
            category="Ethics Declaration",
            severity="error",
            description=(
                "No ethics/IRB approval or exemption statement detected. "
                "medRxiv requires details of ethical oversight."
            ),
            suggestion=(
                "Add a statement about IRB approval (with approval number) "
                "or ethics committee exemption."
            ),
        )
    else:
        # Check for approval number specificity
        has_number = bool(
            re.search(
                r"(?:approval|protocol|IRB)\s*(?:number|no\.?|#)\s*[:=]?\s*[A-Z0-9-]+",
                content,
                re.IGNORECASE,
            )
        )
        if not has_number:
            report.add(
                category="Ethics Declaration",
                severity="info",
                description=(
                    "Ethics statement found but no specific approval number detected. "
                    "Consider including the IRB/ethics approval number."
                ),
            )


def _check_patient_identification(content: str, report: ScreeningReport) -> None:
    """Screen for potentially identifying patient/participant information.

    medRxiv checks for: photographs, exact ages, locations, identifying
    medical conditions, travel histories, family relationship identifiers,
    or identifying pedigree data.
    """
    found_any = False
    for pattern, label, severity in PATIENT_ID_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            found_any = True
            report.add(
                category="Patient Privacy",
                severity=severity,
                description=f"{label} — found {len(matches)} instance(s).",
                suggestion="Verify no identifiable patient information is present.",
            )

    if not found_any:
        # Image references (can't check actual images, but flag references)
        if re.search(
            r"(?:photograph|photo(?:graph)?s?\s+of\s+(?:the\s+)?patient)", content, re.IGNORECASE
        ):
            report.add(
                category="Patient Privacy",
                severity="warning",
                description="Reference to patient photograph detected.",
                suggestion="Ensure patient photos are de-identified or consented.",
            )


def _check_clinical_trial_registration(content: str, report: ScreeningReport) -> None:
    """Check for clinical trial registration number if study is interventional.

    medRxiv requires a clinical trial ID for any research that prospectively
    assigns people to an intervention to study health outcomes.
    """
    content_lower = content.lower()

    is_interventional = any(re.search(p, content_lower) for p in INTERVENTION_SIGNALS)

    if not is_interventional:
        return

    has_trial_id = any(re.search(p, content, re.IGNORECASE) for p in TRIAL_ID_PATTERNS)

    if not has_trial_id:
        report.add(
            category="Clinical Trial Registration",
            severity="error",
            description=(
                "Manuscript describes an interventional study but no clinical trial "
                "registration number (e.g., NCT, ISRCTN) was detected."
            ),
            suggestion=(
                "Register the trial in a recognized registry "
                "(ClinicalTrials.gov, ISRCTN, WHO ICTRP partner, etc.) "
                "and include the registration number."
            ),
        )
    else:
        report.add(
            category="Clinical Trial Registration",
            severity="info",
            description="Clinical trial registration number detected.",
        )
