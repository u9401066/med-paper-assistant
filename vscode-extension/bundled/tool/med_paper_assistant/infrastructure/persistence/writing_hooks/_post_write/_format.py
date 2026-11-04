"""Writing Hooks — A4 wikilink format and A5 language consistency."""

from __future__ import annotations

import re

import structlog

from .._constants import AMER_VS_BRIT, BRIT_VS_AMER
from .._models import HookIssue, HookResult
from .._section_tree import citation_key_from_target

logger = structlog.get_logger()


def _malformed_wikilink_issue(wl: str, section: str) -> HookIssue:
    if re.match(r"^\d{7,8}$", wl):
        issue_type = "PMID-only (missing author prefix)"
        severity = "WARNING"
    elif re.match(r"^PMID:\s*\d+$", wl, re.IGNORECASE):
        issue_type = "PMID: prefix format"
        severity = "WARNING"
    else:
        issue_type = "non-standard format"
        severity = "WARNING"

    return HookIssue(
        hook_id="A4",
        severity=severity,
        section=section,
        message=f"Wikilink [[{wl}]] has {issue_type}",
        suggestion=f"Use format [[author2024_12345678]] for '{wl}'",
    )


def _find_non_preferred_words(content: str, target_dict: dict[str, str]) -> dict[str, list[int]]:
    found_words: dict[str, list[int]] = {}

    lines = content.split("\n")
    in_code_block = False
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block or stripped.startswith("#") or stripped.startswith("[["):
            continue
        line = re.sub(r"\[\[[^\]]*\]\]", "", line)
        words = re.findall(r"\b[a-zA-Z]+\b", line.lower())
        for word in words:
            if word in target_dict:
                found_words.setdefault(word, []).append(line_num)
    return found_words


def _spelling_issues(
    found_words: dict[str, list[int]],
    target_dict: dict[str, str],
    variant_found: str,
    variant_preferred: str,
    section: str,
) -> list[HookIssue]:
    issues: list[HookIssue] = []
    for word, line_nums in sorted(found_words.items()):
        replacement = target_dict[word]
        issues.append(
            HookIssue(
                hook_id="A5",
                severity="WARNING",
                section=section,
                message=f"{variant_found} spelling '{word}' found ({len(line_nums)} occurrence(s))",
                location=f"lines: {', '.join(str(n) for n in line_nums[:5])}{'...' if len(line_nums) > 5 else ''}",
                suggestion=f"Replace with {variant_preferred} spelling '{replacement}'",
            )
        )
    return issues


def _variant_setup(prefer: str) -> tuple[dict[str, str], str, str] | None:
    if prefer == "american":
        return BRIT_VS_AMER, "British", "American"
    if prefer == "british":
        return AMER_VS_BRIT, "American", "British"
    return None


class FormatHooksMixin:
    """A4 / A5: wikilink format and American/British spelling consistency."""

    def check_wikilink_format(
        self,
        content: str,
        section: str = "manuscript",
    ) -> HookResult:
        """
        Hook A4: Validate wikilink format in draft text.

        Checks that all [[wikilinks]] follow the correct format:
        [[author2024_12345678]] (lowercase author + year + underscore + PMID).
        """
        issues: list[HookIssue] = []

        all_wikilinks = re.findall(r"\[\[([^\]]+)\]\]", content)
        if not all_wikilinks:
            return HookResult(
                hook_id="A4",
                passed=True,
                stats={"total_wikilinks": 0, "valid_count": 0, "issue_count": 0},
            )

        valid_count = 0

        for wl in all_wikilinks:
            if citation_key_from_target(wl) is not None:
                valid_count += 1
            else:
                issues.append(_malformed_wikilink_issue(wl, section))

        passed = len(issues) == 0
        stats = {
            "total_wikilinks": len(all_wikilinks),
            "valid_count": valid_count,
            "issue_count": len(issues),
        }

        logger.info("Hook A4 complete", passed=passed, total=len(all_wikilinks), valid=valid_count)
        return HookResult(hook_id="A4", passed=passed, issues=issues, stats=stats)

    def check_language_consistency(
        self,
        content: str,
        prefer: str = "american",
        section: str = "manuscript",
    ) -> HookResult:
        """
        Hook A5: Detect British vs American English mixing.

        Scans the draft for words that belong to the *non-preferred* variant.
        A manuscript should use one variant consistently.

        Args:
            content: Full text or section text to check.
            prefer: "american" or "british" — the expected variant.
            section: Section name for issue reporting.

        Returns:
            HookResult with issues listing each non-preferred word found.
        """
        prefer = self._get_language_preference(prefer)

        variants = _variant_setup(prefer)
        if variants is None:
            return HookResult(
                hook_id="A5", passed=True, stats={"error": f"Unknown preference: {prefer}"}
            )
        target_dict, variant_found, variant_preferred = variants

        found_words = _find_non_preferred_words(content, target_dict)
        issues = _spelling_issues(
            found_words, target_dict, variant_found, variant_preferred, section
        )

        passed = len(issues) == 0
        stats = {
            "preferred_variant": prefer,
            "non_preferred_words_found": len(found_words),
            "total_occurrences": sum(len(v) for v in found_words.values()),
        }

        logger.info(
            "Hook A5 complete",
            passed=passed,
            non_preferred_count=stats["non_preferred_words_found"],
            prefer=prefer,
        )
        return HookResult(hook_id="A5", passed=passed, issues=issues, stats=stats)
