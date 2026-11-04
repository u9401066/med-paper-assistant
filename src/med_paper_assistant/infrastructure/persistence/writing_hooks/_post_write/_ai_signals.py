"""Writing Hooks — A3b structural AI-writing signals."""

from __future__ import annotations

import re
from typing import Any

import structlog

from .._constants import (
    AI_COPULA_AVOIDANCE_VERBS,
    AI_EM_DASH_PATTERN,
    AI_FALSE_RANGE_PATTERN,
    AI_NEGATIVE_PARALLELISM_PATTERNS,
    AI_TRANSITION_WORDS,
)
from .._models import HookIssue, HookResult
from .._text_utils import strip_markdown_prose

logger = structlog.get_logger()


def _warning(section: str, message: str, suggestion: str) -> HookIssue:
    return HookIssue(
        hook_id="A3b",
        severity="WARNING",
        section=section,
        message=message,
        suggestion=suggestion,
    )


def _sentence_uniformity(sentences: list[str], section: str, issues: list[HookIssue]) -> float:
    sentence_lengths = [len(s.split()) for s in sentences]
    sent_cv = 0.0
    if len(sentence_lengths) >= 5:
        mean_len = sum(sentence_lengths) / len(sentence_lengths)
        if mean_len > 0:
            variance = sum((x - mean_len) ** 2 for x in sentence_lengths) / len(sentence_lengths)
            std_dev = variance**0.5
            sent_cv = std_dev / mean_len

        if sent_cv < 0.25:
            issues.append(
                _warning(
                    section,
                    f"Sentence lengths too uniform (CV={sent_cv:.2f}, threshold <0.25). "
                    "AI text tends to produce sentences of similar length.",
                    "Vary sentence structure: mix short punchy sentences with longer complex ones.",
                )
            )
    return sent_cv


def _transition_density(
    sentences: list[str], section: str, issues: list[HookIssue]
) -> tuple[int, dict[str, int]]:
    transition_starts = 0
    total_sentences = len(sentences)
    transition_used: dict[str, int] = {}
    if total_sentences >= 5:
        for s in sentences:
            first_word = s.split()[0].lower().rstrip(",") if s.split() else ""
            if first_word in AI_TRANSITION_WORDS:
                transition_starts += 1
                transition_used[first_word] = transition_used.get(first_word, 0) + 1

        transition_pct = transition_starts / total_sentences * 100
        if transition_pct > 20:
            issues.append(
                HookIssue(
                    hook_id="A3b",
                    severity="CRITICAL" if transition_pct > 35 else "WARNING",
                    section=section,
                    message=f"Excessive transition words at sentence start ({transition_pct:.0f}%, "
                    f"{transition_starts}/{total_sentences} sentences). AI-generated text "
                    "overuses connectors like 'Moreover', 'Furthermore', 'Additionally'.",
                    suggestion="Remove unnecessary transition words. Let ideas flow naturally "
                    "without signposting every connection.",
                )
            )
    return transition_starts, transition_used


def _starter_diversity(sentences: list[str], section: str, issues: list[HookIssue]) -> list[str]:
    starters: list[str] = []
    if len(sentences) >= 8:
        starters = [s.split()[0].lower() for s in sentences if s.split()]
        unique_ratio = len(set(starters)) / len(starters) if starters else 1.0
        if unique_ratio < 0.5:
            issues.append(
                _warning(
                    section,
                    f"Low sentence-starter diversity ({unique_ratio:.2f}, threshold <0.50). "
                    "Repetitive sentence openings suggest AI generation.",
                    "Vary how you begin sentences: use subjects, prepositional "
                    "phrases, subordinate clauses, or inverted structures.",
                )
            )
    return starters


def _list_of_three(prose: str, section: str, issues: list[HookIssue]) -> int:
    matches = re.findall(r"\b\w+(?:\s+\w+)?,\s+\w+(?:\s+\w+)?,\s+and\s+\w+", prose, re.IGNORECASE)
    if len(matches) > 3:
        issues.append(
            _warning(
                section,
                f"Overuse of 'X, Y, and Z' listing pattern ({len(matches)} instances). "
                "AI text frequently uses comma-separated triples.",
                "Vary enumeration: use 'such as X and Y', inline descriptions, "
                "or restructure to avoid formulaic lists.",
            )
        )
    return len(matches)


def _paragraph_uniformity(prose: str, section: str, issues: list[HookIssue]) -> int:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", prose) if len(p.strip().split()) >= 10]
    if len(paragraphs) >= 4:
        para_lengths = [len(p.split()) for p in paragraphs]
        mean_para = sum(para_lengths) / len(para_lengths)
        if mean_para > 0:
            para_variance = sum((x - mean_para) ** 2 for x in para_lengths) / len(para_lengths)
            para_cv = (para_variance**0.5) / mean_para
            if para_cv < 0.20:
                issues.append(
                    _warning(
                        section,
                        f"Paragraph lengths too uniform (CV={para_cv:.2f}, threshold <0.20). "
                        "Human writing naturally has varied paragraph lengths.",
                        "Break up long paragraphs, merge short ones, or let paragraph "
                        "length follow content needs rather than a template.",
                    )
                )
    return len(paragraphs)


