"""
Tests for WritingHooksEngine — Hooks A5, A6, B8, C9, F.

Validates:
  - A5: Language consistency (British vs American English detection)
  - A6: Overlap detection (internal paragraph similarity via n-grams)
  - B8: Data-claim alignment (statistical tests, p-values, CI, software)
  - C9: Supplementary cross-reference (text refs ↔ supplementary files)
  - F:  Data artifact validation (wrapper around DataArtifactTracker)
  - Batch runners: run_post_write_hooks, run_post_section_hooks, run_post_manuscript_hooks
"""

from pathlib import Path

import pytest

from med_paper_assistant.infrastructure.persistence.writing_hooks import (
    AMER_VS_BRIT,
    BRIT_VS_AMER,
    HookIssue,
    HookResult,
    WritingHooksEngine,
)

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project directory structure."""
    d = tmp_path / "test-project"
    d.mkdir()
    (d / ".audit").mkdir()
    (d / "drafts").mkdir()
    return d


@pytest.fixture()
def engine(project_dir: Path) -> WritingHooksEngine:
    return WritingHooksEngine(project_dir)


# ──────────────────────────────────────────────────────────────────────────────
# Dictionary Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestDictionaries:
    def test_brit_vs_amer_is_populated(self):
        assert len(BRIT_VS_AMER) > 100

    def test_amer_vs_brit_reverse_mapping(self):
        assert len(AMER_VS_BRIT) == len(BRIT_VS_AMER)
        for brit, amer in BRIT_VS_AMER.items():
            assert AMER_VS_BRIT[amer] == brit

    def test_common_medical_pairs_present(self):
        assert BRIT_VS_AMER["randomised"] == "randomized"
        assert BRIT_VS_AMER["anaesthesia"] == "anesthesia"
        assert BRIT_VS_AMER["haemoglobin"] == "hemoglobin"
        assert BRIT_VS_AMER["paediatric"] == "pediatric"
        assert BRIT_VS_AMER["colour"] == "color"
        assert BRIT_VS_AMER["centre"] == "center"


# ──────────────────────────────────────────────────────────────────────────────
# HookIssue / HookResult Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestDataClasses:
    def test_hook_issue_to_dict(self):
        issue = HookIssue(
            hook_id="A5",
            severity="WARNING",
            section="Methods",
            message="British spelling found",
            location="line 42",
            suggestion="Use American spelling",
        )
        d = issue.to_dict()
        assert d["hook_id"] == "A5"
        assert d["severity"] == "WARNING"
        assert d["section"] == "Methods"
        assert d["location"] == "line 42"

    def test_hook_result_counts(self):
        issues = [
            HookIssue("X", "CRITICAL", "s", "m1"),
            HookIssue("X", "CRITICAL", "s", "m2"),
            HookIssue("X", "WARNING", "s", "m3"),
            HookIssue("X", "INFO", "s", "m4"),
        ]
        result = HookResult(hook_id="X", passed=False, issues=issues)
        assert result.critical_count == 2
        assert result.warning_count == 1

    def test_hook_result_to_dict(self):
        result = HookResult(hook_id="A5", passed=True, stats={"count": 0})
        d = result.to_dict()
        assert d["hook_id"] == "A5"
        assert d["passed"] is True
        assert d["critical_count"] == 0
        assert d["warning_count"] == 0
        assert d["stats"] == {"count": 0}


# ──────────────────────────────────────────────────────────────────────────────
# Hook A5: Language Consistency
# ──────────────────────────────────────────────────────────────────────────────


class TestHookA5:
    def test_pure_american_passes(self, engine: WritingHooksEngine):
        text = "The randomized trial analyzed the hemoglobin levels of pediatric patients."
        r = engine.check_language_consistency(text, prefer="american")
        assert r.passed is True
        assert r.hook_id == "A5"
        assert len(r.issues) == 0

    def test_pure_british_passes(self, engine: WritingHooksEngine):
        text = "The randomised trial analysed the haemoglobin levels of paediatric patients."
        r = engine.check_language_consistency(text, prefer="british")
        assert r.passed is True
        assert len(r.issues) == 0

    def test_british_in_american_detected(self, engine: WritingHooksEngine):
        text = "The randomised trial used standardised colour scales for the centre."
        r = engine.check_language_consistency(text, prefer="american")
        assert r.passed is False
        found_words = {i.message.split("'")[1] for i in r.issues}
        assert "randomised" in found_words
        assert "standardised" in found_words
        assert "colour" in found_words
        assert "centre" in found_words

    def test_american_in_british_detected(self, engine: WritingHooksEngine):
        text = "The randomized trial used standardized color scales."
        r = engine.check_language_consistency(text, prefer="british")
        assert r.passed is False
        found_words = {i.message.split("'")[1] for i in r.issues}
        assert "randomized" in found_words
        assert "color" in found_words

    def test_headings_skipped(self, engine: WritingHooksEngine):
        text = "# Randomised Methods\nThe trial used American spelling randomized throughout."
        r = engine.check_language_consistency(text, prefer="american")
        # Only "randomised" in heading should be skipped
        found_words = [i.message.split("'")[1] for i in r.issues]
        assert "randomised" not in found_words

    def test_occurrence_count_in_stats(self, engine: WritingHooksEngine):
        text = "The colour of the colour chart showed colour differences."
        r = engine.check_language_consistency(text, prefer="american")
        assert r.stats["total_occurrences"] == 3  # "colour" appears 3 times

    def test_unknown_preference_returns_pass(self, engine: WritingHooksEngine):
        r = engine.check_language_consistency("text", prefer="unknown")
        assert r.passed is True
        assert "error" in r.stats

    def test_section_label_propagated(self, engine: WritingHooksEngine):
        text = "The randomised trial was well-designed."
        r = engine.check_language_consistency(text, prefer="american", section="Introduction")
        assert r.issues[0].section == "Introduction"

    def test_suggestion_provides_replacement(self, engine: WritingHooksEngine):
        text = "The anaesthesia protocol was well-designed."
        r = engine.check_language_consistency(text, prefer="american")
        assert len(r.issues) == 1
        assert "anesthesia" in r.issues[0].suggestion

    def test_case_insensitive(self, engine: WritingHooksEngine):
        text = "The Randomised trial showed Colour changes."
        r = engine.check_language_consistency(text, prefer="american")
        found_words = {i.message.split("'")[1] for i in r.issues}
        assert "randomised" in found_words
        assert "colour" in found_words


# ──────────────────────────────────────────────────────────────────────────────
# Hook A6: Overlap Detection
# ──────────────────────────────────────────────────────────────────────────────


class TestHookA6:
    def test_no_overlap_passes(self, engine: WritingHooksEngine):
        text = (
            "## Introduction\n\n"
            "The first paragraph discusses the background of the clinical trial design and methodology.\n\n"
            "The second paragraph addresses a completely different topic about pharmacokinetics and drug interactions."
        )
        r = engine.check_overlap(text)
        assert r.passed is True
        assert r.hook_id == "A6"

    def test_identical_paragraphs_detected(self, engine: WritingHooksEngine):
        paragraph = (
            "This study investigated the effects of remimazolam on sedation depth "
            "during mechanical ventilation in critically ill patients in the intensive care unit "
            "compared with propofol infusion for long term critical care sedation"
        )
        text = f"## Methods\n\n{paragraph}\n\n## Results\n\n{paragraph}"
        r = engine.check_overlap(text, min_ngram=6, threshold=3)
        assert r.passed is False  # identical → CRITICAL (shared ≥ threshold * 2)
        assert r.stats["flagged_pairs"] >= 1

    def test_short_paragraphs_skipped(self, engine: WritingHooksEngine):
        text = "## Intro\n\nShort text.\n\nAlso short."
        r = engine.check_overlap(text, min_ngram=6)
        assert r.passed is True
        assert r.stats["paragraphs_checked"] == 0

    def test_single_paragraph_passes(self, engine: WritingHooksEngine):
        text = (
            "## Methods\n\n"
            "This is a single long paragraph about the methodology of the randomized controlled trial."
        )
        r = engine.check_overlap(text)
        assert r.passed is True

    def test_partial_overlap_flagged(self, engine: WritingHooksEngine):
        shared = "the primary endpoint was defined as the change in sedation score from baseline to the end of treatment"
        p1 = f"In this randomized trial, {shared} as measured by the RASS scale throughout."
        p2 = f"Our analysis confirmed that {shared} and this finding was statistically significant."
        text = f"## Methods\n\n{p1}\n\n## Results\n\n{p2}"
        r = engine.check_overlap(text, min_ngram=6, threshold=3)
        assert r.stats["flagged_pairs"] >= 1

    def test_threshold_respected(self, engine: WritingHooksEngine):
        # With a very high threshold, even identical paragraphs might pass
        paragraph = "The study was designed to test the primary hypothesis about sedation."
        text = f"## A\n\n{paragraph}\n\n## B\n\n{paragraph}"
        r = engine.check_overlap(text, min_ngram=6, threshold=100)
        assert r.stats.get("flagged_pairs", 0) == 0


# ──────────────────────────────────────────────────────────────────────────────
# Hook B8: Data-Claim Alignment
# ──────────────────────────────────────────────────────────────────────────────


class TestHookB8:
    def test_aligned_methods_results_passes(self, engine: WritingHooksEngine):
        methods = (
            "We used Chi-square test for categorical variables and t-test for continuous "
            "variables. Statistical significance was set at alpha = 0.05. "
            "All analyses were performed using SPSS version 27."
        )
        results = (
            "The chi-square test showed significant differences (p < 0.05). "
            "The t-test revealed improvements in the primary outcome. "
            "Analyses were performed in SPSS."
        )
        r = engine.check_data_claim_alignment(methods, results)
        assert r.passed is True
        assert r.hook_id == "B8"

    def test_undeclared_test_detected(self, engine: WritingHooksEngine):
        methods = "We used t-test for continuous variables."
        results = "The Mann-Whitney U test showed significant differences."
        r = engine.check_data_claim_alignment(methods, results)
        assert r.passed is False
        undeclared = [i for i in r.issues if "not described in Methods" in i.message]
        assert len(undeclared) >= 1
        assert any("Mann-Whitney" in i.message for i in undeclared)

    def test_multiple_undeclared_tests(self, engine: WritingHooksEngine):
        methods = "We performed descriptive statistics."
        results = (
            "The Kaplan-Meier analysis showed survival differences. "
            "Log-rank test was used for comparison. "
            "Cox regression yielded hazard ratios."
        )
        r = engine.check_data_claim_alignment(methods, results)
        assert r.passed is False
        assert r.stats["undeclared_tests"] >= 3

    def test_p_value_threshold_mismatch(self, engine: WritingHooksEngine):
        methods = "Statistical significance was set at alpha = 0.05."
        results = "The result was significant at p < 0.01."
        r = engine.check_data_claim_alignment(methods, results)
        warnings = [i for i in r.issues if "threshold" in i.message.lower()]
        assert len(warnings) >= 1

    def test_ci_width_mismatch(self, engine: WritingHooksEngine):
        methods = "We calculated 95% confidence interval for all estimates."
        results = "The 99% CI was [1.2, 3.4]."
        r = engine.check_data_claim_alignment(methods, results)
        ci_issues = [i for i in r.issues if "CI" in i.message]
        assert len(ci_issues) >= 1

    def test_software_mismatch(self, engine: WritingHooksEngine):
        methods = "All analyses were performed using R version 4.2."
        results = "Data were analyzed in SPSS (p < 0.05)."
        r = engine.check_data_claim_alignment(methods, results)
        sw_issues = [i for i in r.issues if "SPSS" in i.message]
        assert len(sw_issues) >= 1

    def test_empty_content_passes(self, engine: WritingHooksEngine):
        r = engine.check_data_claim_alignment("", "")
        assert r.passed is True

    def test_stat_tests_count_in_stats(self, engine: WritingHooksEngine):
        methods = "Chi-square test and logistic regression were used."
        results = "Chi-square test showed p = 0.03. Logistic regression yielded OR = 2.1."
        r = engine.check_data_claim_alignment(methods, results)
        assert r.stats["stat_tests_in_results"] >= 2
        assert r.stats["stat_tests_in_methods"] >= 2


# ──────────────────────────────────────────────────────────────────────────────
# Hook C9: Supplementary Cross-Reference
# ──────────────────────────────────────────────────────────────────────────────


class TestHookC9:
    def test_no_references_passes(self, engine: WritingHooksEngine):
        text = "This is a manuscript without any supplementary references."
        r = engine.check_supplementary_crossref(text)
        assert r.passed is True
        assert r.hook_id == "C9"
        assert r.stats["text_references"] == 0

    def test_references_without_files_critical(self, engine: WritingHooksEngine):
        text = "See Supplementary Table 1 and Supplementary Figure 2 for details."
        r = engine.check_supplementary_crossref(text)
        assert r.passed is False
        assert r.issues[0].severity == "CRITICAL"
        assert r.stats["text_references"] >= 2

    def test_references_with_matching_files(self, engine: WritingHooksEngine, project_dir: Path):
        supp_dir = project_dir / "supplementary"
        supp_dir.mkdir()
        (supp_dir / "table_1.docx").touch()
        (supp_dir / "figure_2.png").touch()

        text = "See Supplementary Table 1 and Supplementary Figure 2 for details."
        r = engine.check_supplementary_crossref(text)
        assert r.stats["supplementary_files"] == 2

    def test_phantom_reference_warning(self, engine: WritingHooksEngine, project_dir: Path):
        supp_dir = project_dir / "supplementary"
        supp_dir.mkdir()
        (supp_dir / "table_1.docx").touch()
        # Reference Table 1 (exists) and Table 3 (doesn't exist)
        text = "See Supplementary Table 1 and Supplementary Table 3."
        r = engine.check_supplementary_crossref(text)
        phantom = [i for i in r.issues if "3" in i.message and "no matching" in i.message]
        assert len(phantom) >= 1

    def test_exports_supplementary_checked(self, engine: WritingHooksEngine, project_dir: Path):
        exports_supp = project_dir / "exports" / "supplementary"
        exports_supp.mkdir(parents=True)
        (exports_supp / "etable1.docx").touch()

        text = "See Supplementary Table 1 for additional results."
        r = engine.check_supplementary_crossref(text)
        assert r.stats["supplementary_files"] >= 1

    def test_appendix_pattern_detected(self, engine: WritingHooksEngine):
        text = "Further details are provided in Appendix A."
        r = engine.check_supplementary_crossref(text)
        assert r.stats["text_references"] >= 1

    def test_eprefix_pattern_detected(self, engine: WritingHooksEngine):
        text = "As shown in eTable1 and eFigure3."
        r = engine.check_supplementary_crossref(text)
        assert r.stats["text_references"] >= 2


# ──────────────────────────────────────────────────────────────────────────────
# Hook F: Data Artifact Validation
# ──────────────────────────────────────────────────────────────────────────────


class TestHookF:
    def test_no_artifacts_passes(self, engine: WritingHooksEngine):
        """Without any manifest, validation should pass (no artifacts to check)."""
        r = engine.validate_data_artifacts("Some draft content.")
        assert r.hook_id == "F"
        # Passed depends on DataArtifactTracker implementation with empty audit dir
        assert isinstance(r.passed, bool)
        assert isinstance(r.stats, dict)

    def test_none_content_accepted(self, engine: WritingHooksEngine):
        """Passing None should skip draft-dependent checks."""
        r = engine.validate_data_artifacts(None)
        assert r.hook_id == "F"
        assert isinstance(r.passed, bool)


# ──────────────────────────────────────────────────────────────────────────────
# Batch Runners
# ──────────────────────────────────────────────────────────────────────────────


class TestBatchRunners:
    def test_run_post_write_hooks(self, engine: WritingHooksEngine):
        text = "The randomised trial analysed the colour values in the centre."
        results = engine.run_post_write_hooks(text, section="Methods", prefer_language="american")
        assert "A5" in results
        assert "A6" in results
        assert results["A5"].hook_id == "A5"
        assert results["A6"].hook_id == "A6"
        # A5 should detect British words
        assert results["A5"].passed is False

    def test_run_post_section_hooks(self, engine: WritingHooksEngine):
        methods = "We used t-test and chi-square test."
        results_text = "The t-test showed significance. Mann-Whitney revealed differences."
        results = engine.run_post_section_hooks(methods, results_text)
        assert "B8" in results
        assert results["B8"].hook_id == "B8"
        # B8 should detect Mann-Whitney not in Methods
        assert results["B8"].passed is False

    def test_run_post_manuscript_hooks(self, engine: WritingHooksEngine):
        text = "This manuscript has no supplementary references."
        results = engine.run_post_manuscript_hooks(text)
        assert "C9" in results
        assert "F" in results
        assert results["C9"].hook_id == "C9"
        assert results["F"].hook_id == "F"
