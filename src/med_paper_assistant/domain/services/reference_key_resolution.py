"""
Reference key resolution — map a citation key to saved-reference metadata.

Pure functions (no I/O of their own); callers inject the metadata lookup.

Key shapes:
    tang2023_38049909          → PMID 38049909
    PMID:38049909 / 38049909   → PMID 38049909
    smith2024_zot_ABC123XY     → Zotero key (never treated as a PMID)
    jones2023_doi_10.1000_x    → DOI key (never treated as a PMID)
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import Any

_NON_PMID_SEGMENT_RE = re.compile(r"_(?:zot|doi)_", re.IGNORECASE)


def is_non_pmid_key(key: str) -> bool:
    """Return True for Zotero/DOI-style keys whose numeric suffix is not a PMID."""
    return bool(_NON_PMID_SEGMENT_RE.search(key))


def extract_pmid_from_key(key: str) -> str | None:
    """Extract a PMID from a citation key, or None when the key carries no PMID."""
    key = key.strip()
    if key.upper().startswith("PMID:"):
        pmid = key.split(":", 1)[1].strip()
        return pmid or None
    if key.isdigit():
        return key
    if "_" in key and not is_non_pmid_key(key):
        candidate = key.rsplit("_", 1)[-1]
        if candidate.isdigit():
            return candidate
    return None


def reference_id_candidates(key: str) -> list[str]:
    """Return storage ids to try, most specific first, for a citation key."""
    key = key.strip()
    candidates: list[str] = []
    pmid = extract_pmid_from_key(key)
    if pmid:
        candidates.append(pmid)
    elif key:
        candidates.append(key)
        if is_non_pmid_key(key):
            tail = key.split("_", 1)[1]
            if tail not in candidates:
                candidates.append(tail)
    return candidates


def resolve_reference_metadata(
    key: str,
    get_metadata: Callable[[str], dict[str, Any] | None],
    list_reference_ids: Callable[[], Iterable[str]] | None = None,
) -> tuple[str, dict[str, Any]] | None:
    """
    Resolve a citation key to ``(reference_id, metadata)``.

    Tries PMID/storage-id candidates first, then falls back to scanning saved
    references for a matching ``citation_key`` (non-PMID keys only).
    """
    for candidate in reference_id_candidates(key):
        try:
            metadata = get_metadata(candidate)
        except Exception:
            metadata = None
        if metadata:
            return candidate, metadata

    if list_reference_ids is not None and extract_pmid_from_key(key) is None:
        try:
            ids = list(list_reference_ids())
        except Exception:
            return None
        for ref_id in ids:
            try:
                metadata = get_metadata(ref_id)
            except Exception:
                continue
            if metadata and metadata.get("citation_key") == key.strip():
                return ref_id, metadata
    return None
