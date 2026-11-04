"""Thresholds and vocabularies shared by the R-series review hooks."""

from __future__ import annotations

# Minimum review report length (words)
MIN_REVIEW_REPORT_WORDS = 300

# Required reviewer perspectives (at least 3 of these must appear in the report)
REVIEWER_PERSPECTIVES = [
    "methodology",
    "domain",
    "statistic",
    "writing",
    "editor",
    "clinical",
    "ethical",
]
MIN_PERSPECTIVES = 3

# Severity keywords for issue parsing in review reports
SEVERITY_KEYWORDS = {
    "major": ["major", "critical", "serious", "significant"],
    "minor": ["minor", "trivial", "cosmetic", "editorial"],
    "optional": ["optional", "suggestion", "consider", "recommended"],
}

# Maximum DECLINE ratio for author responses
MAX_DECLINE_RATIO = 0.50

# Minimum checklist items in EQUATOR compliance file
MIN_EQUATOR_ITEMS = 5

# Reference budget headroom: how many refs above limit before CRITICAL
REF_BUDGET_HEADROOM = 0  # 0 = strict (no overrun allowed)
