"""
Citation Converter — Bidirectional conversion between wikilink and Pandoc citation formats.

Conversion directions:
  [[key]]                           → [@key]          (for Pandoc --citeproc)
  [1]<!-- [[key]] -->               → [@key]          (reversible format → Pandoc)
  (Author, 2024)<!-- [[key]] -->    → [@key]          (APA reversible → Pandoc)
  [@key]                            → [[key]]         (Pandoc → wikilink for editing)

Multiple citations:
  [[a]] and [[b]]                   → [@a; @b] only when adjacent
  [@a; @b]                          → [[a]] [[b]]

Architecture:
  Domain service — pure functions, no I/O, no external dependencies.
  Called by ExportPipeline (application layer) before Pandoc conversion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ──────────────────────────────────────────────────────────────────────────────
# Patterns
# ──────────────────────────────────────────────────────────────────────────────

# Wikilink: [[citation_key]]
_WIKILINK_RE = re.compile(r"\[\[([^\]\[]+?)\]\]")

# Reversible format from sync_references_from_wikilinks():
#   [1]<!-- [[citation_key]] -->
#   (Author et al., 2024)<!-- [[citation_key]] -->
_REVERSIBLE_RE = re.compile(r"(?:\[\d+\]|\([^)]+,\s*\d{4}\))<!-- \[\[([^\]]+)\]\] -->")

# Pandoc citation: [@key] or [@key1; @key2; ...]
_PANDOC_SINGLE_RE = re.compile(r"\[@([^\];]+)\]")
_PANDOC_MULTI_RE = re.compile(r"\[(@[^\]]+)\]")

# Reference section header
_REFERENCES_HEADER_RE = re.compile(r"^---?\s*$|^## References", re.MULTILINE)


@dataclass
class ConversionResult:
    """Result of a citation format conversion."""

    content: str
    citations_converted: int = 0
    citation_keys: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Wikilink → Pandoc
# ──────────────────────────────────────────────────────────────────────────────


def wikilinks_to_pandoc(content: str) -> ConversionResult:
    """
    Convert wikilink citations to Pandoc [@key] format.

    Handles both raw wikilinks and reversible format.
    Strips the ## References section (Pandoc generates its own).

    Args:
        content: Markdown with [[wikilink]] or reversible citations.

    Returns:
        ConversionResult with Pandoc-formatted content.
    """
    result_content = content
    keys: list[str] = []
    count = 0

    # Step 1: Convert reversible format first (more specific pattern)
    def _replace_reversible(m: re.Match) -> str:
        nonlocal count
        key = m.group(1)
        if key not in keys:
            keys.append(key)
        count += 1
        return f"[@{key}]"

    result_content = _REVERSIBLE_RE.sub(_replace_reversible, result_content)

    # Step 2: Convert remaining raw wikilinks
    def _replace_wikilink(m: re.Match) -> str:
        nonlocal count
        key = m.group(1)
        # Skip non-citation wikilinks (internal links without underscore+digits)
        if not _looks_like_citation_key(key):
            return m.group(0)  # Leave as-is
        if key not in keys:
            keys.append(key)
        count += 1
        return f"[@{key}]"

    result_content = _WIKILINK_RE.sub(_replace_wikilink, result_content)

    # Step 3: Strip existing ## References section (Pandoc --citeproc generates it)
    result_content = _strip_references_section(result_content)

    return ConversionResult(
        content=result_content.rstrip() + "\n",
        citations_converted=count,
        citation_keys=keys,
    )


def pandoc_to_wikilinks(content: str) -> ConversionResult:
    """
    Convert Pandoc [@key] citations back to [[wikilink]] format.

    Args:
        content: Markdown with [@key] citations.

    Returns:
        ConversionResult with wikilink-formatted content.
    """
    keys: list[str] = []
    count = 0

    def _replace_pandoc(m: re.Match) -> str:
        nonlocal count
        inner = m.group(1)  # e.g., "@key1; @key2"
        parts = [p.strip().lstrip("@") for p in inner.split(";")]
        replacements = []
        for key in parts:
            if key and key not in keys:
                keys.append(key)
            replacements.append(f"[[{key}]]")
            count += 1
        return " ".join(replacements)

    result_content = _PANDOC_MULTI_RE.sub(_replace_pandoc, content)

    return ConversionResult(
        content=result_content,
        citations_converted=count,
        citation_keys=keys,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _looks_like_citation_key(key: str) -> bool:
    """
    Heuristic: does this wikilink look like a citation key?

    Citation keys have format: author2024_12345678
    Internal links are just words: "introduction", "methods"
    """
    # Must contain underscore + digits (PubMed/Zotero pattern)
    if re.match(r"^[a-z]+\d{4}_\d+$", key, re.IGNORECASE):
        return True
    # PMID:xxx format
    if key.upper().startswith("PMID:"):
        return True
    # Pure numeric (bare PMID)
    if key.isdigit() and len(key) >= 7:
        return True
    # Zotero format: author2024_zot_xxx
    if re.match(r"^[a-z]+\d{4}_zot_", key, re.IGNORECASE):
        return True
    # DOI format: author2024_doi_xxx
    if re.match(r"^[a-z]+\d{4}_doi_", key, re.IGNORECASE):
        return True
    return False


def _strip_references_section(content: str) -> str:
    """
    Remove the ## References section from markdown.

    Pandoc --citeproc will generate its own reference list.
    We need to strip the hand-generated one to avoid duplication.
    """
    # Find "## References" and everything after it
    # Also handle "---\n\n## References" pattern
    patterns = [
        r"\n---\s*\n+## References\b.*",  # With horizontal rule
        r"\n## References\b.*",  # Without horizontal rule
    ]
    for pattern in patterns:
        content = re.sub(pattern, "", content, flags=re.DOTALL)
    return content


def extract_citation_keys(content: str) -> list[str]:
    """
    Extract all citation keys from content, regardless of format.

    Detects: [[key]], [@key], [1]<!-- [[key]] -->
    Returns deduplicated list in order of first appearance.
    """
    keys: list[str] = []
    seen: set[str] = set()

    def _add(key: str) -> None:
        if key not in seen:
            seen.add(key)
            keys.append(key)

    # Reversible format
    for m in _REVERSIBLE_RE.finditer(content):
        _add(m.group(1))

    # Raw wikilinks
    for m in _WIKILINK_RE.finditer(content):
        key = m.group(1)
        if _looks_like_citation_key(key):
            _add(key)

    # Pandoc format
    for m in _PANDOC_MULTI_RE.finditer(content):
        for part in m.group(1).split(";"):
            k = part.strip().lstrip("@")
            if k:
                _add(k)

    return keys
