"""
Citation Converter — Bidirectional conversion between wikilink and Pandoc citation formats.

Conversion directions:
    [[key]]                           → [@key]          (for Pandoc --citeproc)
    [1] [[key]]                       → [@key]          (Foam-visible reversible format → Pandoc)
    [1]<!-- [[key]] -->               → [@key]          (legacy reversible format → Pandoc)
    (Author, 2024) [[key]]            → [@key]          (APA reversible → Pandoc)
    (Author, 2024)<!-- [[key]] -->    → [@key]          (legacy APA reversible → Pandoc)
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

# Plain wikilink: [[citation_key]]. FOAM embeds (![[...]]) are deliberately
# excluded from export conversion because they represent knowledge-base
# transclusion/evidence blocks, not manuscript in-text citations.
_WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]\[]+?)\]\]")
_FOAM_EMBED_RE = re.compile(r"!\[\[([^\]\[]+?)\]\]")

# Reversible format from sync_references_from_wikilinks():
#   [1] [[citation_key]]
#   [1]<!-- [[citation_key]] -->
#   ^1^ [[citation_key]]
#   ^1^<!-- [[citation_key]] -->
#   (Author et al., 2024) [[citation_key]]
#   (Author et al., 2024)<!-- [[citation_key]] -->
#   (Author et al. 2024) [[citation_key]]
#   (Author et al. 2024)<!-- [[citation_key]] -->
_REVERSIBLE_RE = re.compile(
    r"(?:\[\d+\]|\^\d+\^|\([^)]+,\s*\d{4}\)|\([^)]+\s\d{4}\))"
    r"(?:<!--\s*|[ \t]+)\[\[([^\]]+)\]\](?:\s*-->)?"
)

# Pandoc citation: [@key] or [@key1; @key2; ...]
_PANDOC_SINGLE_RE = re.compile(r"\[@([^\];]+)\]")
_PANDOC_MULTI_RE = re.compile(r"\[(@[^\]]+)\]")

# Reference section header
_REFERENCES_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+references\b", re.IGNORECASE)


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
    # Strip hand-maintained references before converting citations. Otherwise
    # reference-list trailers such as ``[[kim2000_10960403]]`` are converted to
    # raw Pandoc tokens and counted as in-text citations, and can leak into
    # exported output if the heading level is not exactly ``## References``.
    result_content = _strip_references_section(content)
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
        # Skip non-citation and FOAM-only wikilinks. Anchors/aliases are
        # knowledge-base links, not renderable manuscript citations.
        if not _is_plain_manuscript_citation_target(key):
            return m.group(0)  # Leave as-is
        if key not in keys:
            keys.append(key)
        count += 1
        return f"[@{key}]"

    result_content = _WIKILINK_RE.sub(_replace_wikilink, result_content)

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


def restore_reversible_citations_to_wikilinks(content: str) -> str:
    """
    Restore reversible citations back to raw wikilinks before re-syncing.

    Supports both the Foam-visible format and the legacy HTML-comment format.
    The separator intentionally matches only same-line spaces or tabs so a
    bracketed citation marker on one line does not consume a wikilink on the next.
    """

    return _REVERSIBLE_RE.sub(r"[[\1]]", content)


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
    if re.match(r"^[a-z][a-z-]*\d{4}_\d{7,8}$", key, re.IGNORECASE):
        return True
    # PMID:xxx format
    if key.upper().startswith("PMID:"):
        return True
    # Pure numeric (bare PMID)
    if key.isdigit() and len(key) >= 7:
        return True
    # Zotero format: author2024_zot_xxx
    if re.match(r"^[a-z][a-z-]*\d{4}_zot_", key, re.IGNORECASE):
        return True
    # DOI format: author2024_doi_xxx
    if re.match(r"^[a-z][a-z-]*\d{4}_doi_", key, re.IGNORECASE):
        return True
    return False


def split_foam_wikilink_target(target: str) -> tuple[str, str, str]:
    """
    Split a FOAM-compatible wikilink target into base key, anchor, and alias.

    Examples:
      ``ref2024_12345678`` -> ("ref2024_12345678", "", "")
      ``ref2024_12345678#^finding`` -> ("ref2024_12345678", "^finding", "")
      ``ref2024_12345678|Tang 2024`` -> ("ref2024_12345678", "", "Tang 2024")
      ``ref2024_12345678#^finding|quote`` -> ("ref2024_12345678", "^finding", "quote")
    """
    without_alias, alias_sep, alias = target.strip().partition("|")
    base, anchor_sep, anchor = without_alias.strip().partition("#")
    return base.strip(), anchor.strip() if anchor_sep else "", alias.strip() if alias_sep else ""


def citation_key_from_wikilink_target(target: str) -> str | None:
    """Return the saved-reference key base from a plain or FOAM wikilink target."""
    base, _, _ = split_foam_wikilink_target(target)
    return base if _looks_like_citation_key(base) else None


def _is_plain_manuscript_citation_target(target: str) -> bool:
    """Return True only for manuscript citation links that Pandoc should render."""
    base, anchor, alias = split_foam_wikilink_target(target)
    return not anchor and not alias and _looks_like_citation_key(base)


def _strip_references_section(content: str) -> str:
    """
    Remove the ## References section from markdown.

    Pandoc --citeproc will generate its own reference list.
    We need to strip the hand-generated one to avoid duplication.

    Handles ``# References`` through ``###### References`` and strips only up
    to the next same-or-higher-level heading or end-of-string, so sections
    after References are preserved. A horizontal rule immediately before the
    References heading is removed too.
    """
    lines = content.splitlines(keepends=True)
    output: list[str] = []
    i = 0

    while i < len(lines):
        heading = _REFERENCES_HEADING_RE.match(lines[i])
        if not heading:
            output.append(lines[i])
            i += 1
            continue

        if output and re.match(r"^\s*-{3,}\s*$", output[-1]):
            output.pop()
            if output and output[-1].strip() == "":
                output.pop()

        ref_level = len(heading.group(1))
        i += 1
        while i < len(lines):
            next_heading = re.match(r"^\s{0,3}(#{1,6})\s+\S", lines[i])
            if next_heading and len(next_heading.group(1)) <= ref_level:
                break
            i += 1

    return "".join(output)


def extract_citation_keys(content: str) -> list[str]:
    """
    Extract all citation keys from content, regardless of format.

    Detects: [[key]], [@key], [1] [[key]], [1]<!-- [[key]] -->, ^1^ [[key]]
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

    # Raw manuscript citation wikilinks. FOAM anchors/aliases are intentionally
    # not counted as renderable manuscript citations.
    for m in _WIKILINK_RE.finditer(content):
        key = m.group(1)
        if _is_plain_manuscript_citation_target(key):
            _add(key)

    # Pandoc format
    for m in _PANDOC_MULTI_RE.finditer(content):
        for part in m.group(1).split(";"):
            k = part.strip().lstrip("@")
            if k:
                _add(k)

    return keys


def extract_reference_wikilink_keys(
    content: str,
    *,
    include_embeds: bool = True,
    include_pandoc: bool = True,
) -> list[str]:
    """
    Extract saved-reference keys from both manuscript and FOAM wikilinks.

    Unlike :func:`extract_citation_keys`, this includes FOAM anchors, aliases,
    and optionally embeds. It is intended for validation/audit hooks that need
    to know whether a document points at a saved reference without treating
    every FOAM link as a renderable manuscript citation.
    """
    keys: list[str] = []
    seen: set[str] = set()

    def _add(key: str | None) -> None:
        if key and key not in seen:
            seen.add(key)
            keys.append(key)

    for m in _WIKILINK_RE.finditer(content):
        _add(citation_key_from_wikilink_target(m.group(1)))

    if include_embeds:
        for m in _FOAM_EMBED_RE.finditer(content):
            _add(citation_key_from_wikilink_target(m.group(1)))

    if include_pandoc:
        for m in _PANDOC_MULTI_RE.finditer(content):
            for part in m.group(1).split(";"):
                _add(part.strip().lstrip("@"))

    return keys
