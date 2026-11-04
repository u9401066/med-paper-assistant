"""
References-section splitting — locate the References block without losing trailing sections.

Pure function (no I/O). A References block runs from its heading to the next
heading of the same or higher level (or end of text); anything after it
(Figure Legends, Tables, Supplementary, ...) is returned separately so callers
can re-append it after rewriting the bibliography.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_REFERENCES_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+references\b", re.IGNORECASE)
_ANY_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+\S")
_HORIZONTAL_RULE_RE = re.compile(r"^\s*-{3,}\s*$")


@dataclass(frozen=True)
class ReferencesSplit:
    """Content split around the first References block."""

    body: str  # text before the block (trailing rule/blank lines removed)
    references: str  # heading + entries; "" when there is no References heading
    tail: str  # text after the block; "" when the block is last

    @property
    def has_references(self) -> bool:
        return bool(self.references)

    def with_tail(self, content: str) -> str:
        """Re-append the sections that followed the References block."""
        if not self.tail:
            return content
        return content.rstrip("\n") + "\n\n" + self.tail + "\n"


def split_references_section(content: str) -> ReferencesSplit:
    """Split ``content`` into body, References block, and trailing sections."""
    lines = content.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if _REFERENCES_HEADING_RE.match(ln)), None)
    if start is None:
        return ReferencesSplit(body=content.rstrip(), references="", tail="")

    level = len(_REFERENCES_HEADING_RE.match(lines[start]).group(1))  # type: ignore[union-attr]
    end = start + 1
    while end < len(lines):
        heading = _ANY_HEADING_RE.match(lines[end])
        if heading and len(heading.group(1)) <= level:
            break
        end += 1

    body_lines = lines[:start]
    while body_lines and body_lines[-1].strip() == "":
        body_lines.pop()
    if body_lines and _HORIZONTAL_RULE_RE.match(body_lines[-1]):
        body_lines.pop()

    return ReferencesSplit(
        body="".join(body_lines).rstrip(),
        references="".join(lines[start:end]),
        tail="".join(lines[end:]).strip("\n"),
    )
