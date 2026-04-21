"""
Writing Hooks — Module-level constants.

Constants shared across all hook series (A, B, C, F, P, G).
"""

from __future__ import annotations

# ── Anti-AI phrase list (A3 / P2) ──────────────────────────────────
# Union of: auto-paper SKILL.md A3 (7), git-precommit SKILL.md P2 (10),
# DomainConstraintEngine V002 (16), + expanded AI-detection corpus.
# Deduplicated. Keep sorted by category.

ANTI_AI_PHRASES: list[str] = [
    # ── Classic AI filler ──
    "in recent years",
    "it is worth noting",
    "it is important to note",
    "it should be noted",
    "it is widely recognized",
    "it is imperative",
    "it is essential to",
    "it is well established",
    # ── Grandiose / buzzword (Pattern 1: Significance inflation) ──
    "plays a crucial role",
    "plays a vital role",
    "plays a pivotal role",
    "pivotal role",
    "has garnered significant attention",
    "a comprehensive understanding",
    "comprehensive overview",
    "this groundbreaking",
    "groundbreaking",
    "cutting-edge",
    "state-of-the-art",
    "paradigm shift",
    "game-changer",
    "indelible mark",
    "deeply rooted",
    "focal point",
    "key turning point",
    "setting the stage for",
    "marking a pivotal moment",
    "enduring testament",
    "evolving landscape",
    "enduring legacy",
    "profound impact",
    # ── Metaphorical cliché ──
    "delve into",
    "shed light on",
    "pave the way",
    "a myriad of",
    "in the realm of",
    "a testament to",
    "at the forefront",
    "the landscape of",
    "cornerstone of",
    "tapestry of",
    "stands as",
    "rich tapestry",
    "intricate tapestry",
    "vibrant tapestry",
    # ── Promotional language (Pattern 4) ──
    "breathtaking",
    "must-visit",
    "nestled in",
    "in the heart of",
    "natural beauty",
    "boasts a",
    "exemplifies",
    "commitment to excellence",
    # ── Vague academic padding ──
    "multifaceted",
    "underscores the importance",
    "underscores the need",
    "highlights the importance",
    "notably",
    "leveraging",
    "utilizing",
    "a growing body of evidence",
    "has emerged as",
    "increasingly recognized",
    "is of paramount importance",
    "remains an area of active research",
    "warrants further investigation",
    "merits further investigation",
    "nuanced understanding",
    "robust framework",
    "holistic approach",
    # ── AI vocabulary (Pattern 7: High-frequency AI words) ──
    "aligns with",
    "underscores",
    "fostering",
    "showcasing",
    "intricate",
    "intricacies",
    "interplay of",
    "pivotal",
    # ── Copula avoidance (Pattern 8) ──
    "serves as a",
    "stands as a",
    "functions as a",
    # ── Formulaic conclusion / transition ──
    "in conclusion, our study",
    "in summary, this study",
    "taken together, these findings",
    "in light of these findings",
    "despite these challenges",
    "to the best of our knowledge",
    "first and foremost",
    "a deeper understanding",
    "this study adds to the growing literature",
    "this highlights the need",
    "the importance of this cannot be overstated",
    # ── Generic conclusions (Pattern 24) ──
    "the future looks bright",
    "exciting times lie ahead",
    "continues to thrive",
    "journey toward excellence",
    "as we move forward",
    "continues to evolve",
    # ── AI-specific phrasing patterns ──
    "demonstrate the efficacy",
    "elucidate the mechanisms",
    "elucidating",
    "meticulous",
    "bolster",
    "a critical aspect",
    "serve as a foundation",
    "offers a promising avenue",
    # ── Filler phrases (Pattern 22) ──
    "in order to",
    "due to the fact that",
    "at this point in time",
    "in the event that",
    "has the ability to",
    "it goes without saying",
    "needless to say",
    # ── Chatbot artifacts (Pattern 19) ──
    "i hope this helps",
    "let me know if",
    "here is a comprehensive",
    "here's a comprehensive",
    # ── Cutoff disclaimers (Pattern 20) ──
    "while details are limited",
    "based on available information",
    "as of my last",
    # ── Sycophantic tone (Pattern 21) ──
    "great question",
    "excellent point",
    # ── Vague attributions (Pattern 5) ──
    "many scholars argue",
    "experts believe",
    "it is widely believed",
    "according to many",
    "some researchers suggest",
]

