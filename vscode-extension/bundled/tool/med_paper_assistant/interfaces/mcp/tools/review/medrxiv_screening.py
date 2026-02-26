"""
medRxiv Pre-Submission Screening Checks

Automated checks that mirror medRxiv's two-stage screening process:
1. In-house screening (article type, ethics, patient privacy, clinical trial ID)
2. Affiliate screening (health-related research scope, public harm potential)

Called from formatting.py when journal == "medrxiv".
No MCP tools registered here — all checks are called from formatting.py.

Reference: https://www.medrxiv.org/content/about-medrxiv (Screening Process)
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScreeningIssue:
    """A single medRxiv screening issue."""

    category: str
    severity: str  # "error", "warning", "info"
    description: str
    suggestion: Optional[str] = None


@dataclass
class ScreeningReport:
    """Aggregated medRxiv screening report."""

    issues: list[ScreeningIssue] = field(default_factory=list)

    def add(
        self,
        category: str,
        severity: str,
        description: str,
        suggestion: Optional[str] = None,
    ):
        self.issues.append(
            ScreeningIssue(
                category=category,
                severity=severity,
                description=description,
                suggestion=suggestion,
            )
        )

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def to_summary(self) -> str:
        """One-line summary for embedding in check_formatting report."""
        total = len(self.issues)
        if total == 0:
            return "✅ All medRxiv screening checks passed"
        return (
            f"❌ {self.error_count} errors, ⚠️ {self.warning_count} warnings, "
            f"ℹ️ {total - self.error_count - self.warning_count} info"
        )


# ── Stage 1: In-house screening ─────────────────────────────────────────


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

    # Negative signals: title/heading patterns suggesting disallowed types
    disallowed_patterns = [
        (r"(?:narrative|scoping|umbrella)\s+review", "narrative/scoping/umbrella review"),
        (r"^#{1,3}\s+(?:commentary|editorial|opinion)", "commentary/editorial/opinion"),
        (r"(?:letter\s+to\s+(?:the\s+)?editor)", "letter to the editor"),
        (r"^#{1,3}\s+case\s+(?:report|series)", "case report/series"),
    ]
    for pattern, label in disallowed_patterns:
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
    ethics_patterns = [
        r"(?:IRB|institutional\s+review\s+board)",
        r"(?:ethic(?:s|al)\s+(?:committee|approval|review|board|oversight))",
        r"(?:ethic(?:s|al)(?:ly)?\s+(?:approved|exempt|waived))",
        r"(?:informed\s+consent)",
        r"(?:Helsinki\s+Declaration)",
        r"(?:approval\s+(?:number|no\.?|#)\s*[:=]?\s*\w+)",
        r"(?:exempt(?:ion|ed)?\s+(?:from|by)\s+(?:IRB|ethic))",
    ]

    found = any(re.search(p, content, re.IGNORECASE) for p in ethics_patterns)

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
    id_patterns = [
        # Exact age with context suggesting individual patient
        (
            r"\b(\d{1,3})\s*-?\s*year\s*-?\s*old\s+(?:male|female|man|woman|boy|girl|patient)",
            "Specific age with patient description",
            "warning",
        ),
        # Exact dates of admission/visit (DD/MM/YYYY or Month DD, YYYY patterns)
        (
            r"(?:admitted|presented|visited|seen)\s+(?:on|in)\s+"
            r"(?:January|February|March|April|May|June|July|August|September|"
            r"October|November|December)\s+\d{1,2},?\s+\d{4}",
            "Specific date of clinical encounter",
            "warning",
        ),
        # Hospital + specific location that could identify a patient
        (
            r"(?:patient|subject)\s+(?:from|in|at)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}"
            r"\s+(?:Hospital|Clinic|Medical\s+Center)",
            "Patient linked to specific institution",
            "info",
        ),
        # Family identifiers in case context
        (
            r"(?:patient's|proband's)\s+(?:mother|father|sister|brother|daughter|son|spouse|wife|husband)",
            "Family relationship identifier",
            "info",
        ),
        # Pedigree / genealogy data
        (
            r"(?:pedigree|genealog|family\s+tree)",
            "Pedigree/genealogy data detected",
            "info",
        ),
    ]

    found_any = False
    for pattern, label, severity in id_patterns:
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

    # Detect if this is an interventional study
    intervention_signals = [
        r"(?:randomized|randomised)\s+(?:controlled\s+)?trial",
        r"clinical\s+trial",
        r"prospective(?:ly)?\s+assign",
        r"(?:intervention|treatment)\s+(?:group|arm)",
        r"(?:placebo|control)\s+(?:group|arm)",
        r"randomiz(?:ed|ation)\s+(?:to|into)",
    ]

    is_interventional = any(re.search(p, content_lower) for p in intervention_signals)

    if not is_interventional:
        return

    # Look for trial registration numbers
    trial_id_patterns = [
        r"NCT\d{8}",  # ClinicalTrials.gov
        r"ISRCTN\d{8,}",  # ISRCTN Registry
        r"(?:ACTRN|ANZCTR)\d{14}",  # Australian NZ
        r"ChiCTR[-\s]?\d+",  # Chinese Registry
        r"CTRI/\d{4}/\d+/\d+",  # India CTRI
        r"DRKS\d{8}",  # German Registry
        r"EUCTR\d{4}-\d{6}-\d{2}",  # EU Clinical Trials
        r"IRCT\d{14,}N?\d*",  # Iran Registry
        r"JPRN[-\s]?\w+",  # Japan Registry
        r"KCT\d{7}",  # Korean Registry
        r"NTR\d{4,}",  # Netherlands
        r"PACTR\d{15,}",  # Pan African
        r"(?:RBR|UTN)\s*[-:]?\s*\w{6,}",  # Brazil / UTN
        r"SLCTR/\d{4}/\d+",  # Sri Lanka
        r"TCTR\d{11}",  # Thailand
    ]

    has_trial_id = any(re.search(p, content, re.IGNORECASE) for p in trial_id_patterns)

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


# ── Stage 2: Affiliate screening ────────────────────────────────────────


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

    # Health-related check: look for medical/health terms
    health_terms = [
        r"patient",
        r"clinical",
        r"treatment",
        r"diagnosis",
        r"disease",
        r"health",
        r"medical",
        r"hospital",
        r"surgery|surgical",
        r"therap(?:y|eutic)",
        r"epidemic|pandemic",
        r"mortality|morbidity",
        r"public\s+health",
        r"epidemiolog",
    ]
    health_hits = sum(1 for t in health_terms if re.search(t, content_lower))
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

    harm_patterns = [
        # Anti-public-health-measure language
        (
            r"(?:masks?\s+(?:are\s+)?(?:ineffective|useless|harmful|unnecessary))",
            "Statement questioning mask effectiveness",
        ),
        (
            r"(?:vaccin(?:e|ation)s?\s+(?:are\s+)?(?:dangerous|harmful|cause|causing))",
            "Statement about vaccine harm",
        ),
        (
            r"(?:lockdowns?\s+(?:are\s+)?(?:ineffective|useless|harmful|unnecessary))",
            "Statement questioning lockdown effectiveness",
        ),
        # Unsubstantiated therapeutic claims
        (
            r"(?:(?:cure|cures|cured)\s+(?:for\s+)?(?:cancer|COVID|HIV|diabetes|alzheimer))",
            "Claim of cure for major disease",
        ),
        (
            r"(?:miracle\s+(?:cure|treatment|drug|remedy))",
            "Miracle cure/treatment language",
        ),
        # Conspiracy theory language
        (
            r"(?:(?:big\s+pharma|government)\s+(?:cover.?up|conspiracy|hiding))",
            "Conspiracy-adjacent language",
        ),
    ]

    for pattern, label in harm_patterns:
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
    coi_patterns = [
        r"(?:conflict(?:s)?\s+of\s+interest)",
        r"(?:competing\s+interests?)",
        r"(?:disclosure(?:s)?(?:\s+statement)?)",
        r"(?:(?:no|none)\s+(?:conflicts?|competing))",
        r"(?:financial\s+(?:disclosure|interest))",
    ]

    found = any(re.search(p, content, re.IGNORECASE) for p in coi_patterns)

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
