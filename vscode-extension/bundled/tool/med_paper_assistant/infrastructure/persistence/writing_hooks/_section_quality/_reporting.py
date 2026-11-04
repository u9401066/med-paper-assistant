"""Writing Hooks — B14 ethical/registration statements and B16 effect-size reporting."""

from __future__ import annotations

import re
from typing import Any

from .._models import HookIssue, HookResult
from .._section_tree import first_section_text

_ETHICS_MARKERS = [
    r"\b(?:irb|institutional\s+review\s+board)\b",
    r"\bethics\s+committee\b",
    r"\bethical\s+(?:approval|clearance|review)\b",
    r"\bapproved\s+by\b.*\b(?:committee|board|ethics)\b",
    r"\b(?:protocol|study)\s+was\s+approved\b",
    r"\bhuman\s+(?:subjects?|research)\s+(?:committee|protection)\b",
    r"\bdeclaration\s+of\s+helsinki\b",
]

_CONSENT_MARKERS = [
    r"\binformed\s+consent\b",
    r"\bwritten\s+consent\b",
    r"\bconsent\s+was\s+obtained\b",
    r"\bconsent\s+(?:form|process|procedure)\b",
    r"\bwaiver\s+of\s+(?:informed\s+)?consent\b",
    r"\bexempt(?:ed|ion)?\b.*\bconsent\b",
]

_INTERVENTION_MARKERS = [
    r"\brandom(?:ized|ised|ization|isation)\b",
    r"\bclinical\s+trial\b",
    r"\bintervention(?:al)?\b",
    r"\bplacebo\b",
    r"\btreatment\s+(?:arm|group)\b",
    r"\bcontrol\s+(?:arm|group)\b",
]

_REGISTRATION_MARKERS = [
    r"\b(?:NCT\d{8}|ISRCTN\d+|UMIN\d+|ACTRN\d+|ChiCTR\d+)\b",
    r"\b(?:clinicaltrials\.gov|trial\s+regist(?:ry|ration|ered))\b",
    r"\bregistered\s+(?:at|with|in)\b",
    r"\bregistration\s+(?:number|no\.?|#)\b",
]

_EFFECT_SIZE_PATTERNS = [
    r"\b(?:odds\s+ratio|OR)\s*[=:]\s*[\d.]+\b",
    r"\b(?:hazard\s+ratio|HR)\s*[=:]\s*[\d.]+\b",
    r"\b(?:relative\s+risk|risk\s+ratio|RR)\s*[=:]\s*[\d.]+\b",
    r"\b(?:mean\s+difference|MD)\s*[=:]\s*[\d.]+\b",
    r"\b(?:Cohen'?s?\s+d|effect\s+size)\s*[=:]\s*[\d.]+\b",
    r"\br²?\s*=\s*[\d.]+\b",
    r"\b(?:η²|eta\s*squared)\s*=\s*[\d.]+\b",
    r"\b(?:NNT|number\s+needed\s+to\s+treat)\s*[=:]\s*[\d.]+\b",
    r"\b(?:AUC|area\s+under)\s*[=:]\s*[\d.]+\b",
]


def _ethics_issues(content_lower: str, stats: dict[str, Any]) -> list[HookIssue]:
    has_ethics = any(re.search(p, content_lower) for p in _ETHICS_MARKERS)
    stats["has_ethics_approval"] = has_ethics
    if has_ethics:
        return []
    return [
        HookIssue(
            hook_id="B14",
            severity="CRITICAL",
            section="Methods",
            message="No ethical approval statement found",
            suggestion="Add: 'This study was approved by the Institutional Review Board of [institution] (approval no. XXX)'",
        )
    ]


def _consent_issues(content_lower: str, stats: dict[str, Any]) -> list[HookIssue]:
    has_consent = any(re.search(p, content_lower) for p in _CONSENT_MARKERS)
    stats["has_informed_consent"] = has_consent
    if has_consent:
        return []
    return [
        HookIssue(
            hook_id="B14",
            severity="WARNING",
            section="Methods",
            message="No informed consent statement found",
            suggestion="Add: 'Written informed consent was obtained from all participants' or 'The requirement for informed consent was waived due to...'",
        )
    ]


