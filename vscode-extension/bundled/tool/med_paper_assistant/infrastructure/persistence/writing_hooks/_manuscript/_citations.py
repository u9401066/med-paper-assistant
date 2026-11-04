"""Writing Hooks — C11 citation distribution and C12 citation relevance audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from med_paper_assistant.domain.services.citation_converter import extract_citation_keys

from .._models import HookIssue, HookResult
from .._section_tree import extract_wikilink_citation_keys

logger = structlog.get_logger()

_CANONICAL_SECTIONS = ["Introduction", "Methods", "Results", "Discussion"]


def _section_citation_counts(sections: dict[str, str]) -> dict[str, int]:
    section_citations: dict[str, int] = {}
    for canon in _CANONICAL_SECTIONS:
        for name, text in sections.items():
            if name.lower().startswith(canon.lower()):
                section_citations[canon] = len(extract_citation_keys(text))
                break
    return section_citations


def _coverage_issues(section_citations: dict[str, int]) -> list[HookIssue]:
    issues: list[HookIssue] = []
    if section_citations.get("Discussion", 0) == 0 and "Discussion" in section_citations:
        issues.append(
            HookIssue(
                hook_id="C11",
                severity="CRITICAL",
                section="Discussion",
                message="Discussion has 0 citations — must compare findings with prior literature",
                suggestion="Add citations comparing your results with published studies: 'Consistent with [[ref]], ...' or 'In contrast to [[ref]], ...'",
            )
        )
    if section_citations.get("Methods", 0) == 0 and "Methods" in section_citations:
        issues.append(
            HookIssue(
                hook_id="C11",
                severity="WARNING",
                section="Methods",
                message="Methods has 0 citations — should cite methodology sources",
                suggestion="Cite statistical methods, validated instruments, prior protocols, or classification systems used",
            )
        )
    return issues


def _balance_issues(section_citations: dict[str, int], total_citations: int) -> list[HookIssue]:
    issues: list[HookIssue] = []
    for sec_name, count in section_citations.items():
        pct = (count / total_citations) * 100
        if pct > 70 and total_citations >= 5:
            issues.append(
                HookIssue(
                    hook_id="C11",
                    severity="WARNING",
                    section=sec_name,
                    message=f"{sec_name} holds {pct:.0f}% of all citations ({count}/{total_citations}) — distribution imbalance",
                    suggestion=f"Redistribute citations: ensure other sections also cite relevant literature (current: {section_citations})",
                )
            )

    results_count = section_citations.get("Results", 0)
    if results_count > 0 and total_citations > 0:
        results_pct = (results_count / total_citations) * 100
        if results_pct > 50:
            issues.append(
                HookIssue(
                    hook_id="C11",
                    severity="INFO",
                    section="Results",
                    message=f"Results has {results_pct:.0f}% of citations — typically Results should focus on your data, not prior literature",
                    suggestion="Consider moving literature comparisons to Discussion",
                )
            )
    return issues


def _map_refs_to_sections(sections: dict[str, str]) -> dict[str, set[str]]:
    ref_to_sections: dict[str, set[str]] = {}
    for sec_name, sec_text in sections.items():
        for ref_key in extract_wikilink_citation_keys(sec_text):
            ref_to_sections.setdefault(ref_key, set()).add(sec_name)
    return ref_to_sections


def _load_decisions(decisions_path: Path) -> dict[str, Any]:
    if not decisions_path.is_file():
        return {}
    try:
        loaded: dict[str, Any] = json.loads(decisions_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return loaded


def _load_usage(ref_dir: Path) -> tuple[bool, list[str]]:
    """Return (has_analysis, usage_sections) from analysis.json, else metadata.json."""
    analysis_path = ref_dir / "analysis.json"
    meta_path = ref_dir / "metadata.json"
    has_analysis = False
    usage_sections: list[str] = []
    if analysis_path.is_file():
        try:
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            has_analysis = True
            usage_sections = analysis.get("usage_sections", [])
        except (json.JSONDecodeError, OSError):
            pass
    elif meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            has_analysis = meta.get("analysis_completed", False)
            usage_sections = meta.get("usage_sections", [])
        except (json.JSONDecodeError, OSError):
            pass
    return has_analysis, usage_sections


def _usage_mismatch_issues(
    ref_key: str, cited_sections: set[str], usage_sections: list[str]
) -> list[HookIssue]:
    issues: list[HookIssue] = []
    for cited_sec in cited_sections:
        normalized_usage = [s.lower() for s in usage_sections]
        if cited_sec.lower() not in normalized_usage:
            issues.append(
                HookIssue(
                    hook_id="C12",
                    severity="WARNING",
                    section=cited_sec,
                    message=f"[[{ref_key}]] cited in {cited_sec} but usage_sections={usage_sections} — section not in planned usage",
                    location=ref_key,
                    suggestion=f"Update analysis for [[{ref_key}]] to include '{cited_sec}' in usage_sections, or reconsider if this citation belongs here",
                )
            )
    return issues


def _missing_decision_issue(ref_key: str, cited_sections: set[str]) -> HookIssue:
    return HookIssue(
        hook_id="C12",
        severity="WARNING",
        section="References",
        message=f"[[{ref_key}]] has no citation decision record — why was this reference chosen?",
        location=ref_key,
        suggestion=(
            f"Add decision record to citation_decisions.json: "
            f'{{"justification": "...", "cited_sections": {list(cited_sections)}, "decision_date": "..."}}'
        ),
    )


def _audit_citations(
    ref_to_sections: dict[str, set[str]],
    refs_dir: Path,
    decisions: dict[str, Any],
    issues: list[HookIssue],
) -> tuple[int, int, int]:
    has_justification = 0
    missing_justification = 0
    section_mismatch = 0

    for ref_key, cited_sections in sorted(ref_to_sections.items()):
        has_analysis, usage_sections = _load_usage(refs_dir / ref_key)

        if has_analysis and usage_sections:
            mismatches = _usage_mismatch_issues(ref_key, cited_sections, usage_sections)
            section_mismatch += len(mismatches)
            issues.extend(mismatches)

        ref_decision = decisions.get(ref_key, {})
        if ref_decision and ref_decision.get("justification"):
            has_justification += 1
        else:
            missing_justification += 1
            issues.append(_missing_decision_issue(ref_key, cited_sections))

    return has_justification, missing_justification, section_mismatch


class CitationHooksMixin:
    """C11 / C12: citation distribution and justification."""

    # ── Hook C11: Citation Distribution Across Sections ────────────

    def check_citation_distribution(
        self,
        content: str,
    ) -> HookResult:
        """
        C11: Verify citations are distributed across sections, not clustered.
        """
        sections = self._parse_sections_full(content)
        if not sections:
            return HookResult(
                hook_id="C11",
                passed=True,
                stats={"note": "No sections parsed"},
            )

        section_citations = _section_citation_counts(sections)
        total_citations = sum(section_citations.values())

        if total_citations == 0:
            return HookResult(
                hook_id="C11",
                passed=True,
                stats={
                    "note": "No citations found in manuscript",
                    "section_citations": section_citations,
                },
            )

        issues = _coverage_issues(section_citations) + _balance_issues(
            section_citations, total_citations
        )

        passed = not any(i.severity == "CRITICAL" for i in issues)
        stats = {
            "total_citations": total_citations,
            "section_citations": section_citations,
            "distribution_pct": {
                k: round((v / total_citations) * 100, 1) if total_citations > 0 else 0
                for k, v in section_citations.items()
            },
        }

        logger.info(
            "Hook C11 (Citation Distribution) complete",
            passed=passed,
            total=total_citations,
            distribution=section_citations,
        )
        return HookResult(hook_id="C11", passed=passed, issues=issues, stats=stats)

    # ── Hook C12: Citation Relevance Audit ─────────────────────────

    def check_citation_relevance_audit(
        self,
        content: str,
    ) -> HookResult:
        """C12: Verify citations have recorded usage justification."""
        issues: list[HookIssue] = []

        ref_to_sections = _map_refs_to_sections(self._parse_sections(content))

        if not ref_to_sections:
            return HookResult(
                hook_id="C12",
                passed=True,
                stats={"note": "No wikilink citations found"},
            )

        decisions_path = self._project_dir / "citation_decisions.json"
        has_justification, missing_justification, section_mismatch = _audit_citations(
            ref_to_sections,
            self._project_dir / "references",
            _load_decisions(decisions_path),
            issues,
        )

        total = has_justification + missing_justification
        passed = missing_justification == 0 and section_mismatch == 0
        stats = {
            "total_cited_refs": len(ref_to_sections),
            "has_justification": has_justification,
            "missing_justification": missing_justification,
            "section_mismatch": section_mismatch,
            "justification_pct": round(has_justification / total * 100, 1) if total > 0 else 0,
            "decisions_file_exists": decisions_path.is_file(),
        }

        logger.info(
            "Hook C12 (Citation Relevance Audit) complete",
            passed=passed,
            justified=has_justification,
            missing=missing_justification,
            mismatched=section_mismatch,
        )
        return HookResult(hook_id="C12", passed=passed, issues=issues, stats=stats)
