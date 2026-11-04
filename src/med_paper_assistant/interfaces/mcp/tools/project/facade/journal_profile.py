"""Phase 0 journal profile defaults for ``project_action(action="journal_profile")``."""

from __future__ import annotations

from typing import Any

_MINIMUM_REFERENCE_LIMITS = {
    "case-report": 8,
    "letter": 8,
    "original-research": 20,
    "review-article": 30,
    "systematic-review": 40,
}
_WORD_LIMITS = {
    "total_manuscript": 3500,
    "abstract": 250,
    "introduction": 900,
    "methods": 900,
    "results": 900,
    "discussion": 1200,
}
_REQUIRED_DOCUMENTS = {
    "cover_letter": False,
    "data_availability": True,
    "ethics_statement": True,
    "conflict_of_interest": True,
}


def _default_sections() -> list[dict[str, Any]]:
    return [
        {"name": "Abstract", "required": True, "counts_toward_total": False},
        {"name": "Introduction", "required": True, "counts_toward_total": True},
        {"name": "Methods", "required": True, "counts_toward_total": True},
        {"name": "Results", "required": True, "counts_toward_total": True},
        {"name": "Discussion", "required": True, "counts_toward_total": True},
        {"name": "References", "required": True, "counts_toward_total": False},
    ]


def build_journal_profile(
    *,
    target_journal: str,
    paper_type: str,
    citation_style: str,
    language_preference: str,
    writing_style: str,
) -> dict[str, Any]:
    """Build a minimal Phase 0 journal profile that satisfies downstream gates."""
    language = language_preference.strip() or "en-US"
    return {
        "schema": "mdpaper.journal_profile.v1",
        "journal": {
            "name": target_journal.strip() or "generic",
            "locale": language,
        },
        "paper": {
            "type": paper_type.strip() or "original-research",
            "sections": _default_sections(),
        },
        "references": {
            "style": citation_style.strip() or "vancouver",
            "minimum_reference_limits": dict(_MINIMUM_REFERENCE_LIMITS),
        },
        "word_limits": dict(_WORD_LIMITS),
        "assets": {
            "figures_max": 6,
            "tables_max": 6,
        },
        "pipeline": {
            "review_max_rounds": 3,
            "writing": {
                "prefer_language": "british" if language.lower() in {"en-gb", "gb"} else "american",
                "style": writing_style.strip() or "journal",
            },
        },
        "required_documents": dict(_REQUIRED_DOCUMENTS),
    }
