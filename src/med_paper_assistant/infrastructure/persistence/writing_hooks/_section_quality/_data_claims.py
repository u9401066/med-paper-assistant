"""Writing Hooks — B8 Data-Claim Alignment (Results ↔ Methods)."""

from __future__ import annotations

import re

import structlog

from .._models import HookIssue, HookResult

logger = structlog.get_logger()

# Statistical test patterns (test name → regex)
_STAT_TESTS = {
    "t-test": r"\bt[\s-]*test\b",
    "chi-square": r"chi[\s-]*square|χ2|χ²",
    "Fisher exact": r"fisher(?:'s)?\s+exact",
    "Mann-Whitney": r"mann[\s-]*whitney",
    "Wilcoxon": r"wilcoxon",
    "ANOVA": r"\banova\b",
    "Kruskal-Wallis": r"kruskal[\s-]*wallis",
    "logistic regression": r"logistic\s+regression",
    "linear regression": r"linear\s+regression",
    "Cox regression": r"cox\s+(?:proportional\s+hazards?|regression)",
    "Kaplan-Meier": r"kaplan[\s-]*meier",
    "log-rank": r"log[\s-]*rank",
    "McNemar": r"mcnemar",
    "Spearman": r"spearman",
    "Pearson": r"pearson",
    "ANCOVA": r"\bancova\b",
    "mixed model": r"mixed[\s-]*(?:effect|model)",
    "GEE": r"\bgee\b|generalized?\s+estim",
    "Bland-Altman": r"bland[\s-]*altman",
    "ROC": r"\broc\b|receiver\s+operating",
    "AUC": r"\bauc\b|area\s+under\s+(?:the\s+)?curve",
    "sensitivity analysis": r"sensitivity\s+analysis",
    "propensity score": r"propensity\s+score",
    "bootstrap": r"\bbootstrap",
    "Bayesian": r"\bbayesian\b",
    "multiple comparison": r"multiple\s+comparison|bonferroni|holm|tukey|šidák|sidak",
}

_SOFTWARE_PATTERNS = {
    "SPSS": r"\bspss\b",
    "SAS": r"\bsas\b",
    "Stata": r"\bstata\b",
    "R": r"\bR\s+(?:version|software|package|v\d|\(v\d|Foundation|Core\s+Team)",
    "Python": r"\bpython\b",
    "MATLAB": r"\bmatlab\b",
    "GraphPad": r"graphpad",
    "MedCalc": r"medcalc",
}


def _undeclared_test_issues(methods_lower: str, results_lower: str) -> list[HookIssue]:
    issues: list[HookIssue] = []
    for test_name, pattern in _STAT_TESTS.items():
        in_results = bool(re.search(pattern, results_lower))
        in_methods = bool(re.search(pattern, methods_lower))
        if in_results and not in_methods:
            issues.append(
                HookIssue(
                    hook_id="B8",
                    severity="CRITICAL",
                    section="Results ↔ Methods",
                    message=f"'{test_name}' used in Results but not described in Methods",
                    suggestion=f"Add '{test_name}' description to Methods, or remove from Results",
                )
            )
    return issues


def _p_threshold_issues(methods_lower: str, results_lower: str) -> list[HookIssue]:
    issues: list[HookIssue] = []
    alpha_methods = set(
        re.findall(r"(?:significance|alpha|α)\s*(?:level)?\s*(?:of|=|:)?\s*(0\.\d+)", methods_lower)
    )
    p_thresholds_results = set(re.findall(r"p\s*[<>]\s*(0\.\d+)", results_lower))

    if alpha_methods and p_thresholds_results:
        for threshold in p_thresholds_results:
            if threshold not in alpha_methods:
                issues.append(
                    HookIssue(
                        hook_id="B8",
                        severity="WARNING",
                        section="Results ↔ Methods",
                        message=(
                            f"Results uses p-value threshold {threshold} "
                            f"but Methods declares alpha = {', '.join(sorted(alpha_methods))}"
                        ),
                        suggestion="Ensure p-value thresholds in Results match the alpha level declared in Methods",
                    )
                )
    return issues


def _ci_width_issues(methods_lower: str, results_lower: str) -> list[HookIssue]:
    issues: list[HookIssue] = []
    ci_methods = set(re.findall(r"(\d+)%\s*(?:confidence\s+interval|ci)", methods_lower))
    ci_results = set(re.findall(r"(\d+)%\s*(?:confidence\s+interval|ci)", results_lower))

    if ci_methods and ci_results:
        mismatch = ci_results - ci_methods
        for ci in mismatch:
            issues.append(
                HookIssue(
                    hook_id="B8",
                    severity="WARNING",
                    section="Results ↔ Methods",
                    message=f"Results reports {ci}% CI but Methods declares {', '.join(sorted(ci_methods))}% CI",
                    suggestion="Ensure CI percentages are consistent between Methods and Results",
                )
            )
    return issues


def _undeclared_software_issues(methods_lower: str, results_lower: str) -> list[HookIssue]:
    issues: list[HookIssue] = []
    for sw_name, pattern in _SOFTWARE_PATTERNS.items():
        in_results = bool(re.search(pattern, results_lower))
        in_methods = bool(re.search(pattern, methods_lower))
        if in_results and not in_methods:
            issues.append(
                HookIssue(
                    hook_id="B8",
                    severity="WARNING",
                    section="Results ↔ Methods",
                    message=f"Software '{sw_name}' referenced in Results but not declared in Methods",
                    suggestion=f"Add '{sw_name}' to the statistical software section of Methods",
                )
            )
    return issues


class DataClaimHooksMixin:
    """B8: Results statistics must be declared in Methods."""

    def check_data_claim_alignment(
        self,
        methods_content: str,
        results_content: str,
    ) -> HookResult:
        """
        Hook B8: Verify statistical claims in Results align with Methods.

        Checks:
        1. Statistical tests mentioned in Results must appear in Methods
        2. P-value thresholds should be consistent
        3. Outcome measures mentioned in Results should match Methods
        4. Common statistical tests in Results must be declared in Methods
        """
        methods_lower = methods_content.lower()
        results_lower = results_content.lower()

        issues: list[HookIssue] = []
        issues.extend(_undeclared_test_issues(methods_lower, results_lower))
        issues.extend(_p_threshold_issues(methods_lower, results_lower))
        issues.extend(_ci_width_issues(methods_lower, results_lower))
        issues.extend(_undeclared_software_issues(methods_lower, results_lower))

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "stat_tests_in_results": sum(
                1 for _, p in _STAT_TESTS.items() if re.search(p, results_lower)
            ),
            "stat_tests_in_methods": sum(
                1 for _, p in _STAT_TESTS.items() if re.search(p, methods_lower)
            ),
            "undeclared_tests": sum(1 for i in issues if "not described in Methods" in i.message),
        }

        logger.info(
            "Hook B8 complete",
            passed=passed,
            undeclared_tests=stats["undeclared_tests"],
        )
        return HookResult(hook_id="B8", passed=passed, issues=issues, stats=stats)
