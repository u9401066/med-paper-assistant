"""DOI normalization and syntactic validation (offline, deterministic).

Used by reference-integrity gating (Hook P7) to ensure that any DOI attached to
a cited reference is syntactically valid before a manuscript is finalized.

This is an OFFLINE check: it validates the DOI *shape* (the Crossref-recommended
pattern), not whether the DOI actually resolves to a live record. Existence
verification against Crossref/doi.org is intentionally out of scope here so the
check stays deterministic, fast, and network-free.
"""

from __future__ import annotations

import re

# Crossref-recommended DOI pattern: ``10.`` + registrant code (4-9 digits) + ``/``
# + suffix. Covers the overwhelming majority of modern DOIs.
_DOI_CORE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")

# Common wrappers that should be stripped before validation. Matched
# case-insensitively against the lower-cased candidate.
_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi.org/",
    "dx.doi.org/",
    "doi:",
    "doi ",
)


def normalize_doi(raw: str) -> str:
    """Strip URL/scheme wrappers and surrounding noise from a DOI string.

    Returns the bare DOI (for example ``10.1001/jama.2020.1585``). The suffix
    case is preserved because DOI suffixes are technically case-sensitive.
    """
    if not raw:
        return ""

    value = raw.strip()
    lowered = value.lower()
    for prefix in _DOI_PREFIXES:
        if lowered.startswith(prefix):
            value = value[len(prefix) :].strip()
            break

    # Strip trailing punctuation that often leaks from prose / citation strings.
    value = value.rstrip(" .,;)]>")
    return value


def is_valid_doi(raw: str) -> bool:
    """Return True if *raw* is a syntactically valid DOI after normalization."""
    normalized = normalize_doi(raw)
    if not normalized:
        return False
    return bool(_DOI_CORE.match(normalized))


def validate_doi(raw: str) -> tuple[bool, str, str]:
    """Validate a DOI string.

    Returns:
        ``(is_valid, normalized, reason)`` where ``normalized`` is the bare DOI
        after stripping wrappers and ``reason`` is an empty string when valid or
        a short human-readable explanation when invalid.
    """
    normalized = normalize_doi(raw)
    if not normalized:
        return False, "", "empty DOI"
    if not normalized.lower().startswith("10."):
        return False, normalized, "DOI must start with '10.'"
    if "/" not in normalized:
        return False, normalized, "DOI must contain a '/' separator"
    if not _DOI_CORE.match(normalized):
        return False, normalized, "DOI does not match the 10.<registrant>/<suffix> pattern"
    return True, normalized, ""


def normalize_doi_for_filename(doi: str) -> str:
    """Normalize a DOI into a filesystem-safe, lowercase slug.

    Distinct from :func:`normalize_doi` (which strips URL/scheme wrappers and
    preserves the canonical DOI). This collapses ``/`` and ``.`` to hyphens and
    drops every other non-alphanumeric character so the result is safe to embed
    in a filename or identifier.
    """
    if not doi:
        return ""
    normalized = re.sub(r"[/.]", "-", doi)
    normalized = re.sub(r"[^a-zA-Z0-9\-]", "", normalized)
    return normalized.lower()
