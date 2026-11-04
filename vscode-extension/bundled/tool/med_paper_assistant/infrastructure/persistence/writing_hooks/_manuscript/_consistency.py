"""Writing Hooks — C3 N-value consistency and C4 abbreviation first-use."""

from __future__ import annotations

import re

import structlog

from .._constants import COMMON_ABBREVIATIONS
from .._models import HookIssue, HookResult
from .._n_values import methods_n_values, n_value_issues
from .._section_tree import has_selected_ancestor

logger = structlog.get_logger()


def _find_methods_node(nodes):
    return next(
        (n for n in nodes if re.match(r"(?:materials?\s+and\s+)?methods", n.name, re.IGNORECASE)),
        None,
    )


def _unique_abbreviations(all_abbrs: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_abbrs: list[str] = []
    for abbr in all_abbrs:
        if abbr not in seen and abbr not in COMMON_ABBREVIATIONS:
            seen.add(abbr)
            unique_abbrs.append(abbr)
    return unique_abbrs


def _classify_abbreviations(
    content: str, unique_abbrs: list[str]
) -> tuple[list[str], list[str], list[HookIssue]]:
    defined: list[str] = []
    undefined: list[str] = []
    issues: list[HookIssue] = []

    for abbr in unique_abbrs:
        first_pos = content.find(abbr)
        if first_pos == -1:
            continue

        definition_pattern = rf"\b[\w\s]{{3,}}\({re.escape(abbr)}\)"
        context_start = max(0, first_pos - 200)
        context_end = min(len(content), first_pos + len(abbr) + 50)
        context = content[context_start:context_end]

        if re.search(definition_pattern, context):
            defined.append(abbr)
        else:
            undefined.append(abbr)
            issues.append(
                HookIssue(
                    hook_id="C4",
                    severity="WARNING",
                    section="manuscript",
                    message=f"Abbreviation '{abbr}' used without definition at first occurrence",
                    suggestion=f"Add 'Full Name ({abbr})' at first use",
                )
            )
    return defined, undefined, issues


class ConsistencyHooksMixin:
    """C3 / C4: cross-section consistency checks."""

    # ── Hook C3: N-value Cross-Section Consistency ─────────────────

    def check_n_value_consistency(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook C3: Verify N-values (sample sizes) are consistent across sections.

        Methods section is the source of truth. Any N-value appearing in
        other sections that differs from Methods is flagged.
        """
        issues: list[HookIssue] = []
        nodes = self._section_nodes(content)

        methods_node = _find_methods_node(nodes)

        if methods_node is None:
            return HookResult(
                hook_id="C3",
                passed=True,
                stats={"note": "No Methods section found, skipping N-value check"},
            )

        all_methods_values = methods_n_values(methods_node.full_text)

        if not all_methods_values:
            return HookResult(
                hook_id="C3",
                passed=True,
                stats={"note": "No N-values found in Methods"},
            )

        sections_checked = 0
        for node in nodes:
            if node.index == methods_node.index or has_selected_ancestor(
                node, nodes, {methods_node.index}
            ):
                continue
            sections_checked += 1
            issues.extend(n_value_issues(node.name, node.own_text, all_methods_values))

        inconsistencies = sum(1 for i in issues if i.severity == "CRITICAL")
        passed = inconsistencies == 0
        stats = {
            "methods_n_values": sorted(all_methods_values),
            "sections_checked": sections_checked,
            "inconsistencies": inconsistencies,
        }

        logger.info("Hook C3 complete", passed=passed, inconsistencies=inconsistencies)
        return HookResult(hook_id="C3", passed=passed, issues=issues, stats=stats)

    # ── Hook C4: Abbreviation First-Use Definition ─────────────────

    def check_abbreviation_first_use(
        self,
        content: str,
    ) -> HookResult:
        """
        Hook C4: Verify abbreviations are defined at first use.

        Scans for uppercase abbreviations (2+ letters) and checks that each
        is defined with its full form before or at first occurrence.
        Common medical/statistical abbreviations are excluded.
        """
        all_abbrs = re.findall(r"\b([A-Z]{2,})\b", content)
        if not all_abbrs:
            return HookResult(
                hook_id="C4",
                passed=True,
                stats={"abbreviations_found": 0},
            )

        unique_abbrs = _unique_abbreviations(all_abbrs)
        defined, undefined, issues = _classify_abbreviations(content, unique_abbrs)

        passed = len(issues) == 0
        stats = {
            "abbreviations_found": len(unique_abbrs),
            "defined_count": len(defined),
            "undefined_count": len(undefined),
            "undefined": undefined[:10],
        }

        logger.info("Hook C4 complete", passed=passed, undefined=len(undefined))
        return HookResult(hook_id="C4", passed=passed, issues=issues, stats=stats)