# These phrases are only flagged at paragraph start (not mid-sentence).
ANTI_AI_PARAGRAPH_START_ONLY: list[str] = [
    "furthermore",
    "moreover",
    "additionally",
    "in summary",
    "it is noteworthy that",
    "importantly",
    "interestingly",
    "remarkably",
]

# ── Structural AI signal: transition / connector words ─────────────
# Overuse of these at sentence start signals AI-generated text.
AI_TRANSITION_WORDS: set[str] = {
    "additionally",
    "also",
    "collectively",
    "consequently",
    "conversely",
    "correspondingly",
    "crucially",
    "essentially",
    "fundamentally",
    "furthermore",
    "hence",
    "however",
    "importantly",
    "indeed",
    "interestingly",
    "likewise",
    "meanwhile",
    "moreover",
    "nevertheless",
    "nonetheless",
    "notably",
    "overall",
    "remarkably",
    "significantly",
    "similarly",
    "specifically",
    "strikingly",
    "subsequently",
    "therefore",
    "thus",
    "ultimately",
    "undeniably",
    "undoubtedly",
}

# ── Negative parallelism patterns (Pattern 9) ──────────────────────
# "not just X, it's Y" / "not only X, but (also) Y" — overused by AI
AI_NEGATIVE_PARALLELISM_PATTERNS: list[str] = [
    r"\bnot\s+just\b[^.]{3,40},\s*(?:it(?:'s|\s+is)|but)\b",
    r"\bnot\s+only\b[^.]{3,40},?\s*but\s+(?:also\s+)?",
    r"\bnot\s+merely\b[^.]{3,40},?\s*but\b",
]

# ── Copula avoidance verbs (Pattern 8) ─────────────────────────────
# AI avoids "is/has" by substituting impressive-sounding verbs.
AI_COPULA_AVOIDANCE_VERBS: list[str] = [
    "serves as",
    "stands as",
    "functions as",
    "acts as",
    "remains",
    "represents",
    "constitutes",
    "embodies",
]

# ── False range patterns (Pattern 12) ──────────────────────────────
# "from X to Y" — AI loves enumerating vague ranges.
AI_FALSE_RANGE_PATTERN: str = r"\bfrom\s+\w+(?:\s+\w+)?\s+to\s+\w+(?:\s+\w+)?"

# ── Em dash pattern (Pattern 13) ───────────────────────────────────
# AI overuses em dashes (—) for parenthetical asides.
AI_EM_DASH_PATTERN: str = r"—"

# Common abbreviations that should NOT require first-use definition.
COMMON_ABBREVIATIONS: set[str] = {
    "DNA",
    "RNA",
    "ICU",
    "OR",
    "CI",
    "SD",
    "IQR",
    "HR",
    "RR",
    "BMI",
    "CT",
    "MRI",
    "ECG",
    "EEG",
    "EMG",
    "IV",
    "IM",
    "SC",
    "PO",
    "ICU",
    "ED",
    "ER",
    "WHO",
    "FDA",
    "NIH",
    "CDC",
    "IRB",
    "GCP",
    "ITT",
    "PP",
    "CONSORT",
    "STROBE",
    "PRISMA",
    "CARE",
    "STARD",
    "TRIPOD",
    "ANOVA",
    "GEE",
    "ROC",
    "AUC",
    "NNT",
    "NNH",
    "RCT",
    "CPR",
    "INR",
    "PT",
    "APTT",
    "VAS",
    "GCS",
    "ASA",
    "NYHA",
    "APACHE",
    "SOFA",
    "MELD",
    "CRP",
    "WBC",
    "RBC",
    "HB",
    "PLT",
    "ALT",
    "AST",
    "BUN",
    "II",
    "III",
    "IV",
}

