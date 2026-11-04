"""Writing Hooks — B9 tense, B10 paragraph quality, B11 results objectivity, B15 hedging."""

from __future__ import annotations

import re
from typing import Any

from .._models import HookIssue, HookResult
from .._section_tree import first_section_text

_PRESENT_STUDY_VERBS = re.compile(
    r"\b(?:we\s+(?:measure|analyze|collect|record|assess|evaluate|perform|conduct"
    r"|administer|randomize|enroll|recruit|include|exclude|calculate|compare"
    r"|observe|monitor|determine|identify|classify|divide|assign|screen"
    r"|select|extract|obtain|gather|test|examine|sample|survey))\b",
    re.IGNORECASE,
)

_RESULTS_PRESENT_PATTERNS = re.compile(
    r"(?:^|\.\s+)(?:The\s+(?:result|data|analysis|finding|outcome|difference|comparison)"
    r"\s+(?:show|indicate|demonstrate|reveal|suggest|confirm|yield)s?\b)",
    re.IGNORECASE,
)

_INTERPRETIVE_PATTERNS = [
    (r"\bsuggesting\s+(?:that|a|an|the)\b", "suggesting that..."),
    (r"\bindicating\s+(?:that|a|an|the)\b", "indicating that..."),
    (r"\bdemonstrating\s+(?:that|a|an|the)\b", "demonstrating that..."),
    (r"\bimplying\s+(?:that|a|an|the)\b", "implying that..."),
    (
        r"\bthis\s+(?:suggests|indicates|implies|demonstrates)\b",
        "this suggests/indicates...",
    ),
    (
        r"\b(?:may|might|could)\s+(?:be|have|suggest|indicate|reflect|represent)\b",
        "may/might/could (speculative)",
    ),
    (r"\bpossibly\b", "possibly"),
    (r"\bpresumably\b", "presumably"),
    (r"\bapparently\b", "apparently"),
    (r"\binterestingly\b", "interestingly"),
    (r"\bsurprisingly\b", "surprisingly"),
    (r"\bremarkably\b", "remarkably"),
    (r"\bunexpectedly\b", "unexpectedly"),
    (
        r"\b(?:it is|these are)\s+(?:likely|possible|probable|plausible)\b",
        "it is likely/possible...",
    ),
    (
        r"\bthis (?:finding|result|observation)\s+(?:is consistent with|supports|corroborates)\b",
        "this finding supports... (belongs in Discussion)",
    ),
    (
        r"\b(?:we believe|we speculate|we hypothesize|in our opinion)\b",
        "we believe/speculate (opinion)",
    ),
]

_HEDGING_PATTERNS = [
    r"\bmay\s+(?:be|have|suggest|indicate|play|contribute)\b",
    r"\bmight\s+(?:be|have|suggest|indicate|play|contribute)\b",
    r"\bcould\s+(?:be|have|suggest|indicate|play|contribute)\b",
    r"\bpossibly\b",
    r"\bpotentially\b",
    r"\bperhaps\b",
    r"\bseems?\s+to\b",
    r"\bappears?\s+to\b",
    r"\btends?\s+to\b",
    r"\bit\s+is\s+(?:possible|conceivable|plausible)\b",
    r"\bto\s+some\s+(?:extent|degree)\b",
    r"\bin\s+part\b",
    r"\brelatively\b",
    r"\bsomewhat\b",
]


def _split_paragraphs(content: str) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue
        if not stripped:
            if current:
                paragraphs.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append("\n".join(current))
    return paragraphs


def _paragraph_issues(
    index: int, text: str, word_count: int, n_sentences: int, section: str, stats: dict[str, Any]
) -> list[HookIssue]:
    issues: list[HookIssue] = []
    if word_count > 250:
        stats["too_long"] = stats.get("too_long", 0) + 1
        issues.append(
            HookIssue(
                hook_id="B10",
                severity="WARNING",
                section=section,
                message=f"Paragraph {index} is very long ({word_count} words, {n_sentences} sentences). Consider splitting.",
                location=text[:80] + "...",
                suggestion="Split into smaller paragraphs, each focused on one idea",
            )
        )

    if n_sentences <= 1 and word_count > 10:
        if section.lower() not in ("results",):
            stats["too_short"] = stats.get("too_short", 0) + 1
            issues.append(
                HookIssue(
                    hook_id="B10",
                    severity="INFO",
                    section=section,
                    message=f"Paragraph {index} has only 1 sentence. Consider merging or expanding.",
                    location=text[:80],
                    suggestion="Develop the idea further or merge with adjacent paragraph",
                )
            )
    return issues


def _methods_tense_issues(content: str, section: str, stats: dict[str, Any]) -> list[HookIssue]:
    matches = _PRESENT_STUDY_VERBS.findall(content)
    stats["present_verbs"] = len(matches)
    if not matches:
        return []
    unique = set(m.lower() for m in matches)
    return [
        HookIssue(
            hook_id="B9",
            severity="CRITICAL" if len(matches) >= 3 else "WARNING",
            section=section,
            message=f"Methods should use past tense. Found {len(matches)} present-tense study verb(s): {', '.join(list(unique)[:5])}",
            suggestion="Change to past tense (e.g., 'we measured', 'patients received')",
        )
    ]


