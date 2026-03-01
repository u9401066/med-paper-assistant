"""
Review Hooks Engine — Code-enforced quality checks for Phase 7 Autonomous Review.

R-series hooks verify that the review CONTENT is substantive, not just that
the review PROCESS was followed. Integrated into submit_review_round() as a
HARD GATE — the agent cannot submit a review round unless these pass.

Hooks:
  R1  Review Report Depth — report word count, reviewer perspectives, severity breakdown
  R2  Author Response Completeness — every issue addressed, DECLINE ratio ≤ 50%
  R3  EQUATOR Compliance Gate — equator file exists, checklist items ≥ 5
  R4  Review-Fix Traceability — ACCEPT'd issues have corresponding manuscript patches
  R5  Post-Review Anti-AI Gate — re-run A3/A3b after review edits, must PASS
  R6  Citation Budget Gate — total refs ≤ journal limit after review adds new ones;
                              if over, force prioritisation via citation_decisions.json

Architecture:
  - Standalone engine (not a WritingHooksEngine mixin)
  - Returns HookResult/HookIssue from writing_hooks._models
  - Records to HookEffectivenessTracker via the same "R1"…"R6" IDs
  - Called from submit_review_round() in pipeline_gate.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import structlog

from .writing_hooks._models import HookIssue, HookResult

logger = structlog.get_logger()

# ── Constants ──────────────────────────────────────────────────────────

# Minimum review report length (words)
MIN_REVIEW_REPORT_WORDS = 300

# Required reviewer perspectives (at least 3 of these must appear in the report)
REVIEWER_PERSPECTIVES = [
    "methodology",
    "domain",
    "statistic",
    "writing",
    "editor",
    "clinical",
    "ethical",
]
MIN_PERSPECTIVES = 3

# Severity keywords for issue parsing in review reports
SEVERITY_KEYWORDS = {
    "major": ["major", "critical", "serious", "significant"],
    "minor": ["minor", "trivial", "cosmetic", "editorial"],
    "optional": ["optional", "suggestion", "consider", "recommended"],
}

# Maximum DECLINE ratio for author responses
MAX_DECLINE_RATIO = 0.50

# Minimum checklist items in EQUATOR compliance file
MIN_EQUATOR_ITEMS = 5

# Reference budget headroom: how many refs above limit before CRITICAL
REF_BUDGET_HEADROOM = 0  # 0 = strict (no overrun allowed)


class ReviewHooksEngine:
    """
    Code-enforced review quality hooks (R1–R6).

    Usage:
        engine = ReviewHooksEngine(project_dir)
        r1 = engine.check_review_report_depth(round_num)
        r2 = engine.check_author_response_completeness(round_num)
        ...
    """

    def __init__(self, project_dir: str | Path) -> None:
        self._project_dir = Path(project_dir)
        self._audit_dir = self._project_dir / ".audit"
        self._journal_profile: dict[str, Any] | None = None
        self._load_journal_profile()

    def _load_journal_profile(self) -> None:
        """Load journal-profile.yaml if available."""
        profile_path = self._project_dir / "journal-profile.yaml"
        if profile_path.is_file():
            try:
                import yaml

                with open(profile_path, encoding="utf-8") as f:
                    self._journal_profile = yaml.safe_load(f) or {}
            except Exception:
                logger.warning("Failed to load journal-profile.yaml")
                self._journal_profile = None

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

    # ── R1: Review Report Depth ────────────────────────────────────

    def check_review_report_depth(self, round_num: int) -> HookResult:
        """
        R1: Verify review report is substantive and multi-perspective.

        Checks:
        - Report word count ≥ MIN_REVIEW_REPORT_WORDS (300)
        - ≥ 3 reviewer perspectives mentioned
        - Issues categorised by severity (major/minor/optional)
        - At least 1 major issue identified (reviews always find something)
        """
        issues: list[HookIssue] = []
        report_path = self._audit_dir / f"review-report-{round_num}.md"

        if not report_path.is_file():
            issues.append(HookIssue(
                hook_id="R1", severity="CRITICAL", section="review",
                message=f"review-report-{round_num}.md not found",
                suggestion="Write the review report before submitting",
            ))
            return HookResult(hook_id="R1", passed=False, issues=issues)

        content = report_path.read_text(encoding="utf-8")
        words = len(content.split())

        # Word count check
        if words < MIN_REVIEW_REPORT_WORDS:
            issues.append(HookIssue(
                hook_id="R1", severity="CRITICAL", section="review",
                message=f"Review report too short: {words} words (minimum {MIN_REVIEW_REPORT_WORDS})",
                suggestion="Expand review with deeper analysis across methodology, domain, statistics, and writing quality",
            ))

        # Perspective coverage
        content_lower = content.lower()
        found_perspectives = []
        for persp in REVIEWER_PERSPECTIVES:
            if persp in content_lower:
                found_perspectives.append(persp)

        if len(found_perspectives) < MIN_PERSPECTIVES:
            issues.append(HookIssue(
                hook_id="R1", severity="CRITICAL", section="review",
                message=f"Only {len(found_perspectives)}/{MIN_PERSPECTIVES} reviewer perspectives found: {found_perspectives}",
                suggestion=f"Review must cover ≥{MIN_PERSPECTIVES} perspectives from: {REVIEWER_PERSPECTIVES}",
            ))

        # Severity breakdown — parse YAML frontmatter or headings
        major_count = self._count_severity_in_report(content, "major")
        minor_count = self._count_severity_in_report(content, "minor")

        if major_count == 0 and minor_count == 0:
            issues.append(HookIssue(
                hook_id="R1", severity="CRITICAL", section="review",
                message="No issues classified by severity — review must identify issues as major/minor/optional",
                suggestion="Add severity classification to each issue (use YAML frontmatter or section headings)",
            ))
        elif major_count == 0:
            issues.append(HookIssue(
                hook_id="R1", severity="WARNING", section="review",
                message="No major issues found — a thorough review typically identifies at least one major concern",
                suggestion="Re-examine methodology, statistical approach, or conceptual gaps for potential major issues",
            ))

        passed = all(i.severity != "CRITICAL" for i in issues)
        stats = {
            "report_words": words,
            "perspectives_found": found_perspectives,
            "perspective_count": len(found_perspectives),
            "major_issues": major_count,
            "minor_issues": minor_count,
        }
        return HookResult(hook_id="R1", passed=passed, issues=issues, stats=stats)

    # ── R2: Author Response Completeness ───────────────────────────

    def check_author_response_completeness(self, round_num: int) -> HookResult:
        """
        R2: Verify author response addresses ALL review issues.

        Checks:
        - author-response-{N}.md exists
        - Every issue has ACCEPT or DECLINE with reason
        - DECLINE ratio ≤ 50% (can't just reject everything)
        - ACCEPTED issues should have evidence or reference support
        """
        issues: list[HookIssue] = []
        response_path = self._audit_dir / f"author-response-{round_num}.md"

        if not response_path.is_file():
            issues.append(HookIssue(
                hook_id="R2", severity="CRITICAL", section="review",
                message=f"author-response-{round_num}.md not found",
                suggestion="Write the author response before submitting",
            ))
            return HookResult(hook_id="R2", passed=False, issues=issues)

        content = response_path.read_text(encoding="utf-8")

        # Count ACCEPT / DECLINE
        accept_count = len(re.findall(r"\bACCEPT\b", content, re.IGNORECASE))
        decline_count = len(re.findall(r"\bDECLINE\b", content, re.IGNORECASE))
        total_decisions = accept_count + decline_count

        if total_decisions == 0:
            issues.append(HookIssue(
                hook_id="R2", severity="CRITICAL", section="review",
                message="No ACCEPT/DECLINE decisions found in author response",
                suggestion="Each review issue must be explicitly ACCEPT'd or DECLINE'd with reasoning",
            ))
        else:
            # Cross-check with review report
            report_path = self._audit_dir / f"review-report-{round_num}.md"
            if report_path.is_file():
                report_content = report_path.read_text(encoding="utf-8")
                report_issue_count = self._count_total_issues_in_report(report_content)
                if report_issue_count > 0 and total_decisions < report_issue_count:
                    issues.append(HookIssue(
                        hook_id="R2", severity="CRITICAL", section="review",
                        message=f"Only {total_decisions}/{report_issue_count} review issues addressed in author response",
                        suggestion="Every issue in the review report must have an ACCEPT or DECLINE decision",
                    ))

            # DECLINE ratio check
            if total_decisions > 0:
                decline_ratio = decline_count / total_decisions
                if decline_ratio > MAX_DECLINE_RATIO:
                    issues.append(HookIssue(
                        hook_id="R2", severity="CRITICAL", section="review",
                        message=f"DECLINE ratio {decline_ratio:.0%} exceeds maximum {MAX_DECLINE_RATIO:.0%} ({decline_count}/{total_decisions} declined)",
                        suggestion="Re-evaluate declined issues — provide stronger justification or accept more reviewer suggestions",
                    ))

        # Check for evidence/reference support in responses
        # Look for citation wikilinks or "evidence" / "reference" mentions near ACCEPT
        accept_sections = re.findall(
            r"(?:ACCEPT|accept)[^\n]*(?:\n(?!\s*(?:ACCEPT|DECLINE|#{1,3}\s)).*){0,5}",
            content,
        )
        accepts_with_evidence = 0
        for section in accept_sections:
            if re.search(r"\[\[.*?\]\]|doi|pmid|reference|evidence|support|literature|study|data", section, re.IGNORECASE):
                accepts_with_evidence += 1

        if accept_count > 0 and accepts_with_evidence == 0:
            issues.append(HookIssue(
                hook_id="R2", severity="WARNING", section="review",
                message="None of the ACCEPT'd fixes reference supporting evidence or literature",
                suggestion="When accepting reviewer comments, cite references or data to strengthen revisions (use [[wikilink]] or mention specific studies)",
            ))

        passed = all(i.severity != "CRITICAL" for i in issues)
        stats = {
            "accept_count": accept_count,
            "decline_count": decline_count,
            "total_decisions": total_decisions,
            "decline_ratio": round(decline_count / total_decisions, 2) if total_decisions > 0 else 0,
            "accepts_with_evidence": accepts_with_evidence,
        }
        return HookResult(hook_id="R2", passed=passed, issues=issues, stats=stats)

    # ── R3: EQUATOR Compliance Gate ────────────────────────────────

    def check_equator_compliance(self, round_num: int) -> HookResult:
        """
        R3: Verify EQUATOR reporting guideline compliance file exists and is substantive.

        Checks:
        - equator-compliance-{N}.md OR equator-na-{N}.md exists
        - If compliance file: ≥ MIN_EQUATOR_ITEMS checklist items
        - If N/A file: must contain justification
        """
        issues: list[HookIssue] = []

        compliance_path = self._audit_dir / f"equator-compliance-{round_num}.md"
        na_path = self._audit_dir / f"equator-na-{round_num}.md"

        if compliance_path.is_file():
            content = compliance_path.read_text(encoding="utf-8")
            # Count checklist items (lines starting with - [ ] or - [x] or numbered items)
            checklist_items = len(re.findall(
                r"(?:^|\n)\s*(?:[-*]\s*\[[ xX]\]|\d+[\.\)]\s)", content
            ))

            if checklist_items < MIN_EQUATOR_ITEMS:
                issues.append(HookIssue(
                    hook_id="R3", severity="CRITICAL", section="review",
                    message=f"EQUATOR checklist has only {checklist_items} items (minimum {MIN_EQUATOR_ITEMS})",
                    suggestion="Complete the EQUATOR reporting guideline checklist (CONSORT/STROBE/PRISMA/CARE etc.)",
                ))

            stats = {"type": "compliance", "checklist_items": checklist_items}

        elif na_path.is_file():
            content = na_path.read_text(encoding="utf-8")
            words = len(content.split())
            if words < 30:
                issues.append(HookIssue(
                    hook_id="R3", severity="WARNING", section="review",
                    message=f"EQUATOR N/A justification too brief ({words} words) — explain why no reporting guideline applies",
                    suggestion="Provide clear justification (≥30 words) for why no EQUATOR reporting guideline is applicable",
                ))
            stats = {"type": "not_applicable", "justification_words": words}

        else:
            issues.append(HookIssue(
                hook_id="R3", severity="CRITICAL", section="review",
                message=f"Neither equator-compliance-{round_num}.md nor equator-na-{round_num}.md found",
                suggestion="Create equator-compliance-{N}.md with reporting guideline checklist, or equator-na-{N}.md with justification",
            ))
            stats = {"type": "missing"}

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="R3", passed=passed, issues=issues, stats=stats)

    # ── R4: Review-Fix Traceability ────────────────────────────────

    def check_review_fix_traceability(
        self,
        round_num: int,
        issues_fixed: int,
        manuscript_changed: bool,
    ) -> HookResult:
        """
        R4: Verify ACCEPT'd issues actually produced manuscript changes.

        Checks:
        - If issues_fixed > 0, manuscript MUST have changed
        - ACCEPT'd issues should have corresponding changes described in response
        """
        issues: list[HookIssue] = []

        response_path = self._audit_dir / f"author-response-{round_num}.md"
        accept_count = 0
        if response_path.is_file():
            content = response_path.read_text(encoding="utf-8")
            accept_count = len(re.findall(r"\bACCEPT\b", content, re.IGNORECASE))

        # Core traceability: accepted issues should have produced changes
        if accept_count > 0 and not manuscript_changed:
            issues.append(HookIssue(
                hook_id="R4", severity="CRITICAL", section="review",
                message=f"{accept_count} issues ACCEPT'd but manuscript was NOT modified",
                suggestion="Apply the accepted fixes to the manuscript using patch_draft()",
            ))

        # Check issues_fixed vs accept_count consistency
        if accept_count > 0 and issues_fixed == 0:
            issues.append(HookIssue(
                hook_id="R4", severity="WARNING", section="review",
                message=f"{accept_count} issues ACCEPT'd but issues_fixed=0 — inconsistent",
                suggestion=f"Set issues_fixed={accept_count} or higher to reflect accepted changes",
            ))

        # Check for change descriptions in response (look for "Changed:", "Fixed:", "Updated:", etc.)
        if response_path.is_file():
            content = response_path.read_text(encoding="utf-8")
            change_descriptors = len(re.findall(
                r"(?:changed|modified|updated|revised|added|removed|rewrote|corrected|fixed|edited)",
                content, re.IGNORECASE,
            ))
            if accept_count > 0 and change_descriptors == 0:
                issues.append(HookIssue(
                    hook_id="R4", severity="WARNING", section="review",
                    message="Author response lacks change descriptions — each ACCEPT should describe what was changed",
                    suggestion="Add change descriptions (e.g., 'Changed: rewrote paragraph 3 of Discussion to clarify...')",
                ))

        passed = all(i.severity != "CRITICAL" for i in issues)
        stats = {
            "accept_count": accept_count,
            "issues_fixed": issues_fixed,
            "manuscript_changed": manuscript_changed,
        }
        return HookResult(hook_id="R4", passed=passed, issues=issues, stats=stats)

    # ── R5: Post-Review Anti-AI Gate ───────────────────────────────

    def check_post_review_anti_ai(self, manuscript_content: str) -> HookResult:
        """
        R5: Re-run Anti-AI detection after review edits.

        Review fixes can inadvertently re-introduce AI-characteristic language.
        Delegates to WritingHooksEngine A3/A3b and aggregates.
        """
        from .writing_hooks import WritingHooksEngine

        engine = WritingHooksEngine(self._project_dir)
        a3_result = engine.check_anti_ai_patterns(manuscript_content)
        a3b_result = engine.check_ai_writing_signals(manuscript_content)

        issues: list[HookIssue] = []
        # Elevate A3/A3b issues as R5 issues
        for issue in a3_result.issues:
            issues.append(HookIssue(
                hook_id="R5",
                severity=issue.severity,
                section=issue.section,
                message=f"[Post-Review A3] {issue.message}",
                location=issue.location,
                suggestion=issue.suggestion,
            ))
        for issue in a3b_result.issues:
            issues.append(HookIssue(
                hook_id="R5",
                severity=issue.severity,
                section=issue.section,
                message=f"[Post-Review A3b] {issue.message}",
                location=issue.location,
                suggestion=issue.suggestion,
            ))

        passed = a3_result.passed and a3b_result.passed
        stats = {
            "a3_passed": a3_result.passed,
            "a3b_passed": a3b_result.passed,
            "a3_critical": a3_result.critical_count,
            "a3b_critical": a3b_result.critical_count,
            "total_ai_issues": len(issues),
        }
        return HookResult(hook_id="R5", passed=passed, issues=issues, stats=stats)

    # ── R6: Citation Budget Gate ───────────────────────────────────

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
            return HookResult(
                hook_id="R6",
                passed=True,
                issues=[],
                stats={"total_refs": total_refs, "max_refs": "not_configured", "over_budget": 0},
            )

        over_budget = total_refs - max_refs

        if over_budget > REF_BUDGET_HEADROOM:
            issues.append(HookIssue(
                hook_id="R6", severity="CRITICAL", section="References",
                message=f"Citation count ({total_refs}) exceeds journal limit ({max_refs}) by {over_budget}",
                suggestion=f"Remove {over_budget} lowest-priority references. Use citation_decisions.json priority field to rank.",
            ))

            # Provide specific trim suggestions based on citation_decisions.json
            trim_suggestions = self._suggest_refs_to_trim(
                wikilinks, manuscript_content, over_budget,
            )
            if trim_suggestions:
                for ref_key, reason in trim_suggestions:
                    issues.append(HookIssue(
                        hook_id="R6", severity="WARNING", section="References",
                        message=f"Trim candidate: [[{ref_key}]] — {reason}",
                        suggestion=f"Remove [[{ref_key}]] from manuscript and references, or justify keeping it in citation_decisions.json",
                    ))

        elif over_budget == 0:
            issues.append(HookIssue(
                hook_id="R6", severity="WARNING", section="References",
                message=f"Citation count ({total_refs}) at exact limit ({max_refs}) — no room for additional references",
                suggestion="Consider whether all references are essential; any new addition will require removing another",
            ))

        # Check for refs without citation_decisions.json entry
        decisions_path = self._project_dir / "citation_decisions.json"
        decisions: dict[str, Any] = {}
        if decisions_path.is_file():
            try:
                decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        undocumented_refs = [ref for ref in wikilinks if ref not in decisions]
        if undocumented_refs and over_budget > 0:
            issues.append(HookIssue(
                hook_id="R6", severity="WARNING", section="References",
                message=f"{len(undocumented_refs)} references lack citation_decisions.json entry — cannot prioritise without justification",
                suggestion="Add priority (1-5) and justification to citation_decisions.json for all references to enable informed trimming",
            ))

        passed = over_budget <= REF_BUDGET_HEADROOM
        stats = {
            "total_refs": total_refs,
            "max_refs": max_refs,
            "over_budget": max(0, over_budget),
            "undocumented_refs": len(undocumented_refs),
            "budget_utilization_pct": round(total_refs / max_refs * 100, 1) if max_refs > 0 else 0,
        }
        return HookResult(hook_id="R6", passed=passed, issues=issues, stats=stats)

    # ── Batch Runner ───────────────────────────────────────────────

    def run_all(
        self,
        round_num: int,
        issues_fixed: int = 0,
        manuscript_changed: bool = True,
        manuscript_content: str = "",
    ) -> dict[str, HookResult]:
        """
        Run all R-series hooks for a review round.

        Returns dict mapping hook_id -> HookResult.
        """
        results: dict[str, HookResult] = {}
        results["R1"] = self.check_review_report_depth(round_num)
        results["R2"] = self.check_author_response_completeness(round_num)
        results["R3"] = self.check_equator_compliance(round_num)
        results["R4"] = self.check_review_fix_traceability(
            round_num, issues_fixed, manuscript_changed,
        )
        if manuscript_content:
            results["R5"] = self.check_post_review_anti_ai(manuscript_content)
            results["R6"] = self.check_citation_budget(manuscript_content)
        return results

    # ── Helpers ─────────────────────────────────────────────────────

    def _count_severity_in_report(self, content: str, severity: str) -> int:
        """Count issues of a given severity in review report."""
        # Try YAML frontmatter first
        yaml_match = re.search(rf"^\s*{severity}:\s*(\d+)", content, re.MULTILINE)
        if yaml_match:
            return int(yaml_match.group(1))

        # Fall back to counting headings/list items with severity keyword
        keywords = SEVERITY_KEYWORDS.get(severity, [severity])
        count = 0
        for keyword in keywords:
            count += len(re.findall(
                rf"(?:^|\n)\s*[-*]\s*.*\b{keyword}\b",
                content, re.IGNORECASE,
            ))
        return count

    def _count_total_issues_in_report(self, content: str) -> int:
        """Count total issues across all severities in review report."""
        total = 0
        for severity in ("major", "minor", "optional"):
            total += self._count_severity_in_report(content, severity)
        # If YAML frontmatter didn't work, count numbered/bulleted items under issue headings
        if total == 0:
            total = len(re.findall(
                r"(?:^|\n)\s*(?:\d+[\.\)]\s|[-*]\s+(?!#))",
                content,
            ))
        return total

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

        # Load citation decisions for priority
        decisions_path = self._project_dir / "citation_decisions.json"
        decisions: dict[str, Any] = {}
        if decisions_path.is_file():
            try:
                decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        # Build scoring: lower score = higher trim priority
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

        # Sort by score ascending (lowest score = first to trim)
        scored.sort(key=lambda x: x[1])

        # Return top N suggestions
        return [(ref, reason) for ref, _, reason in scored[:over_budget]]


__all__ = ["ReviewHooksEngine"]