# Default citation density thresholds (citations per N words).
# A section needing >= 1 citation per 100 words has threshold 100.
# 0 means no minimum requirement for that section.
DEFAULT_CITATION_DENSITY: dict[str, int] = {
    "introduction": 100,
    "discussion": 150,
    "methods": 0,
    "results": 0,
}

# ── Minimum reference counts per paper type ────────────────────────
# Code-Enforced by Phase 2 Gate (pipeline_gate_validator.py).
# journal-profile.yaml `minimum_reference_limits` overrides these defaults.
# Fallback: DEFAULT_MIN_REFERENCES when paper type not found.
DEFAULT_MIN_REFERENCES: int = 15

DEFAULT_MINIMUM_REFERENCES: dict[str, int] = {
    "original-research": 20,
    "review-article": 30,
    "systematic-review": 40,
    "meta-analysis": 40,
    "case-report": 8,
    "letter": 5,
}

# Sections that count toward total manuscript word count.
# Per academic convention (ICMJE, NEJM, JAMA, BMJ, Lancet, BJA):
# Word count = main body text only.
# Abstract, References, Figure Legends, Tables, Acknowledgments,
# Author Contributions, etc. are NOT counted.
BODY_SECTIONS: set[str] = {
    "introduction",
    "methods",
    "materials and methods",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "case presentation",
    "case report",
    "literature review",
    "background",
}


# ── British vs American English dictionary (A5) ────────────────────