def _results_tense_issues(content: str, section: str, stats: dict[str, Any]) -> list[HookIssue]:
    we_present = _PRESENT_STUDY_VERBS.findall(content)
    data_present = _RESULTS_PRESENT_PATTERNS.findall(content)
    total = len(we_present) + len(data_present)
    stats["present_verbs"] = total
    if not total:
        return []
    return [
        HookIssue(
            hook_id="B9",
            severity="CRITICAL" if total >= 3 else "WARNING",
            section=section,
            message=f"Results should use past tense. Found {total} present-tense verb(s)",
            suggestion="Change to past tense (e.g., 'showed', 'demonstrated', 'was observed')",
        )
    ]


def _hedging_issues(
    content: str, section: str, total_words: int, stats: dict[str, Any]
) -> list[HookIssue]:
    total_hedges = 0
    found_phrases: list[str] = []

    for pattern in _HEDGING_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        total_hedges += len(matches)
        found_phrases.extend(matches)

    stats["hedge_count"] = total_hedges
    stats["words"] = total_words
    stats["density_per_1000"] = round(total_hedges * 1000 / max(total_words, 1), 1)

    if total_words <= 100:
        return []
    density = total_hedges * 1000 / total_words
    if density > 6:
        return [
            HookIssue(
                hook_id="B15",
                severity="CRITICAL",
                section=section,
                message=f"Excessive hedging: {total_hedges} hedging phrases ({density:.1f}/1000 words). Weakens the manuscript.",
                location="; ".join(list(dict.fromkeys(found_phrases))[:8]),
                suggestion="Replace hedges with direct statements. E.g., 'may suggest' → 'suggests', 'could be' → 'is'",
            )
        ]
    if density > 3:
        return [
            HookIssue(
                hook_id="B15",
                severity="WARNING",
                section=section,
                message=f"High hedging density: {total_hedges} hedging phrases ({density:.1f}/1000 words).",
                location="; ".join(list(dict.fromkeys(found_phrases))[:8]),
                suggestion="Consider strengthening some hedged statements with direct language",
            )
        ]
    return []


class SectionStyleHooksMixin:
    """B9 / B10 / B11 / B15: tense, paragraph, objectivity and hedging checks."""

    def check_section_tense(
        self,
        content: str,
        section: str = "manuscript",
    ) -> HookResult:
        """
        Hook B9: Verify verb tense matches section conventions.

        Scientific writing convention:
        - Methods / Results → past tense
        - Introduction / Discussion → present tense for established facts
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {"section": section, "present_verbs": 0, "past_verbs": 0}

        sec_lower = section.lower()

        if sec_lower in ("methods", "materials and methods", "study design"):
            issues.extend(_methods_tense_issues(content, section, stats))
        elif sec_lower in ("results",):
            issues.extend(_results_tense_issues(content, section, stats))

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B9", passed=passed, issues=issues, stats=stats)

    def check_paragraph_quality(
        self,
        content: str,
        section: str = "manuscript",
    ) -> HookResult:
        """
        Hook B10: Check paragraph structure quality.

        Checks paragraph length (too short / too long) and single-sentence paragraphs.
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {"total_paragraphs": 0, "too_short": 0, "too_long": 0}

        paragraphs = _split_paragraphs(content)
        stats["total_paragraphs"] = len(paragraphs)

        for i, para in enumerate(paragraphs, 1):
            text = para.strip()
            if not text or text.startswith("|") or text.startswith("- "):
                continue

            word_count = self._count_words(text)
            sentences = re.split(r"[.!?]+\s+|[.!?]+$", text)
            sentences = [s for s in sentences if s.strip()]
            issues.extend(_paragraph_issues(i, text, word_count, len(sentences), section, stats))

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B10", passed=passed, issues=issues, stats=stats)

    def check_results_interpretation(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook B11: Detect interpretive/speculative language in Results.

        Results section should present data objectively without interpretation.
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {"interpretive_count": 0}

        sections = self._parse_sections_full(content)
        results_text = first_section_text(sections, "result")

        if not results_text:
            return HookResult(hook_id="B11", passed=True, issues=issues, stats=stats)

        found_items: list[str] = []
        for pattern, label in _INTERPRETIVE_PATTERNS:
            matches = re.findall(pattern, results_text, re.IGNORECASE)
            if matches:
                found_items.extend([label] * len(matches))

        stats["interpretive_count"] = len(found_items)

        if found_items:
            unique_labels = list(dict.fromkeys(found_items))
            severity = "CRITICAL" if len(found_items) >= 5 else "WARNING"
            issues.append(
                HookIssue(
                    hook_id="B11",
                    severity=severity,
                    section="Results",
                    message=f"Results contains {len(found_items)} interpretive/speculative phrase(s): {', '.join(unique_labels[:6])}",
                    suggestion="Move interpretation to Discussion. Results should only state observed data and statistical outcomes.",
                )
            )

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B11", passed=passed, issues=issues, stats=stats)

    def check_hedging_density(
        self,
        content: str,
        section: str = "manuscript",
    ) -> HookResult:
        """
        Hook B15: Detect overuse of hedging / weak language.

        Thresholds: > 3 per 1000 words = WARNING, > 6 = CRITICAL.
        """
        stats: dict[str, Any] = {}
        total_words = self._count_words(content)
        issues = _hedging_issues(content, section, total_words, stats)

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B15", passed=passed, issues=issues, stats=stats)