def _registration_issues(content_lower: str, stats: dict[str, Any]) -> list[HookIssue]:
    # Trial registration is only required for interventional studies
    is_interventional = any(re.search(p, content_lower) for p in _INTERVENTION_MARKERS)
    if not is_interventional:
        return []
    has_registration = any(re.search(p, content_lower) for p in _REGISTRATION_MARKERS)
    stats["has_registration"] = has_registration
    stats["is_interventional"] = True
    if has_registration:
        return []
    return [
        HookIssue(
            hook_id="B14",
            severity="CRITICAL",
            section="Methods",
            message="Interventional study detected but no trial registration found",
            suggestion="Add trial registration number (e.g., NCT12345678) and registry name",
        )
    ]


def _p_value_issues(results_text: str, stats: dict[str, Any]) -> tuple[int, list[HookIssue]]:
    issues: list[HookIssue] = []
    p_values = re.findall(r"p\s*[<=>\u2264\u2265]\s*[\d.]+", results_text, re.IGNORECASE)
    stats["p_value_count"] = len(p_values)

    # Check for "p = 0.000"
    p_zero = re.findall(r"p\s*=\s*0\.000\b", results_text, re.IGNORECASE)
    if p_zero:
        issues.append(
            HookIssue(
                hook_id="B16",
                severity="CRITICAL",
                section="Results",
                message=f"Found 'p = 0.000' ({len(p_zero)} occurrence(s)). This is statistically incorrect.",
                suggestion="Use 'p < 0.001' instead of 'p = 0.000'",
            )
        )

    # Check for vague p-values
    vague_p = re.findall(r"p\s*<\s*0\.05\b", results_text, re.IGNORECASE)
    exact_p = re.findall(r"p\s*=\s*0\.\d+", results_text, re.IGNORECASE)
    stats["exact_p_count"] = len(exact_p)
    stats["vague_p_count"] = len(vague_p)

    if vague_p and not exact_p:
        issues.append(
            HookIssue(
                hook_id="B16",
                severity="WARNING",
                section="Results",
                message="Only vague p-values (p < 0.05) with no exact p-values reported",
                suggestion="Report exact p-values (e.g., p = 0.032) alongside threshold comparisons",
            )
        )
    return len(p_values), issues


def _effect_size_issues(
    results_text: str, p_value_count: int, stats: dict[str, Any]
) -> list[HookIssue]:
    issues: list[HookIssue] = []
    effect_sizes_found = sum(
        len(re.findall(p, results_text, re.IGNORECASE)) for p in _EFFECT_SIZE_PATTERNS
    )
    stats["effect_size_count"] = effect_sizes_found

    # Check for CI alongside effect sizes
    ci_patterns = re.findall(
        r"\b(?:95%?\s*CI|confidence\s+interval)\s*[=:,]?\s*[\[(]?\s*[\d.]+\s*[-–]\s*[\d.]+",
        results_text,
        re.IGNORECASE,
    )
    stats["ci_count"] = len(ci_patterns)

    if p_value_count >= 3 and effect_sizes_found == 0:
        issues.append(
            HookIssue(
                hook_id="B16",
                severity="WARNING",
                section="Results",
                message=f"Found {p_value_count} p-values but no effect size measures",
                suggestion="Report effect sizes (OR, HR, RR, Cohen's d, etc.) alongside p-values. Modern standards require both.",
            )
        )

    if effect_sizes_found > 0 and len(ci_patterns) == 0:
        issues.append(
            HookIssue(
                hook_id="B16",
                severity="WARNING",
                section="Results",
                message=f"Found {effect_sizes_found} effect size(s) but no confidence intervals",
                suggestion="Report 95% CI alongside all effect sizes (e.g., OR = 2.3, 95% CI 1.2-4.5)",
            )
        )
    return issues


class ReportingHooksMixin:
    """B14 / B16: ethics statements and statistical reporting completeness."""

    def check_ethical_statements(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook B14: Verify presence of ethical approval and trial registration.
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {}

        content_lower = content.lower()

        issues.extend(_ethics_issues(content_lower, stats))
        issues.extend(_consent_issues(content_lower, stats))
        issues.extend(_registration_issues(content_lower, stats))

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B14", passed=passed, issues=issues, stats=stats)

    def check_effect_size_reporting(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook B16: Verify statistical reporting completeness.

        Modern standards require effect sizes, CI, exact p-values.
        No "p = 0.000" (should be p < 0.001).
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {}

        sections = self._parse_sections_full(content)
        results_text = first_section_text(sections, "result")

        if not results_text:
            return HookResult(hook_id="B16", passed=True, issues=issues, stats=stats)

        p_value_count, p_issues = _p_value_issues(results_text, stats)
        issues.extend(p_issues)
        issues.extend(_effect_size_issues(results_text, p_value_count, stats))

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="B16", passed=passed, issues=issues, stats=stats)
