"""Writing Hooks — C14 claim-evidence alignment."""

from __future__ import annotations

import re

from med_paper_assistant.domain.services.citation_converter import (
    extract_reference_wikilink_keys,
)

from .._models import HookIssue, HookResult

_STRONG_CLAIM_PATTERNS = [
    (r"\bfundamentally\s+changes?\b", "fundamentally changes", "magnitude", "CRITICAL"),
    (r"\bdirectly\s+proves?\b", "directly proves", "causality", "CRITICAL"),
    (r"\bproves?\b", "proves", "causality", "CRITICAL"),
    (
        r"\bfirst\s+(?:known|reported|study|case|demonstration|description|evidence|trial|analysis)\b",
        "first",
        "novelty",
        "CRITICAL",
    ),
    (r"\bnovel\b", "novel", "novelty", "CRITICAL"),
    (r"\bunique\b", "unique", "novelty", "CRITICAL"),
    (r"\bunprecedented\b", "unprecedented", "novelty", "CRITICAL"),
    (r"\bdefinitive(?:ly)?\b", "definitive", "certainty", "WARNING"),
    (r"\bcausal(?:ly|ity)?\b", "causal", "causality", "CRITICAL"),
    (r"\bsuperior(?:ity)?\b", "superior", "superiority", "CRITICAL"),
    (r"\bdramatically\b", "dramatically", "magnitude", "WARNING"),
]

_EVIDENCE_PATTERNS = [
    r"\[@[^\]]+\]",
    r"\bPMID\s*:?\s*\d+",
    r"\b(?:Figure|Table|Supplementary\s+(?:Figure|Table))\s+\d+",
    r"\bsource-material(?:s)?\b",
    r"\basset-aware\b",
    r"\bdata[-\s]?artifact\b",
]


def _match_strong_claim(
    sentence: str, patterns: list[tuple[str, str, str, str]]
) -> tuple[str, str, str] | None:
    for pattern, label, claim_type, severity in patterns:
        if re.search(pattern, sentence, re.IGNORECASE):
            return label, claim_type, severity
    return None


def _claim_issue(sentence: str, label: str, claim_type: str, severity: str) -> HookIssue:
    excerpt = sentence[:180] + ("..." if len(sentence) > 180 else "")
    return HookIssue(
        hook_id="C14",
        severity=severity,
        section="manuscript",
        message=(
            f"Strong {claim_type} claim '{label}' lacks visible evidence backing "
            f"(citation, source-material, table/figure, or data artifact): {excerpt}"
        ),
    )


class ClaimEvidenceHooksMixin:
    """C14: strong claims need visible evidence."""

    _STRONG_CLAIM_PATTERNS = _STRONG_CLAIM_PATTERNS

    def _sentence_has_evidence_marker(self, sentence: str) -> bool:
        """Return whether a strong claim sentence cites evidence or data context."""
        if extract_reference_wikilink_keys(sentence):
            return True
        return any(re.search(pattern, sentence, re.IGNORECASE) for pattern in _EVIDENCE_PATTERNS)

    def check_claim_evidence_alignment(self, content: str) -> HookResult:
        """Hook C14: strong scientific claims must be backed by visible evidence.

        This is intentionally separate from A3 anti-AI style checks. Terms such
        as "fundamentally changes" are not always AI writing, but they are
        strong scientific claims and should cite literature, tables/figures,
        source-material context, or data artifacts.
        """
        issues: list[HookIssue] = []
        sentences = re.split(r"(?<=[.!?])\s+", content)
        flagged = 0
        by_type: dict[str, int] = {}

        for sentence in sentences:
            stripped = sentence.strip()
            if not stripped:
                continue
            claim = _match_strong_claim(stripped, self._STRONG_CLAIM_PATTERNS)
            if claim is None or self._sentence_has_evidence_marker(stripped):
                continue

            label, claim_type, severity = claim
            flagged += 1
            by_type[claim_type] = by_type.get(claim_type, 0) + 1
            issues.append(_claim_issue(stripped, label, claim_type, severity))

        critical = any(issue.severity == "CRITICAL" for issue in issues)
        return HookResult(
            hook_id="C14",
            passed=not critical,
            issues=issues,
            stats={"strong_claims_without_evidence": flagged, "by_claim_type": by_type},
        )
