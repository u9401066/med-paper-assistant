"""Writing Hooks — A1 word-count compliance and A2 citation density."""

from __future__ import annotations

import re
from typing import Any

import structlog

from .._models import HookIssue, HookResult

logger = structlog.get_logger()


def _word_count_severity(
    deviation_pct: float, tolerance_pct: float, critical_threshold_pct: int
) -> str | None:
    if abs(deviation_pct) > critical_threshold_pct:
        return "CRITICAL"
    if abs(deviation_pct) > tolerance_pct:
        return "WARNING"
    return None


def _word_count_issue(
    sec_name: str,
    word_count: int,
    target: int,
    deviation_pct: float,
    tolerance_pct: float,
    severity: str,
) -> HookIssue:
    direction = "over" if deviation_pct > 0 else "under"
    return HookIssue(
        hook_id="A1",
        severity=severity,
        section=sec_name,
        message=(
            f"{sec_name}: {word_count} words ({deviation_pct:+.0f}% {direction} "
            f"target {target}, tolerance ±{tolerance_pct}%)"
        ),
        suggestion=f"{'Trim' if deviation_pct > 0 else 'Expand'} the {sec_name} section",
    )


def _word_count_record(
    sec_name: str, word_count: int, target: int, deviation_pct: float
) -> dict[str, Any]:
    return {
        "section": sec_name,
        "word_count": word_count,
        "target": target,
        "deviation_pct": round(deviation_pct, 1),
    }


def _citation_density_issue(
    section_name: str, citation_count: int, word_count: int, threshold: int
) -> HookIssue:
    required = word_count / threshold
    density_per_100w = (citation_count / word_count) * 100 if word_count else 0
    return HookIssue(
        hook_id="A2",
        severity="WARNING",
        section=section_name,
        message=(
            f"{section_name}: {citation_count} citations in {word_count} words "
            f"(density {density_per_100w:.1f}/100w, need ≥1/{threshold}w = {required:.0f} citations)"
        ),
        suggestion=f"Add more citations to {section_name} (need ≥{required:.0f})",
    )


class CountHooksMixin:
    """A1 / A2: word-count and citation-density checks."""

    def check_word_count_compliance(
        self,
        content: str,
        section_name: str | None = None,
        critical_threshold_pct: int = 50,
    ) -> HookResult:
        """
        Hook A1: Check section word counts against targets.

        If section_name is provided, checks that single section.
        If None, parses content into sections and checks each.

        Args:
            content: Section text or full manuscript.
            section_name: If provided, treat content as a single section.
            critical_threshold_pct: Deviation % that triggers CRITICAL (default 50).
        """
        issues: list[HookIssue] = []
        tolerance_pct = self._get_word_tolerance_pct()

        if section_name:
            sections_to_check = {section_name: content}
        else:
            sections_to_check = self._sections_with_word_limits(content)

        checked: list[dict[str, Any]] = []

        for sec_name, sec_text in sections_to_check.items():
            target = self._get_section_word_limit(sec_name)
            if target is None:
                continue
            word_count = self._count_words(sec_text)
            deviation_pct = ((word_count - target) / target) * 100 if target > 0 else 0

            severity = _word_count_severity(deviation_pct, tolerance_pct, critical_threshold_pct)
            if severity:
                issues.append(
                    _word_count_issue(
                        sec_name, word_count, target, deviation_pct, tolerance_pct, severity
                    )
                )

            checked.append(_word_count_record(sec_name, word_count, target, deviation_pct))

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {"sections_checked": checked, "tolerance_pct": tolerance_pct}

        logger.info("Hook A1 complete", passed=passed, sections=len(checked))
        return HookResult(hook_id="A1", passed=passed, issues=issues, stats=stats)

    def check_citation_density(
        self,
        content: str,
        section_name: str = "manuscript",
    ) -> HookResult:
        """
        Hook A2: Check citation density (wikilinks per N words).

        Args:
            content: Section text.
            section_name: Section name for threshold lookup.
        """
        threshold = self._get_citation_density_threshold(section_name)
        if threshold == 0:
            return HookResult(
                hook_id="A2",
                passed=True,
                stats={"section": section_name, "threshold": 0, "skipped": True},
            )

        citation_count = len(re.findall(r"\[\[[^\]]+\]\]", content))
        word_count = self._count_words(content)

        if word_count == 0:
            return HookResult(
                hook_id="A2",
                passed=True,
                stats={"section": section_name, "word_count": 0},
            )

        required = word_count / threshold
        density_per_100w = (citation_count / word_count) * 100 if word_count else 0

        issues: list[HookIssue] = []
        if citation_count < required:
            issues.append(
                _citation_density_issue(section_name, citation_count, word_count, threshold)
            )
        passed = len(issues) == 0
        stats = {
            "section": section_name,
            "citation_count": citation_count,
            "word_count": word_count,
            "density_per_100w": round(density_per_100w, 2),
            "threshold_per_nw": threshold,
        }

        logger.info("Hook A2 complete", passed=passed, density=density_per_100w)
        return HookResult(hook_id="A2", passed=passed, issues=issues, stats=stats)
