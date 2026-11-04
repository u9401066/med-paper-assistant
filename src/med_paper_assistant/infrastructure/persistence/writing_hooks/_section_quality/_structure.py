"""Writing Hooks — B12 Introduction funnel and B13 Discussion structure."""

from __future__ import annotations

import re
from typing import Any

from .._models import HookIssue, HookResult
from .._section_tree import first_section_text

_OBJECTIVE_MARKERS = [
    r"\b(?:aim|objective|purpose|goal)\s+(?:of|was|is)\b",
    r"\bwe\s+(?:aimed|sought|investigated|hypothesized|examined)\b",
    r"\bthis\s+study\s+(?:aimed|sought|examined|investigated|evaluated)\b",
    r"\bthe\s+(?:aim|objective|purpose)\b",
    r"\bherein\b",
    r"\bpresent\s+study\b",
    r"\bto\s+(?:evaluate|investigate|examine|assess|determine|compare|explore)\b",
]

_GAP_MARKERS = [
    r"\b(?:however|nevertheless|yet|despite|although)\b",
    r"\b(?:gap|limitation|lacking|unknown|unclear|understudied|unexplored)\b",
    r"\b(?:no\s+(?:study|data|evidence|report)|remains?\s+(?:unclear|unknown|elusive))\b",
    r"\b(?:limited|scarce|sparse|insufficient)\s+(?:data|evidence|information|research)\b",
    r"\b(?:has|have)\s+not\s+been\s+(?:studied|examined|explored|investigated)\b",
]

_RESULTS_PREVIEW_PATTERNS = [
    r"\bour\s+(?:results|findings|data)\s+(?:show|demonstrate|reveal|indicate)\b",
    r"\bwe\s+(?:found|observed|demonstrated|showed)\s+(?:that|a|an|the|significant)\b",
    r"\bthe\s+results?\s+(?:of|from)\s+(?:this|our|the\s+(?:present|current))\s+study\b",
]

_FINDINGS_MARKERS = [
    r"\b(?:main|principal|key|major|primary|important)\s+(?:finding|result|outcome)\b",
    r"\b(?:our|this|the\s+present)\s+study\s+(?:found|showed|demonstrated|revealed)\b",
    r"\b(?:we\s+(?:found|observed|demonstrated))\b",
    r"\bto\s+(?:our|the)\s+(?:best\s+of\s+)?knowledge\b",
]

_LIMITATION_MARKERS = [
    r"\blimitation",
    r"\bweakness",
    r"\bshortcoming",
    r"\bdrawback",
    r"\bcaveat",
    r"\b(?:should|must)\s+be\s+interpreted\s+with\s+caution\b",
    r"\bseveral\s+(?:potential\s+)?limitations?\b",
]

_IMPLICATION_MARKERS = [
    r"\bimplication",
    r"\bclinical\s+(?:practice|significance|relevance|utility)\b",
    r"\bpractical\s+(?:implication|application|relevance)\b",
    r"\bfuture\s+(?:research|studies|investigation|direction)\b",
    r"\btranslational\b",
    r"\b(?:may|could)\s+(?:help|improve|enhance|facilitate|guide|inform)\b",
]


def _intro_objective_issues(paragraphs: list[str], stats: dict[str, Any]) -> list[HookIssue]:
    # Last paragraph should contain objective markers
    if not paragraphs:
        return []
    last_para = paragraphs[-1].lower()
    has_objective = any(re.search(p, last_para) for p in _OBJECTIVE_MARKERS)
    stats["has_objective"] = has_objective
    if has_objective:
        return []
    return [
        HookIssue(
            hook_id="B12",
            severity="WARNING",
            section="Introduction",
            message="Last paragraph of Introduction should state the study objective/aim",
            suggestion="Add a clear objective statement: 'This study aimed to...' or 'We sought to...'",
        )
    ]


def _intro_gap_issues(paragraphs: list[str], stats: dict[str, Any]) -> list[HookIssue]:
    if len(paragraphs) < 2:
        return []
    gap_zone = (
        " ".join(p.lower() for p in paragraphs[-3:])
        if len(paragraphs) >= 3
        else paragraphs[-1].lower()
    )
    has_gap = any(re.search(p, gap_zone) for p in _GAP_MARKERS)
    stats["has_gap_statement"] = has_gap
    if has_gap:
        return []
    return [
        HookIssue(
            hook_id="B12",
            severity="WARNING",
            section="Introduction",
            message="Introduction should identify a knowledge gap or limitation of prior work",
            suggestion="Add gap language: 'However, no study has...', 'It remains unclear whether...'",
        )
    ]


def _intro_results_preview_issues(intro_text: str) -> list[HookIssue]:
    for pattern in _RESULTS_PREVIEW_PATTERNS:
        if re.search(pattern, intro_text, re.IGNORECASE):
            return [
                HookIssue(
                    hook_id="B12",
                    severity="CRITICAL",
                    section="Introduction",
                    message="Introduction should NOT preview study results",
                    suggestion="Remove results from Introduction. Results belong in the Results section.",
                )
            ]
    return []


