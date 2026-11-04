"""Writing Hooks — A3 anti-AI phrase detection."""

from __future__ import annotations

import re

import structlog

from .._constants import ANTI_AI_PARAGRAPH_START_ONLY, ANTI_AI_PHRASES
from .._models import HookIssue, HookResult

logger = structlog.get_logger()


def _count_phrases(content: str) -> tuple[dict[str, int], int]:
    content_lower = content.lower()
    phrase_counts: dict[str, int] = {}
    total_matches = 0

    for phrase in ANTI_AI_PHRASES:
        count = len(re.findall(rf"\b{re.escape(phrase)}\b", content_lower))
        if count > 0:
            phrase_counts[phrase] = count
            total_matches += count

    for phrase in ANTI_AI_PARAGRAPH_START_ONLY:
        count = len(re.findall(rf"(?:^|\n\n)\s*{re.escape(phrase)}\b", content, re.IGNORECASE))
        if count > 0:
            phrase_counts[f"{phrase} (paragraph start)"] = count
            total_matches += count

    return phrase_counts, total_matches


class AntiAiPhraseHooksMixin:
    """A3: AI-characteristic phrase detection."""

    def check_anti_ai_patterns(
        self,
        content: str,
        section: str = "manuscript",
        warn_threshold: int = 1,
        critical_threshold: int = 3,
    ) -> HookResult:
        """
        Hook A3: Detect AI-characteristic phrasing.

        Scans for forbidden phrases from the unified ANTI_AI_PHRASES list.
        "Furthermore" is only flagged at paragraph start.

        Args:
            content: Text to scan.
            section: Section name for reporting.
            warn_threshold: Total matches to trigger WARNING (default 1).
            critical_threshold: Total matches to trigger CRITICAL (default 3).
        """
        issues: list[HookIssue] = []
        phrase_counts, total_matches = _count_phrases(content)

        for phrase, count in phrase_counts.items():
            severity = "CRITICAL" if total_matches >= critical_threshold else "WARNING"
            issues.append(
                HookIssue(
                    hook_id="A3",
                    severity=severity,
                    section=section,
                    message=f"AI-characteristic phrase '{phrase}' found ({count}x)",
                    suggestion="Replace with specific, concrete language",
                )
            )

        passed = total_matches < warn_threshold
        stats = {
            "total_matches": total_matches,
            "unique_phrases_found": len(phrase_counts),
            "phrase_counts": phrase_counts,
        }

        logger.info("Hook A3 complete", passed=passed, total_matches=total_matches)
        return HookResult(hook_id="A3", passed=passed, issues=issues, stats=stats)
