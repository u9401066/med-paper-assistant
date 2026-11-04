"""Shared parsing helpers for review reports (used by R1 and R2)."""

from __future__ import annotations

import re

from ._constants import SEVERITY_KEYWORDS


class ReportParsingMixin:
    """Severity counting over review-report Markdown."""

    def _count_severity_in_report(self, content: str, severity: str) -> int:
        """Count issues of a given severity in review report."""
        # Try YAML frontmatter first
        yaml_match = re.search(rf"^\s*{severity}:\s*(\d+)", content, re.MULTILINE)
        if yaml_match:
            return int(yaml_match.group(1))

        # Fall back to counting headings/list items with severity keyword
        keywords = SEVERITY_KEYWORDS.get(severity, [severity])
        count = 0
        for keyword in keywords:
            count += len(
                re.findall(
                    rf"(?:^|\n)\s*[-*]\s*.*\b{keyword}\b",
                    content,
                    re.IGNORECASE,
                )
            )
        return count

    def _count_total_issues_in_report(self, content: str) -> int:
        """Count total issues across all severities in review report."""
        total = 0
        for severity in ("major", "minor", "optional"):
            total += self._count_severity_in_report(content, severity)
        # If YAML frontmatter didn't work, count numbered/bulleted items under issue headings
        if total == 0:
            total = len(
                re.findall(
                    r"(?:^|\n)\s*(?:\d+[\.\)]\s|[-*]\s+(?!#))",
                    content,
                )
            )
        return total