def _negative_parallelism(prose: str, section: str, issues: list[HookIssue]) -> int:
    count = 0
    for pat in AI_NEGATIVE_PARALLELISM_PATTERNS:
        count += len(re.findall(pat, prose, re.IGNORECASE))
    if count > 2:
        issues.append(
            _warning(
                section,
                f"Negative parallelism overuse ({count} instances of "
                "'not just X, it's Y' / 'not only...but...'). AI text frequently "
                "uses this rhetorical device.",
                "Rephrase to direct statements instead of 'not just/only' constructions.",
            )
        )
    return count


def _copula_avoidance(prose: str, section: str, issues: list[HookIssue]) -> int:
    copula_count = 0
    copula_found: dict[str, int] = {}
    for verb in AI_COPULA_AVOIDANCE_VERBS:
        cnt = len(re.findall(rf"\b{re.escape(verb)}\b", prose, re.IGNORECASE))
        if cnt > 0:
            copula_count += cnt
            copula_found[verb] = cnt
    if copula_count > 3:
        issues.append(
            _warning(
                section,
                f"Copula avoidance detected ({copula_count} instances: "
                f"{', '.join(f'{v} ({c}x)' for v, c in copula_found.items())}). "
                "AI avoids 'is/has' by substituting grandiose verbs.",
                "Consider simpler alternatives: 'is', 'has', 'means'.",
            )
        )
    return copula_count


def _em_dash_overuse(prose: str, section: str, issues: list[HookIssue]) -> int:
    em_dash_count = len(re.findall(AI_EM_DASH_PATTERN, prose))
    word_count_for_density = len(prose.split())
    em_dash_per_500w = (
        (em_dash_count / word_count_for_density * 500) if word_count_for_density > 0 else 0
    )
    if em_dash_count > 3 and em_dash_per_500w > 3:
        issues.append(
            _warning(
                section,
                f"Em dash overuse ({em_dash_count} em dashes, "
                f"{em_dash_per_500w:.1f} per 500 words). "
                "AI overuses em dashes for parenthetical asides.",
                "Use commas, parentheses, or restructure sentences. "
                "Reserve em dashes for emphasis.",
            )
        )
    return em_dash_count


def _false_ranges(prose: str, section: str, issues: list[HookIssue]) -> int:
    matches = re.findall(AI_FALSE_RANGE_PATTERN, prose, re.IGNORECASE)
    if len(matches) > 4:
        issues.append(
            _warning(
                section,
                f"Excessive 'from X to Y' range patterns ({len(matches)} instances). "
                "AI text overuses vague range enumerations.",
                "Be specific with numbers or quantities instead of vague ranges.",
            )
        )
    return len(matches)


def _signal_stats(
    issues: list[HookIssue], sentences: list[str], starters: list[str], m: dict[str, Any]
) -> dict[str, Any]:
    total_sentences = len(sentences)
    transition_used = m["transition_used"]
    return {
        "ai_signal_count": len(issues),
        "sentence_cv": round(m["sent_cv"], 3),
        "transition_pct": round(m["transition_starts"] / total_sentences * 100, 1)
        if total_sentences > 0
        else 0,
        "starter_diversity": round(len(set(starters)) / len(starters), 3)
        if total_sentences >= 8 and starters
        else 1.0,
        "list_of_three_count": m["list_of_three"],
        "paragraph_count": m["paragraph_count"],
        "sentence_count": total_sentences,
        "transition_word_counts": dict(sorted(transition_used.items(), key=lambda x: -x[1])[:10]),
        "neg_parallelism_count": m["neg_parallel"],
        "copula_avoidance_count": m["copula"],
        "em_dash_count": m["em_dash"],
        "false_range_count": m["false_ranges"],
    }


class AiSignalHooksMixin:
    """A3b: structural signals of AI-generated text."""

    def check_ai_writing_signals(
        self,
        content: str,
        section: str = "manuscript",
    ) -> HookResult:
        """
        Hook A3b: Detect structural signals of AI-generated text.

        Goes beyond phrase matching (A3) to detect patterns that AI detectors
        like Gemini 3.1 flag: overly uniform sentence length, excessive
        transition words, low sentence-starter diversity, and formulaic
        list-of-three patterns.

        Args:
            content: Text to scan (full manuscript or section).
            section: Section name for reporting.
        """
        issues: list[HookIssue] = []

        prose = strip_markdown_prose(content)

        if len(prose) < 200:
            return HookResult(hook_id="A3b", passed=True, issues=[], stats={"skipped": True})

        sentences = [s.strip() for s in re.split(r"[.!?]+", prose) if len(s.strip().split()) >= 3]
        m: dict[str, Any] = {}
        m["sent_cv"] = _sentence_uniformity(sentences, section, issues)
        m["transition_starts"], m["transition_used"] = _transition_density(
            sentences, section, issues
        )
        starters = _starter_diversity(sentences, section, issues)
        m["list_of_three"] = _list_of_three(prose, section, issues)
        m["paragraph_count"] = _paragraph_uniformity(prose, section, issues)
        m["neg_parallel"] = _negative_parallelism(prose, section, issues)
        m["copula"] = _copula_avoidance(prose, section, issues)
        m["em_dash"] = _em_dash_overuse(prose, section, issues)
        m["false_ranges"] = _false_ranges(prose, section, issues)

        passed = len(issues) == 0
        stats = _signal_stats(issues, sentences, starters, m)
        logger.info(
            "Hook A3b complete",
            passed=passed,
            signal_count=len(issues),
            sent_cv=m["sent_cv"],
        )
        return HookResult(hook_id="A3b", passed=passed, issues=issues, stats=stats)
