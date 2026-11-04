"""Writing Hooks — sample-size (N-value) extraction helpers for hook C3."""

from __future__ import annotations

import re

from ._models import HookIssue

_NUM = r"(\d{1,3}(?:,\d{3})+|\d+)"
_NOUN = r"(?:patients|subjects|participants|individuals|cases|controls|samples|enrolled)"

# Totals are compared strictly; plain "<n> patients" counts may be subgroups.
TOTAL_PATTERNS = [
    (rf"\b[Nn]\s*=\s*{_NUM}(?![\d,]*\d)", "N="),
    (rf"\btotal\s+of\s+{_NUM}\s+{_NOUN}", "total of"),
]
SUBGROUP_PATTERNS = [
    (rf"(?<![\d,.]){_NUM}\s+{_NOUN}", "count of"),
]


def extract_n_values(text: str, patterns: list[tuple[str, str]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for pattern, label in patterns:
        values = {v.replace(",", "") for v in re.findall(pattern, text, re.IGNORECASE)}
        if values:
            result[label] = values
    return result


def methods_n_values(methods_text: str) -> set[str]:
    values: set[str] = set()
    for patterns in (TOTAL_PATTERNS, SUBGROUP_PATTERNS):
        for vals in extract_n_values(methods_text, patterns).values():
            values |= vals
    return values


def n_value_issues(section_name: str, text: str, methods_values: set[str]) -> list[HookIssue]:
    """C3 issues for N-values in ``text`` that Methods does not report."""
    issues: list[HookIssue] = []
    for patterns, severity in ((TOTAL_PATTERNS, "CRITICAL"), (SUBGROUP_PATTERNS, "INFO")):
        for label, values in extract_n_values(text, patterns).items():
            for val in sorted(values):
                if val in methods_values or int(val) <= 1:
                    continue
                shown = f"N={val}" if label == "N=" else f"{label} {val}"
                issues.append(
                    HookIssue(
                        hook_id="C3",
                        severity=severity,
                        section=section_name,
                        message=(
                            f"N-value {shown} in {section_name} "
                            f"not found in Methods (Methods has: {sorted(methods_values)})"
                        ),
                        suggestion=f"Verify {shown} is correct or add to Methods",
                    )
                )
    return issues