# Key = British spelling, Value = American spelling
# Covers the most common medical/scientific divergences.
BRIT_VS_AMER: dict[str, str] = {
    # -ise / -ize
    "randomise": "randomize",
    "randomised": "randomized",
    "randomisation": "randomization",
    "randomising": "randomizing",
    "standardise": "standardize",
    "standardised": "standardized",
    "standardisation": "standardization",
    "characterise": "characterize",
    "characterised": "characterized",
    "characterisation": "characterization",
    "categorise": "categorize",
    "categorised": "categorized",
    "categorisation": "categorization",
    "optimise": "optimize",
    "optimised": "optimized",
    "optimisation": "optimization",
    "minimise": "minimize",
    "minimised": "minimized",
    "utilise": "utilize",
    "utilised": "utilized",
    "utilisation": "utilization",
    "analyse": "analyze",
    "analysed": "analyzed",
    "analysing": "analyzing",
    "recognise": "recognize",
    "recognised": "recognized",
    "summarise": "summarize",
    "summarised": "summarized",
    "generalise": "generalize",
    "generalised": "generalized",
    "generalisation": "generalization",
    "hospitalise": "hospitalize",
    "hospitalised": "hospitalized",
    "hospitalisation": "hospitalization",
    "specialise": "specialize",
    "specialised": "specialized",
    "specialisation": "specialization",
    "normalise": "normalize",
    "normalised": "normalized",
    "normalisation": "normalization",
    "visualise": "visualize",
    "visualised": "visualized",
    "visualisation": "visualization",
    "hypothesise": "hypothesize",
    "hypothesised": "hypothesized",
    "prioritise": "prioritize",
    "prioritised": "prioritized",
    "sensitise": "sensitize",
    "sensitised": "sensitized",
    "immunise": "immunize",
    "immunised": "immunized",
    "immunisation": "immunization",
    "localise": "localize",
    "localised": "localized",
    "localisation": "localization",
    "stabilise": "stabilize",
    "stabilised": "stabilized",
    "stabilisation": "stabilization",
    # -our / -or
    "colour": "color",
    "colours": "colors",
    "favour": "favor",
    "favourable": "favorable",
    "favourably": "favorably",
    "behaviour": "behavior",
    "behaviours": "behaviors",
    "behavioural": "behavioral",
    "tumour": "tumor",
    "tumours": "tumors",
    "honour": "honor",
    "labour": "labor",
    "neighbour": "neighbor",
    "neighbourhood": "neighborhood",
    "humour": "humor",
    "vigour": "vigor",
    "vapour": "vapor",
    "odour": "odor",
    "rumour": "rumor",
    "savour": "savor",
    # -re / -er
    "centre": "center",
    "centres": "centers",
    "fibre": "fiber",
    "fibres": "fibers",
    "litre": "liter",
    "litres": "liters",
    "metre": "meter",
    "metres": "meters",
    "theatre": "theater",
    "theatres": "theaters",
    "spectre": "specter",
    "manoeuvre": "maneuver",
    "manoeuvres": "maneuvers",
    # -ae / -e (medical)
    "anaemia": "anemia",
    "anaemic": "anemic",
    "anaesthesia": "anesthesia",
    "anaesthesiologist": "anesthesiologist",
    "anaesthetic": "anesthetic",
    "anaesthetist": "anesthetist",
    "haemorrhage": "hemorrhage",
    "haemorrhagic": "hemorrhagic",
    "haemoglobin": "hemoglobin",
    "haemolysis": "hemolysis",
    "haemolytic": "hemolytic",
    "haemostasis": "hemostasis",
    "haemodynamic": "hemodynamic",
    "haematoma": "hematoma",
    "haematology": "hematology",
    "haematological": "hematological",
    "leukaemia": "leukemia",
    "oedema": "edema",
    "oesophagus": "esophagus",
    "oesophageal": "esophageal",
    "orthopaedic": "orthopedic",
    "orthopaedics": "orthopedics",
    "paediatric": "pediatric",
    "paediatrics": "pediatrics",
    "paediatrician": "pediatrician",
    "gynaecology": "gynecology",
    "gynaecological": "gynecological",
    "gynaecologist": "gynecologist",
    "foetus": "fetus",
    "foetal": "fetal",
    # -ence / -ense
    "defence": "defense",
    "offence": "offense",
    "licence": "license",
    # -ogue / -og
    "analogue": "analog",
    "catalogue": "catalog",
    "dialogue": "dialog",
    # Double-L / Single-L
    "labelled": "labeled",
    "labelling": "labeling",
    "modelled": "modeled",
    "modelling": "modeling",
    "cancelled": "canceled",
    "cancelling": "canceling",
    "travelled": "traveled",
    "travelling": "traveling",
    "counselled": "counseled",
    "counselling": "counseling",
    "signalled": "signaled",
    "signalling": "signaling",
    "channelled": "channeled",
    "channelling": "channeling",
    # Other common pairs
    "programme": "program",
    "programmes": "programs",
    "practise": "practice",
    "practised": "practiced",
    "ageing": "aging",
    "artefact": "artifact",
    "artefacts": "artifacts",
    "grey": "gray",
    "judgement": "judgment",
    "plough": "plow",
    "sceptical": "skeptical",
    "sulphate": "sulfate",
    "aluminium": "aluminum",
    "diarrhoea": "diarrhea",
    "coeliac": "celiac",
    "caesarean": "cesarean",
}

# Build reverse dictionary (American → British)
AMER_VS_BRIT: dict[str, str] = {v: k for k, v in BRIT_VS_AMER.items()}

# Sanity check: mapping must be bijective (no ambiguous reversals)
if len(AMER_VS_BRIT) != len(BRIT_VS_AMER):
    raise ValueError(
        "BRIT_VS_AMER has duplicate values — reverse map lost "
        f"{len(BRIT_VS_AMER) - len(AMER_VS_BRIT)} entries"
    )
