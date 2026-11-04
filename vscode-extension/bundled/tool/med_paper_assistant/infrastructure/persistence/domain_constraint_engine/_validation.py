"""Rule checkers for DomainConstraintEngine.validate_against_constraints ('Sand Spreader')."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ._models import ConstraintViolation

CONSENT_KEYWORDS = [
    "informed consent",
    "patient consent",
    "written consent",
    "irb approval",
    "irb waiver",
    "ethics committee",
    "ethical approval",
    "institutional review board",
]


@dataclass(frozen=True)
class _CheckContext:
    """One constraint evaluated against one piece of content."""

    constraint: dict[str, Any]
    content: str
    content_lower: str
    word_count: int
    section: str

    @property
    def rule(self) -> Any:
        return self.constraint.get("rule", "")

    @property
    def params(self) -> dict[str, Any]:
        return self.constraint.get("params") or {}

    @property
    def is_manuscript(self) -> bool:
        return self.section == "manuscript"

    def violation(
        self, message: str, suggestion: str, section: str | None = None
    ) -> ConstraintViolation:
        return ConstraintViolation(
            constraint_id=self.constraint.get("id", ""),
            rule=self.rule,
            category=self.constraint.get("category", ""),
            severity=self.constraint.get("severity", "WARNING"),
            message=message,
            section=self.section if section is None else section,
            suggestion=suggestion,
        )


def _check_anti_ai_vocabulary(ctx: _CheckContext) -> list[ConstraintViolation]:
    violations: list[ConstraintViolation] = []
    for pattern in ctx.params.get("forbidden_patterns", []):
        if re.search(rf"\b{re.escape(pattern.lower())}\b", ctx.content_lower):
            violations.append(
                ctx.violation(
                    f"AI-typical phrase detected: '{pattern}'",
                    f"Rephrase to avoid '{pattern}'",
                )
            )
    return violations


def _check_word_count_range(ctx: _CheckContext) -> list[ConstraintViolation]:
    min_w = ctx.params.get("min_words", 0)
    max_w = ctx.params.get("max_words", 999999)
    if ctx.word_count < min_w:
        return [
            ctx.violation(
                f"Word count {ctx.word_count} below minimum {min_w}",
                f"Expand content to at least {min_w} words",
            )
        ]
    if ctx.word_count > max_w:
        return [
            ctx.violation(
                f"Word count {ctx.word_count} exceeds maximum {max_w}",
                f"Reduce content to at most {max_w} words",
            )
        ]
    return []


def _check_required_sections(ctx: _CheckContext) -> list[ConstraintViolation]:
    if not ctx.is_manuscript:
        return []
    violations: list[ConstraintViolation] = []
    for req_section in ctx.params.get("sections", []):
        # Check if section heading exists via regex (any heading level)
        heading_pattern = rf"^\s*#{{1,4}}\s+{re.escape(req_section)}\s*$"
        if not re.search(heading_pattern, ctx.content, re.IGNORECASE | re.MULTILINE):
            violations.append(
                ctx.violation(
                    f"Required section '{req_section}' not found",
                    f"Add '## {req_section}' section",
                    section="manuscript",
                )
            )
    return violations


def _check_methods_before_results(ctx: _CheckContext) -> list[ConstraintViolation]:
    if not ctx.is_manuscript:
        return []
    methods_match = re.search(
        r"^\s*#{1,4}\s+Methods\s*$", ctx.content, re.IGNORECASE | re.MULTILINE
    )
    results_match = re.search(
        r"^\s*#{1,4}\s+Results\s*$", ctx.content, re.IGNORECASE | re.MULTILINE
    )
    if methods_match and results_match and methods_match.start() > results_match.start():
        return [
            ctx.violation(
                "Methods section appears after Results",
                "Move Methods section before Results",
                section="manuscript",
            )
        ]
    return []


def _check_minimum_references(ctx: _CheckContext) -> list[ConstraintViolation]:
    min_refs = ctx.params.get("min_references", 0)
    # Count unique wikilink citations [[...]]
    wikilinks = set(re.findall(r"\[\[([^\]]+)\]\]", ctx.content))
    if len(wikilinks) >= min_refs:
        return []
    return [
        ctx.violation(
            f"Only {len(wikilinks)} unique citations found, minimum {min_refs} required",
            f"Add at least {min_refs - len(wikilinks)} more citations",
        )
    ]


def _check_patient_consent_mentioned(ctx: _CheckContext) -> list[ConstraintViolation]:
    if not ctx.is_manuscript:
        return []
    if any(kw in ctx.content_lower for kw in CONSENT_KEYWORDS):
        return []
    return [
        ctx.violation(
            "No mention of patient consent or IRB approval found",
            "Add a statement about informed consent or IRB approval/waiver",
            section="manuscript",
        )
    ]


def _split_section_paragraphs(content: str) -> dict[str, list[str]]:
    """Map each heading to its paragraphs (non-empty, 3+ words)."""
    headings = list(re.compile(r"^\s*#{1,4}\s+(.+?)\s*$", re.MULTILINE).finditer(content))
    section_texts: dict[str, list[str]] = {}
    if len(headings) < 2:
        return section_texts
    for i, heading in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        sec_content = content[heading.end() : end].strip()
        section_texts[heading.group(1).strip()] = [
            p.strip() for p in sec_content.split("\n\n") if p.strip() and len(p.split()) >= 3
        ]
    return section_texts


def _check_no_overlap_between_sections(ctx: _CheckContext) -> list[ConstraintViolation]:
    if not ctx.is_manuscript:
        return []
    violations: list[ConstraintViolation] = []
    seen_paragraphs: dict[str, str] = {}  # paragraph -> section_name
    for sec_name, paragraphs in _split_section_paragraphs(ctx.content).items():
        for para in paragraphs:
            # Normalize for comparison
            normalized = " ".join(para.lower().split())
            if normalized in seen_paragraphs:
                violations.append(
                    ctx.violation(
                        f"Duplicate paragraph found in "
                        f"'{seen_paragraphs[normalized]}' and '{sec_name}'",
                        "Remove or rewrite the duplicated paragraph",
                        section="manuscript",
                    )
                )
                break  # One violation per section pair is enough
            seen_paragraphs[normalized] = sec_name
    return violations


_RULE_CHECKERS: dict[str, Callable[[_CheckContext], list[ConstraintViolation]]] = {
    "anti_ai_vocabulary": _check_anti_ai_vocabulary,
    "word_count_range": _check_word_count_range,
    "required_sections": _check_required_sections,
    "methods_before_results": _check_methods_before_results,
    "minimum_references": _check_minimum_references,
    "patient_consent_mentioned": _check_patient_consent_mentioned,
    "no_overlap_between_sections": _check_no_overlap_between_sections,
}


def collect_violations(
    constraints: list[dict[str, Any]], content: str, section: str
) -> list[ConstraintViolation]:
    """Run every constraint's rule checker (if any) against the content."""
    content_lower = content.lower()
    word_count = len(content.split())
    violations: list[ConstraintViolation] = []
    for constraint in constraints:
        ctx = _CheckContext(constraint, content, content_lower, word_count, section)
        checker = _RULE_CHECKERS.get(ctx.rule) if isinstance(ctx.rule, str) else None
        if checker is not None:
            violations.extend(checker(ctx))
    return violations