def _discussion_findings_issues(paragraphs: list[str], stats: dict[str, Any]) -> list[HookIssue]:
    first_para = paragraphs[0].lower() if paragraphs else ""
    has_main_finding = any(re.search(p, first_para) for p in _FINDINGS_MARKERS)
    stats["has_main_finding"] = has_main_finding
    if has_main_finding or not paragraphs:
        return []
    return [
        HookIssue(
            hook_id="B13",
            severity="WARNING",
            section="Discussion",
            message="First paragraph should summarize the main findings",
            suggestion="Start with: 'The main/principal finding of this study was...' or 'Our study demonstrated...'",
        )
    ]


def _discussion_citation_issues(discussion_text: str, stats: dict[str, Any]) -> list[HookIssue]:
    citation_count = len(re.findall(r"\[\[[^\]]+\]\]", discussion_text))
    stats["citation_count"] = citation_count
    if citation_count >= 3:
        return []
    return [
        HookIssue(
            hook_id="B13",
            severity="WARNING",
            section="Discussion",
            message=f"Discussion has only {citation_count} citation(s). Should compare findings with prior literature.",
            suggestion="Add comparisons: 'Consistent with Smith et al. [[ref]], we found...' or 'In contrast to...'",
        )
    ]


def _discussion_limitation_issues(disc_lower: str, stats: dict[str, Any]) -> list[HookIssue]:
    has_limitations = any(re.search(p, disc_lower) for p in _LIMITATION_MARKERS)
    stats["has_limitations"] = has_limitations
    if has_limitations:
        return []
    return [
        HookIssue(
            hook_id="B13",
            severity="CRITICAL",
            section="Discussion",
            message="Discussion MUST contain a Limitations paragraph",
            suggestion="Add: 'This study has several limitations. First, ...' Discuss design constraints, generalizability, etc.",
        )
    ]


def _discussion_implication_issues(disc_lower: str, stats: dict[str, Any]) -> list[HookIssue]:
    has_implications = any(re.search(p, disc_lower) for p in _IMPLICATION_MARKERS)
    stats["has_implications"] = has_implications
    if has_implications:
        return []
    return [
        HookIssue(
            hook_id="B13",
            severity="WARNING",
            section="Discussion",
            message="Discussion should mention clinical/practical implications or future directions",
            suggestion="Add: 'These findings suggest that...' or 'Future studies should...'",
        )
    ]


class SectionStructureHooksMixin:
    """B12 / B13: Introduction funnel and Discussion completeness."""

    def check_intro_structure(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook B12: Verify Introduction follows the funnel structure.

        Expected: (1) Broad context → (2) Evidence with citations →
        (3) Knowledge gap → (4) Study objective.
        Also checks: no results preview in Introduction.
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {}

        sections = self._parse_sections_full(content)
        intro_text = first_section_text(sections, "introduction")

        if not intro_text:
            return HookResult(hook_id="B12", passed=True, issues=issues, stats=stats)

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", intro_text) if p.strip()]
        paragraphs = [p for p in paragraphs if not p.startswith("|") and not p.startswith("- ")]
        stats["paragraph_count"] = len(paragraphs)

        if len(paragraphs) < 3:
            issues.append(
                HookIssue(
                    hook_id="B12",
                    severity="WARNING",
                    section="Introduction",
                    message=f"Introduction has only {len(paragraphs)} paragraph(s). Typically needs ≥3 for proper funnel structure.",
                    suggestion="Structure: (1) Broad context → (2) Evidence with citations → (3) Gap → (4) Objective",
                )
            )

        issues.extend(_intro_objective_issues(paragraphs, stats))
        issues.extend(_intro_gap_issues(paragraphs, stats))
        issues.extend(_intro_results_preview_issues(intro_text))

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B12", passed=passed, issues=issues, stats=stats)

    def check_discussion_structure(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook B13: Verify Discussion has required structural components.

        Required: main findings, literature comparison, limitations (CRITICAL),
        implications. Limitations is CRITICAL if missing.
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {}

        sections = self._parse_sections_full(content)
        discussion_text = first_section_text(sections, "discussion")

        if not discussion_text:
            return HookResult(hook_id="B13", passed=True, issues=issues, stats=stats)

        disc_lower = discussion_text.lower()
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", discussion_text) if p.strip()]
        paragraphs = [p for p in paragraphs if not p.startswith("|")]
        stats["paragraph_count"] = len(paragraphs)

        issues.extend(_discussion_findings_issues(paragraphs, stats))
        issues.extend(_discussion_citation_issues(discussion_text, stats))
        issues.extend(_discussion_limitation_issues(disc_lower, stats))
        issues.extend(_discussion_implication_issues(disc_lower, stats))

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B13", passed=passed, issues=issues, stats=stats)
