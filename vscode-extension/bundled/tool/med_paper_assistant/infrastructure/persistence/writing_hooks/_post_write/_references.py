"""Writing Hooks — A7 reference sufficiency (pre-write gate)."""

from __future__ import annotations

from pathlib import Path

from .._models import HookIssue, HookResult


def _count_saved_references(project_dir: Path) -> int:
    refs_dir = project_dir / "references"
    ref_count = 0
    if refs_dir.is_dir():
        ref_count = len(list(refs_dir.glob("*/metadata.json")))
        if ref_count == 0:
            ref_count = len(list(refs_dir.glob("*.md")))
    return ref_count


def _insufficient_issue(ref_count: int, min_refs: int, paper_type: str) -> HookIssue:
    deficit = min_refs - ref_count
    return HookIssue(
        hook_id="A7",
        severity="CRITICAL",
        section="references",
        message=(
            f"Insufficient references: {ref_count}/{min_refs} "
            f"(paper type: {paper_type}, need {deficit} more). "
            f"Expand literature search before writing."
        ),
        suggestion=(
            f"Run more searches with unified_search() and save at least "
            f"{deficit} additional references with save_reference_mcp(pmid)."
        ),
    )


def _sufficient_issue(
    ref_count: int, min_refs: int, paper_type: str, max_refs: int | None
) -> HookIssue:
    budget_note = f", max {max_refs}" if max_refs else ""
    return HookIssue(
        hook_id="A7",
        severity="INFO",
        section="references",
        message=(
            f"Reference library: {ref_count}/{min_refs} minimum met "
            f"(paper type: {paper_type}{budget_note})."
        ),
    )


class ReferenceSufficiencyHooksMixin:
    """A7: saved references must meet the paper-type minimum before writing."""

    def check_reference_sufficiency(self) -> HookResult:
        """Hook A7: Check that saved references meet paper-type-specific minimum.

        Code-Enforced pre-write check. Reads journal-profile.yaml for paper type,
        counts saved references, and compares against minimum thresholds.

        This is the WRITING-SIDE enforcement counterpart to Phase 2 Gate.
        Phase 2 Gate blocks phase transitions; A7 blocks individual write operations
        when the reference library is known to be insufficient.

        Returns:
            HookResult with CRITICAL severity if below minimum.
        """
        issues: list[HookIssue] = []
        paper_type = self._get_paper_type()
        min_refs = self._get_min_references(paper_type)
        ref_count = _count_saved_references(self._project_dir)

        passed = ref_count >= min_refs
        if not passed:
            issues.append(_insufficient_issue(ref_count, min_refs, paper_type))
        else:
            max_refs = self._get_max_references(paper_type)
            issues.append(_sufficient_issue(ref_count, min_refs, paper_type, max_refs))

        return HookResult(
            hook_id="A7",
            passed=passed,
            issues=issues,
        )
