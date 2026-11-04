"""Writing Hooks — Hierarchical markdown section parsing and citation-key helpers."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from med_paper_assistant.domain.services.citation_converter import (
    citation_key_from_wikilink_target,
    split_foam_wikilink_target,
)

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)")

# author2024_12345678, garcia-lopez2020_1234, smith2024_zot_ABC, smith2024_doi_10.1000/x
_CITATION_KEY_RE = re.compile(r"^[a-z][a-z-]*\d{4}_(?:\d{1,8}|zot_\S+|doi_\S+)$", re.IGNORECASE)
_WIKILINK_TARGET_RE = re.compile(r"(?<!!)\[\[([^\[\]]+?)\]\]")


@dataclass
class SectionNode:
    """One markdown heading with its own text and the text of nested subsections."""

    index: int
    level: int
    name: str
    own_text: str
    full_text: str
    parent: int | None


def parse_section_nodes(content: str) -> list[SectionNode]:
    """Parse headings (levels 1-3) into nodes in document order.

    A section spans until the next heading of the same or higher level, so
    ``###`` text is part of its ``##`` parent. A lone ``#`` document title
    that precedes ``##`` sections is treated as a childless title.
    """
    headings: list[tuple[int, int, str]] = []
    lines = content.split("\n")
    for line_no, line in enumerate(lines):
        match = _HEADING_RE.match(line)
        if match:
            headings.append((line_no, len(match.group(1)), match.group(2).strip()))

    level_one = [h for h in headings if h[1] == 1]
    title_line = (
        level_one[0][0]
        if len(level_one) == 1 and any(h[1] == 2 for h in headings) and headings[0] == level_one[0]
        else None
    )

    nodes: list[SectionNode] = []
    stack: list[int] = []
    for idx, (line_no, level, name) in enumerate(headings):
        is_title = line_no == title_line
        next_any = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        own_text = "\n".join(lines[line_no + 1 : next_any]).strip()

        end = len(lines)
        if not is_title:
            for later_line, later_level, _ in headings[idx + 1 :]:
                if later_level <= level:
                    end = later_line
                    break
        nested_heading_lines = {h[0] for h in headings[idx + 1 :] if h[0] < end}
        full_lines = [lines[i] for i in range(line_no + 1, end) if i not in nested_heading_lines]
        full_text = own_text if is_title else "\n".join(full_lines).strip()

        parent: int | None = None
        if not is_title:
            while stack and nodes[stack[-1]].level >= level:
                stack.pop()
            parent = stack[-1] if stack else None
            stack.append(idx)
        nodes.append(SectionNode(idx, level, name, own_text, full_text, parent))
    return nodes


def has_selected_ancestor(node: SectionNode, nodes: list[SectionNode], selected: set[int]) -> bool:
    """Return whether any ancestor of ``node`` is in ``selected``."""
    parent = node.parent
    while parent is not None:
        if parent in selected:
            return True
        parent = nodes[parent].parent
    return False


def select_outermost(
    nodes: list[SectionNode], predicate: Callable[[str], bool]
) -> list[SectionNode]:
    """Select nodes matching ``predicate`` that have no selected ancestor."""
    selected: set[int] = set()
    result: list[SectionNode] = []
    for node in nodes:
        if predicate(node.name) and not has_selected_ancestor(node, nodes, selected):
            selected.add(node.index)
            result.append(node)
    return result


def citation_key_from_target(target: str) -> str | None:
    """Return the saved-reference key for a wikilink target, or None if not a key.

    Bare PMIDs and ``PMID:`` forms are not manuscript citation keys.
    """
    base, _, _ = split_foam_wikilink_target(target)
    if _CITATION_KEY_RE.match(base):
        return base
    key = citation_key_from_wikilink_target(target)
    if key and not key.isdigit() and not key.upper().startswith("PMID:"):
        return key
    return None


def extract_wikilink_citation_keys(text: str) -> list[str]:
    """Return citation keys of all ``[[...]]`` wikilinks in ``text`` (in order, with repeats)."""
    keys: list[str] = []
    for match in _WIKILINK_TARGET_RE.finditer(text):
        key = citation_key_from_target(match.group(1))
        if key:
            keys.append(key)
    return keys
