"""Writing Hooks — Limits and whitelists (abbreviations, citation density, references, body)."""

from __future__ import annotations

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
# Code-Enforced by Phase 2 Gate (pipeline_gate_validator/).
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
