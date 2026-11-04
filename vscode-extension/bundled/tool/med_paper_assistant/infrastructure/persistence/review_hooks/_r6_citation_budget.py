"""R6 — Citation Budget Gate."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..writing_hooks._models import HookIssue, HookResult
from ._constants import REF_BUDGET_HEADROOM


def _over_budget_issues(
    total_refs: int,
    max_refs: int,
    over_budget: int,
    trim_suggestions: list[tuple[str, str]],
) -> list[HookIssue]:
    """CRITICAL over-budget issue followed by one WARNING per trim candidate."""
    issues = [
        HookIssue(
            hook_id="R6",
            severity="CRITICAL",
            section="References",
            message=f"Citation count ({total_refs}) exceeds journal limit ({max_refs}) by {over_budget}",
            suggestion=f"Remove {over_budget} lowest-priority references. Use citation_decisions.json priority field to rank.",
        )
    ]
    for ref_key, reason in trim_suggestions:
        issues.append(
            HookIssue(
                hook_id="R6",
                severity="WARNING",
                section="References",
                message=f"Trim candidate: [[{ref_key}]] — {reason}",
                suggestion=f"Remove [[{ref_key}]] from manuscript and references, or justify keeping it in citation_decisions.json",
            )
        )
    return issues


def _at_limit_issue(total_refs: int, max_refs: int) -> HookIssue:
    return HookIssue(
        hook_id="R6",
        severity="WARNING",
        section="References",
        message=f"Citation count ({total_refs}) at exact limit ({max_refs}) — no room for additional references",
        suggestion="Consider whether all references are essential; any new addition will require removing another",
    )


def _undocumented_refs_issue(undocumented_count: int) -> HookIssue:
    return HookIssue(
        hook_id="R6",
        severity="WARNING",
        section="References",
        message=f"{undocumented_count} references lack citation_decisions.json entry — cannot prioritise without justification",
        suggestion="Add priority (1-5) and justification to citation_decisions.json for all references to enable informed trimming",
    )


def _unconfigured_budget_result(total_refs: int) -> HookResult:
    return HookResult(
        hook_id="R6",
        passed=True,
        issues=[],
        stats={"total_refs": total_refs, "max_refs": "not_configured", "over_budget": 0},
    )


class CitationBudgetMixin:
    """R6: reference count must stay within the journal limit."""

    _project_dir: Path
    _journal_profile: dict[str, Any] | None

    def _get_max_references(self) -> int | None:
        """Get max references from journal profile (paper-type-specific > global)."""
        if not self._journal_profile:
            return None
        refs_cfg = self._journal_profile.get("references", {})
        paper_type = self._journal_profile.get("paper", {}).get("type", "")
        type_limits = refs_cfg.get("reference_limits", {})
        if paper_type and paper_type in type_limits:
            return int(type_limits[paper_type])
        max_refs = refs_cfg.get("max_references")
        return int(max_refs) if max_refs is not None else None

    def _load_citation_decisions(self) -> dict[str, Any]:
        decisions_path = self._project_dir / "citation_decisions.json"
        decisions: dict[str, Any] = {}
        if decisions_path.is_file():
            try:
                decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return decisions

    def check_citation_budget(self, manuscript_content: str) -> HookResult:
        """
        R6: Enforce reference count ≤ journal limit after review round.

        Review often adds supporting references. This hook:
        1. Counts unique wikilink citations in manuscript
        2. Compares against journal-profile max_references
        3. If over budget: CRITICAL — must prioritise and trim
        4. Checks citation_decisions.json for priority/justification
        5. Suggests which refs to remove (lowest priority, fewest citations)
        """
        issues: list[HookIssue] = []

        # Count unique citations in manuscript
        wikilinks = set(re.findall(r"\[\[(\w+\d{4}_\d+)\]\]", manuscript_content))
        total_refs = len(wikilinks)

        max_refs = self._get_max_references()
        if max_refs is None:
            # No limit configured — just report count
            return _unconfigured_budget_result(total_refs)

        over_budget = total_refs - max_refs

        if over_budget > REF_BUDGET_HEADROOM:
            # Provide specific trim suggestions based on citation_decisions.json
            trim_suggestions = self._suggest_refs_to_trim(
                wikilinks,
                manuscript_content,
                over_budget,
            )
            issues.extend(_over_budget_issues(total_refs, max_refs, over_budget, trim_suggestions))
        elif over_budget == 0:
            issues.append(_at_limit_issue(total_refs, max_refs))

        # Check for refs without citation_decisions.json entry
        decisions = self._load_citation_decisions()
        undocumented_refs = [ref for ref in wikilinks if ref not in decisions]
        if undocumented_refs and over_budget > 0:
            issues.append(_undocumented_refs_issue(len(undocumented_refs)))

        passed = over_budget <= REF_BUDGET_HEADROOM
        stats = {
            "total_refs": total_refs,
            "max_refs": max_refs,
            "over_budget": max(0, over_budget),
            "undocumented_refs": len(undocumented_refs),
            "budget_utilization_pct": round(total_refs / max_refs * 100, 1) if max_refs > 0 else 0,
        }
        return HookResult(hook_id="R6", passed=passed, issues=issues, stats=stats)

    def _suggest_refs_to_trim(
        self,
        wikilinks: set[str],
        manuscript_content: str,
        over_budget: int,
    ) -> list[tuple[str, str]]:
        """
        Suggest references to remove based on priority and citation frequency.

        Priority order for trimming (lowest priority first):
        1. No citation_decisions.json entry (unknown importance)
        2. Lowest priority score in citation_decisions.json
        3. Fewest in-text citations (cited only once)
        4. Most recently added (not in original concept)
        """
        # Count in-text citation frequency
        ref_frequency: dict[str, int] = {}
        for ref in wikilinks:
            ref_frequency[ref] = len(re.findall(re.escape(f"[[{ref}]]"), manuscript_content))

        decisions = self._load_citation_decisions()
        scored = self._score_refs_for_trim(wikilinks, decisions, ref_frequency)

        # Sort by score ascending (lowest score = first to trim)
        scored.sort(key=lambda x: x[1])

        # Return top N suggestions
        return [(ref, reason) for ref, _, reason in scored[:over_budget]]

    @staticmethod
    def _score_refs_for_trim(
        wikilinks: set[str],
        decisions: dict[str, Any],
        ref_frequency: dict[str, int],
    ) -> list[tuple[str, float, str]]:
        """Score refs: lower score = higher trim priority."""
        scored: list[tuple[str, float, str]] = []
        for ref in wikilinks:
            decision = decisions.get(ref, {})
            priority = decision.get("priority", 0)  # 0 = undocumented
            freq = ref_frequency.get(ref, 0)
            # Score: priority * 10 + freq (higher = harder to trim)
            score = priority * 10 + freq
            reason_parts = []
            if priority == 0:
                reason_parts.append("no priority in citation_decisions.json")
            else:
                reason_parts.append(f"priority={priority}")
            reason_parts.append(f"cited {freq}x")
            scored.append((ref, score, ", ".join(reason_parts)))
        return scored
