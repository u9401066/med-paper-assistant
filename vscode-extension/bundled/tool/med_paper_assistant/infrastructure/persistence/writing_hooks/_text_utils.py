"""Writing Hooks — Shared text utilities mixin."""

from __future__ import annotations

import re
from typing import Any

from ._constants import BODY_SECTIONS
from ._section_tree import (
    SectionNode,
    has_selected_ancestor,
    parse_section_nodes,
    select_outermost,
)

# CJK scripts have no word separators, so each character counts as one word.
_CJK = "\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff"
_WORD_RE = re.compile(rf"[{_CJK}]|\d+(?:[,.]\d+)+|(?:(?![{_CJK}])\w)+")


def strip_markdown_prose(content: str) -> str:
    """Drop markdown headings and reference wikilinks, leaving prose for style analysis."""
    prose = re.sub(r"^#+\s.*$", "", content, flags=re.MULTILINE)
    prose = re.sub(r"\[\[[^\]]*\]\]", "", prose)
    return prose.strip()


class TextUtilsMixin:
    """Shared text processing utilities used by multiple hook series."""

    @staticmethod
    def _strip_frontmatter(text: str) -> str:
        """Strip YAML frontmatter (--- ... ---) from markdown content."""
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                text = text[end + 4 :]
        return text

    @staticmethod
    def _count_words(text: str) -> int:
        """Count words in text, stripping markdown formatting and frontmatter."""
        # Strip YAML frontmatter
        cleaned = TextUtilsMixin._strip_frontmatter(text)
        # Strip wikilinks
        cleaned = re.sub(r"\[\[[^\]]*\]\]", "CITE", cleaned)
        # Strip markdown links [text](url)
        cleaned = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cleaned)
        # Strip bold/italic markers
        cleaned = re.sub(r"[*_]{1,3}", "", cleaned)
        # Strip headings markers
        cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
        return len(_WORD_RE.findall(cleaned))

    @staticmethod
    def _strip_markdown_tables(text: str) -> str:
        """Remove markdown table rows from text (tables are display items, not counted)."""
        lines = text.split("\n")
        return "\n".join(line for line in lines if not re.match(r"^\s*\|.*\|\s*$", line))

    def _extract_body_word_count(self, content: str) -> dict[str, Any]:
        """Extract word count for body sections only (academic convention).

        Per ICMJE / major journal guidelines, manuscript word count includes
        only main body text (Introduction through Conclusion). Excludes:
        - Title / Author info (before first section heading)
        - Abstract (has its own word limit)
        - References (has its own count limit)
        - Tables (display items)
        - Figure legends, Acknowledgments, Author Contributions, etc.

        Returns dict with body_words, section_breakdown, excluded_sections.
        """
        nodes = self._section_nodes(content)
        body_words = 0
        breakdown: list[dict[str, Any]] = []
        excluded: list[str] = []

        # Check journal profile for custom body sections
        custom_body: set[str] | None = None
        if self._journal_profile:
            paper = self._journal_profile.get("paper", {})
            profile_sections = paper.get("sections", [])
            counts_flags = [s for s in profile_sections if s.get("counts_toward_total") is True]
            if counts_flags:
                custom_body = {s["name"].lower() for s in counts_flags}

        body_set = custom_body if custom_body else BODY_SECTIONS

        # Subsections count toward their body parent, never twice.
        selected_nodes = select_outermost(nodes, lambda name: name.lower() in body_set)
        selected = {n.index for n in selected_nodes}
        for node in selected_nodes:
            cleaned = self._strip_markdown_tables(node.full_text)
            wc = self._count_words(cleaned)
            body_words += wc
            breakdown.append({"section": node.name, "words": wc})
        for node in nodes:
            if node.index not in selected and not has_selected_ancestor(node, nodes, selected):
                excluded.append(node.name)

        return {
            "body_words": body_words,
            "breakdown": breakdown,
            "excluded_sections": excluded,
        }

    @staticmethod
    def _section_nodes(content: str) -> list[SectionNode]:
        """Parse content (frontmatter stripped) into hierarchical section nodes."""
        return parse_section_nodes(TextUtilsMixin._strip_frontmatter(content))

    def _sections_with_word_limits(self, content: str) -> dict[str, str]:
        """Outermost sections that have a configured word limit, with nested text included."""
        limit = getattr(self, "_get_section_word_limit")
        nodes = select_outermost(self._section_nodes(content), lambda n: limit(n) is not None)
        return {node.name: node.full_text for node in nodes}

    @staticmethod
    def _merge_by_name(pairs: list[tuple[str, str]]) -> dict[str, str]:
        merged: dict[str, str] = {}
        for name, text in pairs:
            merged[name] = f"{merged[name]}\n{text}".strip() if name in merged else text
        return merged

    @staticmethod
    def _parse_sections(content: str) -> dict[str, str]:
        """Parse markdown content into {section_name: own_text} (flat, no nested text).

        Strips YAML frontmatter before parsing. Duplicate heading names are
        merged instead of overwritten.
        """
        nodes = TextUtilsMixin._section_nodes(content)
        return TextUtilsMixin._merge_by_name([(n.name, n.own_text) for n in nodes])

    @staticmethod
    def _parse_sections_full(content: str) -> dict[str, str]:
        """Like ``_parse_sections`` but each section includes its nested subsections."""
        nodes = TextUtilsMixin._section_nodes(content)
        return TextUtilsMixin._merge_by_name([(n.name, n.full_text) for n in nodes])
