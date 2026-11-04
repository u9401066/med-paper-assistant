"""Writing Hooks — A6 internal paragraph overlap detection."""

from __future__ import annotations

import re

import structlog

from .._models import HookIssue, HookResult

logger = structlog.get_logger()


def _overlap_paragraphs(content: str, min_ngram: int) -> list[tuple[str, str]]:
    paragraphs: list[tuple[str, str]] = []
    current_section = "Unknown"
    for block in re.split(r"\n{2,}", content):
        block = block.strip()
        if not block:
            continue
        heading_match = re.match(r"^#{1,3}\s+(.+)", block)
        if heading_match:
            current_section = heading_match.group(1).strip()
            continue
        words = block.split()
        if len(words) < min_ngram:
            continue
        paragraphs.append((current_section, block))
    return paragraphs


def _extract_ngrams(text: str, n: int) -> set[str]:
    # Strip statistical notation to avoid false positives
    # e.g. "F(X,Y) = Z, p < 0.001, η²p = 0.12" → common in Results
    cleaned = re.sub(
        r"[FtZrR]\s*\([^)]*\)\s*=\s*[\d.]+"
        r"|p\s*[<>=]+\s*[\d.]+"
        r"|η[²2]p?\s*=\s*[\d.]+"
        r"|\bCI\s*[:=]?\s*\[[^]]*\]"
        r"|\bd\s*=\s*[\d.]+"
        r"|\bOR\s*=\s*[\d.]+"
        r"|\bHR\s*=\s*[\d.]+"
        r"|\bRR\s*=\s*[\d.]+"
        r"|\bAOR\s*=\s*[\d.]+"
        r"|\bβ\s*=\s*[\-\d.]+"
        r"|\bSD\s*=\s*[\d.]+"
        r"|\bSE\s*=\s*[\d.]+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    words = re.findall(r"\b[a-z]+\b", cleaned.lower())
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def _flag_shared_pairs(
    paragraphs: list[tuple[str, str]], min_ngram: int, threshold: int
) -> list[tuple[int, int, int]]:
    para_ngrams: list[set[str]] = [_extract_ngrams(text, min_ngram) for _, text in paragraphs]

    flagged_pairs: list[tuple[int, int, int]] = []
    for i in range(len(paragraphs)):
        for j in range(i + 1, len(paragraphs)):
            shared = para_ngrams[i] & para_ngrams[j]
            if len(shared) >= threshold:
                flagged_pairs.append((i, j, len(shared)))
    return flagged_pairs


def _overlap_issues(
    paragraphs: list[tuple[str, str]],
    flagged_pairs: list[tuple[int, int, int]],
    min_ngram: int,
    threshold: int,
) -> list[HookIssue]:
    issues: list[HookIssue] = []
    for i, j, shared_count in flagged_pairs:
        sec_i, text_i = paragraphs[i]
        sec_j, text_j = paragraphs[j]
        preview_i = text_i[:80].replace("\n", " ") + "..."
        preview_j = text_j[:80].replace("\n", " ") + "..."

        severity = "CRITICAL" if shared_count >= threshold * 2 else "WARNING"
        issues.append(
            HookIssue(
                hook_id="A6",
                severity=severity,
                section=f"{sec_i} ↔ {sec_j}",
                message=f"{shared_count} shared {min_ngram}-grams between paragraphs",
                location=f"P{i + 1} ({sec_i}): '{preview_i}' vs P{j + 1} ({sec_j}): '{preview_j}'",
                suggestion="Rephrase one of the paragraphs to avoid repetitive phrasing",
            )
        )
    return issues


class OverlapHooksMixin:
    """A6: self-plagiarism / copy-paste residue between paragraphs."""

    def check_overlap(
        self,
        content: str,
        min_ngram: int = 6,
        threshold: int = 3,
    ) -> HookResult:
        """
        Hook A6: Detect internal paragraph overlap (copy-paste residue).

        Splits content into paragraphs, extracts n-grams, and finds
        n-grams that appear in multiple paragraphs.

        Args:
            content: Full manuscript text.
            min_ngram: Minimum n-gram size (words). Default 6.
            threshold: Minimum shared n-grams between two paragraphs
                       to flag as WARNING. Default 3.
        """
        paragraphs = _overlap_paragraphs(content, min_ngram)

        if len(paragraphs) < 2:
            return HookResult(
                hook_id="A6", passed=True, stats={"paragraphs_checked": len(paragraphs)}
            )

        flagged_pairs = _flag_shared_pairs(paragraphs, min_ngram, threshold)
        issues = _overlap_issues(paragraphs, flagged_pairs, min_ngram, threshold)

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "paragraphs_checked": len(paragraphs),
            "flagged_pairs": len(flagged_pairs),
            "max_shared_ngrams": max((s for _, _, s in flagged_pairs), default=0),
        }

        logger.info(
            "Hook A6 complete",
            passed=passed,
            paragraphs=len(paragraphs),
            flagged_pairs=len(flagged_pairs),
        )
        return HookResult(hook_id="A6", passed=passed, issues=issues, stats=stats)
