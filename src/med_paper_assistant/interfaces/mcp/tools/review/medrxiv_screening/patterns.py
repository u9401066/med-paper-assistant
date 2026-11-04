"""Regex pattern tables used by the medRxiv screening checks."""

# Negative signals: title/heading patterns suggesting disallowed article types
DISALLOWED_ARTICLE_PATTERNS = [
    (r"(?:narrative|scoping|umbrella)\s+review", "narrative/scoping/umbrella review"),
    (r"^#{1,3}\s+(?:commentary|editorial|opinion)", "commentary/editorial/opinion"),
    (r"(?:letter\s+to\s+(?:the\s+)?editor)", "letter to the editor"),
    (r"^#{1,3}\s+case\s+(?:report|series)", "case report/series"),
]

ETHICS_PATTERNS = [
    r"(?:IRB|institutional\s+review\s+board)",
    r"(?:ethic(?:s|al)\s+(?:committee|approval|review|board|oversight))",
    r"(?:ethic(?:s|al)(?:ly)?\s+(?:approved|exempt|waived))",
    r"(?:informed\s+consent)",
    r"(?:Helsinki\s+Declaration)",
    r"(?:approval\s+(?:number|no\.?|#)\s*[:=]?\s*\w+)",
    r"(?:exempt(?:ion|ed)?\s+(?:from|by)\s+(?:IRB|ethic))",
]

PATIENT_ID_PATTERNS = [
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

# Detect if this is an interventional study
INTERVENTION_SIGNALS = [
    r"(?:randomized|randomised)\s+(?:controlled\s+)?trial",
    r"clinical\s+trial",
    r"prospective(?:ly)?\s+assign",
    r"(?:intervention|treatment)\s+(?:group|arm)",
    r"(?:placebo|control)\s+(?:group|arm)",
    r"randomiz(?:ed|ation)\s+(?:to|into)",
]

# Look for trial registration numbers
TRIAL_ID_PATTERNS = [
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

# Health-related check: look for medical/health terms
HEALTH_TERMS = [
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

HARM_PATTERNS = [
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

COI_PATTERNS = [
    r"(?:conflict(?:s)?\s+of\s+interest)",
    r"(?:competing\s+interests?)",
    r"(?:disclosure(?:s)?(?:\s+statement)?)",
    r"(?:(?:no|none)\s+(?:conflicts?|competing))",
    r"(?:financial\s+(?:disclosure|interest))",
]
