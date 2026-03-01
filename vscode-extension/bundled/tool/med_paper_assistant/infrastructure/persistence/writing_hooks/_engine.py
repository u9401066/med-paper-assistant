"""Writing Hooks — Engine class (composition of all mixin series + batch runners)."""

from __future__ import annotations

from pathlib import Path

from ._data_artifacts import DataArtifactsMixin
from ._git import GitHooksMixin
from ._journal_config import JournalConfigMixin
from ._manuscript import ManuscriptHooksMixin
from ._models import HookIssue, HookResult
from ._post_write import PostWriteHooksMixin
from ._precommit import PreCommitMixin
from ._section_quality import SectionQualityMixin
from ._text_utils import TextUtilsMixin


class WritingHooksEngine(
    JournalConfigMixin,
    TextUtilsMixin,
    PostWriteHooksMixin,
    SectionQualityMixin,
    ManuscriptHooksMixin,
    DataArtifactsMixin,
    PreCommitMixin,
    GitHooksMixin,
):
    """
    Unified engine for all writing-quality hooks.

    Composes all mixin series:
    - A-series (PostWriteHooksMixin): A1–A6, A3b — post-write immediate checks
    - B-series (SectionQualityMixin): B8–B16 — section-level quality
    - C-series (ManuscriptHooksMixin): C3–C13 — manuscript-level consistency
    - F-series (DataArtifactsMixin): F1–F4 — data artifact validation
    - P-series (PreCommitMixin): P5, P7 — pre-commit integrity
    - G-series (GitHooksMixin): G9 — git status

    Batch runners orchestrate hooks into logical groups.
    """

    def __init__(self, project_dir: Path | str) -> None:
        # JournalConfigMixin.__init__ sets _project_dir, _audit_dir, etc.
        JournalConfigMixin.__init__(self, project_dir)

    # ── Batch Runner: Post-Write ───────────────────────────────────

    def run_post_write_hooks(
        self,
        content: str,
        section: str = "manuscript",
        prefer_language: str = "american",
    ) -> dict[str, HookResult]:
        """
        Run all post-write hooks (A1-A6, B9, B10, B15) on a section.

        Returns:
            Dict mapping hook_id -> HookResult.
        """
        return {
            "A1": self.check_word_count_compliance(content, section_name=section),
            "A2": self.check_citation_density(content, section_name=section),
            "A3": self.check_anti_ai_patterns(content, section=section),
            "A3b": self.check_ai_writing_signals(content, section=section),
            "A4": self.check_wikilink_format(content, section=section),
            "A5": self.check_language_consistency(content, prefer=prefer_language, section=section),
            "A6": self.check_overlap(content),
            "B9": self.check_section_tense(content, section=section),
            "B10": self.check_paragraph_quality(content, section=section),
            "B15": self.check_hedging_density(content, section=section),
        }

    # ── Batch Runner: Post-Section ─────────────────────────────────

    def run_post_section_hooks(
        self,
        methods_content: str,
        results_content: str,
        full_content: str = "",
    ) -> dict[str, HookResult]:
        """
        Run post-section hooks (B8-B16).

        B8 needs Methods + Results.
        B9-B16 need full manuscript content for section-aware quality checks.

        Returns:
            Dict mapping hook_id -> HookResult.
        """
        results: dict[str, HookResult] = {
            "B8": self.check_data_claim_alignment(methods_content, results_content),
        }
        if full_content:
            results["B11"] = self.check_results_interpretation(full_content)
            results["B12"] = self.check_intro_structure(full_content)
            results["B13"] = self.check_discussion_structure(full_content)
            results["B14"] = self.check_ethical_statements(full_content)
            results["B16"] = self.check_effect_size_reporting(full_content)
        return results

    # ── Batch Runner: Post-Manuscript ──────────────────────────────

    def run_post_manuscript_hooks(
        self,
        content: str,
    ) -> dict[str, HookResult]:
        """
        Run all post-manuscript hooks (C3, C4, C5, C6, C7a, C7d, C9, F) on the full manuscript.

        Returns:
            Dict mapping hook_id -> HookResult.
        """
        return {
            "C3": self.check_n_value_consistency(content),
            "C4": self.check_abbreviation_first_use(content),
            "C5": self.check_wikilink_resolvable(content),
            "C6": self.check_total_word_count(content),
            "C7a": self.check_figure_table_counts(content),
            "C7d": self.check_cross_references(content),
            "C9": self.check_supplementary_crossref(content),
            "F": self.validate_data_artifacts(content),
        }

    # ── Batch Runner: Pre-Commit ───────────────────────────────────

    def run_precommit_hooks(
        self,
        content: str,
        prefer_language: str = "american",
    ) -> dict[str, HookResult]:
        """
        Run all pre-commit hooks (P1, P2, P4, P5, P7).

        P1 delegates to C5 (wikilink resolvable).
        P2 delegates to A3 (anti-AI, with P2 thresholds).
        P4 delegates to A1 (word count, with 50% critical threshold).

        Returns:
            Dict mapping hook_id -> HookResult.
        """
        # P1: Citation integrity — delegate to C5 with hook_id remap
        p1_result = self.check_wikilink_resolvable(content)
        p1_result.hook_id = "P1"
        for issue in p1_result.issues:
            issue.hook_id = "P1"

        # P2: Anti-AI scan — delegate to A3 with P2 thresholds
        p2_result = self.check_anti_ai_patterns(
            content,
            section="precommit",
            warn_threshold=1,
            critical_threshold=3,
        )
        p2_result.hook_id = "P2"
        for issue in p2_result.issues:
            issue.hook_id = "P2"

        # P2b: Structural AI signals — delegate to A3b
        p2b_result = self.check_ai_writing_signals(content, section="precommit")
        p2b_result.hook_id = "P2"
        # Merge A3b issues into P2 result
        for issue in p2b_result.issues:
            issue.hook_id = "P2"
            p2_result.issues.append(issue)
        if not p2b_result.passed:
            p2_result.passed = False

        # P4: Word count — delegate to A1 with 50% critical threshold
        p4_result = self.check_word_count_compliance(content, critical_threshold_pct=50)
        p4_result.hook_id = "P4"
        for issue in p4_result.issues:
            issue.hook_id = "P4"

        return {
            "P1": p1_result,
            "P2": p2_result,
            "P4": p4_result,
            "P5": self.check_protected_content(),
            "P7": self.check_reference_integrity(content),
        }
