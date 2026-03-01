"""Writing Hooks — Shared text utilities mixin."""

from __future__ import annotations

import re
from typing import Any

from ._constants import BODY_SECTIONS


class TextUtilsMixin:
    """Shared text processing utilities used by multiple hook series."""

    @staticmethod
    def _count_words(text: str) -> int:
        """Count words in text, stripping markdown formatting."""
        # Strip wikilinks
        cleaned = re.sub(r"\[\[[^\]]*\]\]", "CITE", text)
        # Strip markdown links [text](url)
        cleaned = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cleaned)
        # Strip bold/italic markers
        cleaned = re.sub(r"[*_]{1,3}", "", cleaned)
        # Strip headings markers
        cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
        return len(re.findall(r"\b\w+\b", cleaned))

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
        sections = self._parse_sections(content)
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

        for sec_name, sec_text in sections.items():
            if sec_name.lower() in body_set:
                cleaned = self._strip_markdown_tables(sec_text)
                wc = self._count_words(cleaned)
                body_words += wc
                breakdown.append({"section": sec_name, "words": wc})
            else:
                excluded.append(sec_name)

        return {
            "body_words": body_words,
            "breakdown": breakdown,
            "excluded_sections": excluded,
        }

    @staticmethod
    def _parse_sections(content: str) -> dict[str, str]:
        """Parse markdown content into {section_name: section_text} dict."""
        sections: dict[str, str] = {}
        current_name: str | None = None
        current_lines: list[str] = []

        for line in content.split("\n"):
            heading_match = re.match(r"^#{1,3}\s+(.+)", line)
            if heading_match:
                if current_name is not None:
                    sections[current_name] = "\n".join(current_lines).strip()
                current_name = heading_match.group(1).strip()
                current_lines = []
            elif current_name is not None:
                current_lines.append(line)

        if current_name is not None:
            sections[current_name] = "\n".join(current_lines).strip()

        return sections
