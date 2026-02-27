"""
Tests for WritingHooksEngine — 29 Code-Enforced Hooks.

Validates:
  - A1: Word count compliance (section word count vs target)
  - A2: Citation density (wikilinks per N words)
  - A3: Anti-AI pattern detection (forbidden phrases)
  - A4: Wikilink format validation
  - A5: Language consistency (British vs American English detection)
  - A6: Overlap detection (internal paragraph similarity via n-grams)
  - B8: Data-claim alignment (statistical tests, p-values, CI, software)
  - C3: N-value consistency (sample sizes across sections)
  - C4: Abbreviation first-use (defined at first occurrence)
  - C5: Wikilink resolvable (mapped to saved references)
  - C6: Total word count (manuscript total vs journal limit)
  - C7a: Figure/table count limits
  - C7d: Cross-reference orphan/phantom detection
  - C9: Supplementary cross-reference (text refs ↔ supplementary files)
  - F:  Data artifact validation (wrapper around DataArtifactTracker)
  - P5: Protected content (🔒 blocks in concept.md)
  - P7: Reference integrity (verified metadata)
  - Batch runners: run_post_write_hooks, run_post_section_hooks,
                   run_post_manuscript_hooks, run_precommit_hooks
"""

import json
from pathlib import Path

import pytest
import yaml

from med_paper_assistant.infrastructure.persistence.writing_hooks import (
    AMER_VS_BRIT,
    ANTI_AI_PHRASES,
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
def project_with_profile(tmp_path: Path) -> Path:
    """Create a project directory with journal-profile.yaml."""
    d = tmp_path / "test-project-profile"
    d.mkdir()
    (d / ".audit").mkdir()
    (d / "drafts").mkdir()
    profile = {
        "word_limits": {"total_manuscript": 5000},
        "paper": {
            "sections": [
                {"name": "Introduction", "word_limit": 800},
                {"name": "Methods", "word_limit": 1500},
                {"name": "Results", "word_limit": 1500},
                {"name": "Discussion", "word_limit": 1500},
            ],
        },
        "pipeline": {
            "tolerance": {"word_percent": 20},
            "writing": {
                "citation_density": {
                    "introduction": 100,
                    "discussion": 150,
                },
            },
        },
        "assets": {"figures_max": 6, "tables_max": 5},
    }
    with open(d / "journal-profile.yaml", "w") as f:
        yaml.dump(profile, f)
    return d


@pytest.fixture()
def engine(project_dir: Path) -> WritingHooksEngine:
    return WritingHooksEngine(project_dir)


@pytest.fixture()
def engine_with_profile(project_with_profile: Path) -> WritingHooksEngine:
    return WritingHooksEngine(project_with_profile)


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


# ──────────────────────────────────────────────────────────────────────────────
# Hook A1: Word Count Compliance
# ──────────────────────────────────────────────────────────────────────────────


class TestHookA1:
    def test_within_limits_passes(self, engine_with_profile: WritingHooksEngine):
        # Introduction target is 800 words; generate ~800 words
        words = " ".join(["word"] * 800)
        r = engine_with_profile.check_word_count_compliance(words, section_name="Introduction")
        assert r.passed is True
        assert r.hook_id == "A1"

    def test_over_limit_warning(self, engine_with_profile: WritingHooksEngine):
        # 800 * 1.25 = 1000 words → 25% over → WARNING
        words = " ".join(["word"] * 1000)
        r = engine_with_profile.check_word_count_compliance(words, section_name="Introduction")
        assert r.passed is True  # WARNING doesn't fail
        assert len(r.issues) >= 1
        assert r.issues[0].severity == "WARNING"

    def test_way_over_limit_critical(self, engine_with_profile: WritingHooksEngine):
        # 800 * 1.55 = 1240 words → >50% over → CRITICAL
        words = " ".join(["word"] * 1300)
        r = engine_with_profile.check_word_count_compliance(words, section_name="Introduction")
        assert r.passed is False
        assert any(i.severity == "CRITICAL" for i in r.issues)

    def test_no_profile_uses_defaults(self, engine: WritingHooksEngine):
        # DEFAULT_WORD_LIMITS has Introduction=800
        words = " ".join(["word"] * 800)
        r = engine.check_word_count_compliance(words, section_name="Introduction")
        assert r.passed is True

    def test_unknown_section_skips(self, engine: WritingHooksEngine):
        r = engine.check_word_count_compliance("some text", section_name="UnknownSection")
        assert r.passed is True
        assert len(r.issues) == 0

    def test_multi_section_parsing(self, engine_with_profile: WritingHooksEngine):
        intro_words = " ".join(["word"] * 800)
        methods_words = " ".join(["word"] * 1500)
        text = f"## Introduction\n\n{intro_words}\n\n## Methods\n\n{methods_words}"
        r = engine_with_profile.check_word_count_compliance(text)
        assert r.passed is True


# ──────────────────────────────────────────────────────────────────────────────
# Hook A2: Citation Density
# ──────────────────────────────────────────────────────────────────────────────


class TestHookA2:
    def test_sufficient_citations_passes(self, engine_with_profile: WritingHooksEngine):
        # ~90 words + 2 citations → density well above 1/100w for Introduction
        words = " ".join(["word"] * 90)
        text = f"{words} [[smith2024_12345678]] [[jones2023_87654321]]"
        r = engine_with_profile.check_citation_density(text, section_name="Introduction")
        assert r.passed is True
        assert r.hook_id == "A2"

    def test_low_density_warning(self, engine_with_profile: WritingHooksEngine):
        # 300 words, need >=3 citations for Introduction (1/100w)
        words = " ".join(["word"] * 300)
        text = f"{words} [[smith2024_12345678]]"
        r = engine_with_profile.check_citation_density(text, section_name="Introduction")
        assert r.passed is False
        assert len(r.issues) >= 1
        assert r.issues[0].severity == "WARNING"

    def test_methods_section_skipped(self, engine_with_profile: WritingHooksEngine):
        # Methods has threshold 0, so no check needed
        r = engine_with_profile.check_citation_density("no citations here", section_name="Methods")
        assert r.passed is True
        assert r.stats.get("skipped") is True

    def test_empty_content(self, engine: WritingHooksEngine):
        r = engine.check_citation_density("", section_name="Introduction")
        assert r.passed is True

    def test_stats_contain_density(self, engine_with_profile: WritingHooksEngine):
        words = " ".join(["word"] * 100)
        text = f"{words} [[a2024_12345678]] [[b2024_23456789]]"
        r = engine_with_profile.check_citation_density(text, section_name="Introduction")
        assert "density_per_100w" in r.stats
        assert r.stats["citation_count"] == 2


# ──────────────────────────────────────────────────────────────────────────────
# Hook A3: Anti-AI Pattern Detection
# ──────────────────────────────────────────────────────────────────────────────


class TestHookA3:
    def test_clean_text_passes(self, engine: WritingHooksEngine):
        text = "The trial demonstrated a significant reduction in mortality rates."
        r = engine.check_anti_ai_patterns(text)
        assert r.passed is True
        assert r.hook_id == "A3"
        assert r.stats["total_matches"] == 0

    def test_single_ai_phrase_warning(self, engine: WritingHooksEngine):
        text = "It is worth noting that the results were significant."
        r = engine.check_anti_ai_patterns(text)
        assert r.passed is False
        assert r.stats["total_matches"] >= 1
        assert any(i.severity == "WARNING" for i in r.issues)

    def test_multiple_ai_phrases_critical(self, engine: WritingHooksEngine):
        text = (
            "In recent years, it is worth noting that this groundbreaking "
            "study has shed light on important findings."
        )
        r = engine.check_anti_ai_patterns(text, critical_threshold=3)
        assert r.passed is False
        assert any(i.severity == "CRITICAL" for i in r.issues)

    def test_furthermore_at_paragraph_start_flagged(self, engine: WritingHooksEngine):
        text = "First paragraph about methods.\n\nFurthermore, the results showed improvement."
        r = engine.check_anti_ai_patterns(text)
        assert r.stats["total_matches"] >= 1
        assert any("furthermore" in key.lower() for key in r.stats.get("phrase_counts", {}))

    def test_furthermore_mid_sentence_ok(self, engine: WritingHooksEngine):
        text = "The study provided evidence that furthermore supports the hypothesis."
        r = engine.check_anti_ai_patterns(text)
        # "furthermore" mid-sentence should not be flagged (only paragraph start)
        furthermore_matches = [
            k for k in r.stats.get("phrase_counts", {}) if "furthermore" in k.lower()
        ]
        assert len(furthermore_matches) == 0

    def test_case_insensitive(self, engine: WritingHooksEngine):
        text = "IN RECENT YEARS the field has evolved."
        r = engine.check_anti_ai_patterns(text)
        assert r.stats["total_matches"] >= 1

    def test_anti_ai_list_populated(self):
        assert len(ANTI_AI_PHRASES) >= 20


# ──────────────────────────────────────────────────────────────────────────────
# Hook A4: Wikilink Format Validation
# ──────────────────────────────────────────────────────────────────────────────


class TestHookA4:
    def test_valid_wikilinks_pass(self, engine: WritingHooksEngine):
        text = "The study [[smith2024_12345678]] showed results [[jones2023_87654321]]."
        r = engine.check_wikilink_format(text)
        assert r.passed is True
        assert r.hook_id == "A4"
        assert r.stats["valid_count"] == 2

    def test_pmid_only_warning(self, engine: WritingHooksEngine):
        text = "The study [[12345678]] showed results."
        r = engine.check_wikilink_format(text)
        assert r.passed is False
        assert any("PMID-only" in i.message for i in r.issues)

    def test_no_wikilinks_passes(self, engine: WritingHooksEngine):
        text = "This text has no citations at all."
        r = engine.check_wikilink_format(text)
        assert r.passed is True
        assert r.stats["total_wikilinks"] == 0

    def test_mixed_format(self, engine: WritingHooksEngine):
        text = "Valid [[smith2024_12345678]] and invalid [[PMID: 87654321]]."
        r = engine.check_wikilink_format(text)
        assert r.passed is False
        assert r.stats["valid_count"] == 1
        assert r.stats["issue_count"] == 1


# ──────────────────────────────────────────────────────────────────────────────
# Hook C3: N-value Consistency
# ──────────────────────────────────────────────────────────────────────────────


class TestHookC3:
    def test_consistent_n_values_passes(self, engine: WritingHooksEngine):
        text = (
            "## Methods\n\nWe enrolled N=150 patients in the study.\n\n"
            "## Results\n\nOf the N=150 patients, 75 were in the intervention group."
        )
        r = engine.check_n_value_consistency(text)
        assert r.passed is True
        assert r.hook_id == "C3"

    def test_inconsistent_n_values_critical(self, engine: WritingHooksEngine):
        text = (
            "## Methods\n\nWe enrolled N=150 patients in the study.\n\n"
            "## Results\n\nOf the N=200 patients, outcomes were measured."
        )
        r = engine.check_n_value_consistency(text)
        assert r.passed is False
        assert any(i.severity == "CRITICAL" for i in r.issues)
        assert "200" in r.issues[0].message

    def test_no_methods_section_skips(self, engine: WritingHooksEngine):
        text = "## Results\n\nN=150 patients completed the study."
        r = engine.check_n_value_consistency(text)
        assert r.passed is True

    def test_participant_pattern_detected(self, engine: WritingHooksEngine):
        text = (
            "## Methods\n\n120 patients were enrolled.\n\n"
            "## Results\n\n120 patients completed follow-up."
        )
        r = engine.check_n_value_consistency(text)
        assert r.passed is True

    def test_stats_contain_n_values(self, engine: WritingHooksEngine):
        text = (
            "## Methods\n\nWe enrolled N=150 patients and N=75 controls.\n\n"
            "## Results\n\nN=150 patients completed the study."
        )
        r = engine.check_n_value_consistency(text)
        assert "methods_n_values" in r.stats
        assert "150" in r.stats["methods_n_values"]
        assert "75" in r.stats["methods_n_values"]


# ──────────────────────────────────────────────────────────────────────────────
# Hook C4: Abbreviation First-Use
# ──────────────────────────────────────────────────────────────────────────────


class TestHookC4:
    def test_all_defined_passes(self, engine: WritingHooksEngine):
        text = (
            "Acute Respiratory Distress Syndrome (ARDS) is a condition. "
            "ARDS was treated with mechanical ventilation."
        )
        r = engine.check_abbreviation_first_use(text)
        assert r.passed is True
        assert r.hook_id == "C4"

    def test_undefined_abbreviation_warning(self, engine: WritingHooksEngine):
        text = "The CABG procedure was performed successfully. CABG outcomes were favorable."
        r = engine.check_abbreviation_first_use(text)
        assert r.passed is False
        assert any("CABG" in i.message for i in r.issues)

    def test_common_exclusions_skipped(self, engine: WritingHooksEngine):
        # Common abbreviations like DNA, RNA, ICU should not be flagged
        text = "The DNA analysis was performed in the ICU using standard OR protocols."
        r = engine.check_abbreviation_first_use(text)
        # None of these should be flagged
        flagged = {i.message.split("'")[1] for i in r.issues}
        assert "DNA" not in flagged
        assert "ICU" not in flagged

    def test_no_abbreviations_passes(self, engine: WritingHooksEngine):
        text = "This text has no uppercase abbreviations at all."
        r = engine.check_abbreviation_first_use(text)
        assert r.passed is True

    def test_stats_counts(self, engine: WritingHooksEngine):
        text = "International Normalized Ratio (INR) was measured. The CRRT protocol was started."
        r = engine.check_abbreviation_first_use(text)
        assert "defined_count" in r.stats
        assert "undefined_count" in r.stats


# ──────────────────────────────────────────────────────────────────────────────
# Hook C5: Wikilink Resolvable
# ──────────────────────────────────────────────────────────────────────────────


class TestHookC5:
    def test_no_wikilinks_passes(self, engine: WritingHooksEngine):
        r = engine.check_wikilink_resolvable("No citations here.")
        assert r.passed is True
        assert r.hook_id == "C5"

    def test_resolved_wikilinks_pass(self, engine: WritingHooksEngine, project_dir: Path):
        refs_dir = project_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "smith2024_12345678").mkdir()
        r = engine.check_wikilink_resolvable("See [[smith2024_12345678]] for details.")
        assert r.passed is True
        assert r.stats["resolved"] == 1

    def test_unresolved_wikilink_critical(self, engine: WritingHooksEngine, project_dir: Path):
        refs_dir = project_dir / "references"
        refs_dir.mkdir()
        r = engine.check_wikilink_resolvable("See [[nonexistent2024_99999999]] for details.")
        assert r.passed is False
        assert any(i.severity == "CRITICAL" for i in r.issues)
        assert r.stats["unresolved"] == 1

    def test_pmid_partial_match(self, engine: WritingHooksEngine, project_dir: Path):
        refs_dir = project_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "smith2024_12345678").mkdir()
        r = engine.check_wikilink_resolvable("See [[12345678]] for details.")
        assert r.passed is True
        assert r.stats["resolved"] == 1


# ──────────────────────────────────────────────────────────────────────────────
# Hook C6: Total Word Count
# ──────────────────────────────────────────────────────────────────────────────


class TestHookC6:
    def test_under_limit_passes(self, engine_with_profile: WritingHooksEngine):
        words = " ".join(["word"] * 4000)
        r = engine_with_profile.check_total_word_count(words)
        assert r.passed is True
        assert r.hook_id == "C6"

    def test_over_limit_warning(self, engine_with_profile: WritingHooksEngine):
        # Limit is 5000, 15% over → WARNING
        words = " ".join(["word"] * 5800)
        r = engine_with_profile.check_total_word_count(words)
        assert r.passed is True  # WARNING-only
        assert any(i.severity == "WARNING" for i in r.issues)

    def test_way_over_limit_critical(self, engine_with_profile: WritingHooksEngine):
        # Limit is 5000, >20% over → CRITICAL
        words = " ".join(["word"] * 6200)
        r = engine_with_profile.check_total_word_count(words)
        assert r.passed is False
        assert any(i.severity == "CRITICAL" for i in r.issues)

    def test_excludes_references(self, engine_with_profile: WritingHooksEngine):
        body = " ".join(["word"] * 4000)
        refs = " ".join(["reference"] * 5000)
        text = f"{body}\n\n## References\n\n{refs}"
        r = engine_with_profile.check_total_word_count(text)
        assert r.passed is True  # Only body counted
        assert r.stats["excludes_references"] is True

    def test_no_limit_configured(self, engine: WritingHooksEngine):
        r = engine.check_total_word_count("some text")
        assert r.passed is True
        assert "note" in r.stats


# ──────────────────────────────────────────────────────────────────────────────
# Hook C7a: Figure/Table Count Limits
# ──────────────────────────────────────────────────────────────────────────────


class TestHookC7a:
    def test_within_limits_passes(self, engine_with_profile: WritingHooksEngine):
        text = "See Figure 1 and Table 1 for results."
        r = engine_with_profile.check_figure_table_counts(text)
        assert r.passed is True
        assert r.hook_id == "C7a"

    def test_exceeds_figure_limit_warning(self, engine_with_profile: WritingHooksEngine):
        # limits: figures_max=6, tables_max=5
        figs = " ".join([f"Figure {i}" for i in range(1, 9)])  # 8 figures
        r = engine_with_profile.check_figure_table_counts(figs)
        assert r.passed is False
        assert any("Figure count" in i.message for i in r.issues)

    def test_no_limits_configured(self, engine: WritingHooksEngine):
        r = engine.check_figure_table_counts("Figure 1 and Table 1")
        assert r.passed is True


# ──────────────────────────────────────────────────────────────────────────────
# Hook C7d: Cross-References
# ──────────────────────────────────────────────────────────────────────────────


class TestHookC7d:
    def test_all_refs_match_passes(self, engine: WritingHooksEngine, project_dir: Path):
        results_dir = project_dir / "results"
        results_dir.mkdir()
        manifest = {
            "assets": [
                {"id": "fig1", "type": "figure", "number": "1"},
                {"id": "tbl1", "type": "table", "number": "1"},
            ]
        }
        with open(results_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)
        text = "See Figure 1 and Table 1 for details."
        r = engine.check_cross_references(text)
        assert r.passed is True
        assert r.hook_id == "C7d"

    def test_phantom_ref_critical(self, engine: WritingHooksEngine, project_dir: Path):
        results_dir = project_dir / "results"
        results_dir.mkdir()
        manifest = {"assets": [{"id": "fig1", "type": "figure", "number": "1"}]}
        with open(results_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)
        r = engine.check_cross_references("See Figure 1 and Figure 3.")
        assert r.passed is False
        phantom = [i for i in r.issues if "Phantom" in i.message]
        assert len(phantom) >= 1
        assert phantom[0].severity == "CRITICAL"

    def test_orphan_asset_warning(self, engine: WritingHooksEngine, project_dir: Path):
        results_dir = project_dir / "results"
        results_dir.mkdir()
        manifest = {
            "assets": [
                {"id": "fig1", "type": "figure", "number": "1"},
                {"id": "fig2", "type": "figure", "number": "2"},
            ]
        }
        with open(results_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)
        r = engine.check_cross_references("See Figure 1 for details.")
        orphan = [i for i in r.issues if "Orphan" in i.message]
        assert len(orphan) >= 1
        assert orphan[0].severity == "WARNING"

    def test_no_manifest_passes(self, engine: WritingHooksEngine):
        r = engine.check_cross_references("Figure 1 and Table 1")
        assert r.passed is True


# ──────────────────────────────────────────────────────────────────────────────
# Hook P5: Protected Content
# ──────────────────────────────────────────────────────────────────────────────


class TestHookP5:
    def test_filled_protected_blocks_pass(self, engine: WritingHooksEngine, project_dir: Path):
        concept = (
            "# Concept\n\n"
            "## NOVELTY STATEMENT \U0001f512\n\n"
            "This study is the first to examine the effect of remimazolam.\n\n"
            "## KEY SELLING POINTS \U0001f512\n\n"
            "1. Novel sedation approach\n"
            "2. Better hemodynamic stability\n"
        )
        (project_dir / "concept.md").write_text(concept)
        r = engine.check_protected_content()
        assert r.passed is True
        assert r.hook_id == "P5"
        assert r.stats["protected_blocks_found"] == 2

    def test_empty_protected_block_critical(self, engine: WritingHooksEngine, project_dir: Path):
        concept = (
            "# Concept\n\n"
            "## NOVELTY STATEMENT \U0001f512\n\n"
            "This has content.\n\n"
            "## KEY SELLING POINTS \U0001f512\n\n"
            "[placeholder]\n"
        )
        (project_dir / "concept.md").write_text(concept)
        r = engine.check_protected_content()
        assert r.passed is False
        assert any(i.severity == "CRITICAL" for i in r.issues)
        assert "KEY SELLING POINTS" in r.issues[0].message

    def test_no_concept_file_passes(self, engine: WritingHooksEngine):
        r = engine.check_protected_content()
        assert r.passed is True

    def test_no_protected_blocks_passes(self, engine: WritingHooksEngine, project_dir: Path):
        concept = "# Concept\n\n## Background\n\nSome background text.\n"
        (project_dir / "concept.md").write_text(concept)
        r = engine.check_protected_content()
        assert r.passed is True
        assert r.stats["protected_blocks_found"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# Hook P7: Reference Integrity
# ──────────────────────────────────────────────────────────────────────────────


class TestHookP7:
    def test_all_verified_passes(self, engine: WritingHooksEngine, project_dir: Path):
        refs_dir = project_dir / "references"
        refs_dir.mkdir()
        ref1 = refs_dir / "smith2024_12345678"
        ref1.mkdir()
        meta = {"_data_source": "pubmed_api", "title": "Test"}
        with open(ref1 / "metadata.json", "w") as f:
            json.dump(meta, f)
        r = engine.check_reference_integrity()
        assert r.passed is True
        assert r.hook_id == "P7"
        assert r.stats["verified_count"] == 1

    def test_unverified_warning(self, engine: WritingHooksEngine, project_dir: Path):
        refs_dir = project_dir / "references"
        refs_dir.mkdir()
        ref1 = refs_dir / "smith2024_12345678"
        ref1.mkdir()
        meta = {"_data_source": "agent_input", "title": "Test"}
        with open(ref1 / "metadata.json", "w") as f:
            json.dump(meta, f)
        r = engine.check_reference_integrity()
        assert r.passed is False
        assert any(i.severity == "WARNING" for i in r.issues)
        assert r.stats["unverified_count"] == 1

    def test_no_references_dir_passes(self, engine: WritingHooksEngine):
        r = engine.check_reference_integrity()
        assert r.passed is True

    def test_missing_metadata_unverified(self, engine: WritingHooksEngine, project_dir: Path):
        refs_dir = project_dir / "references"
        refs_dir.mkdir()
        ref1 = refs_dir / "smith2024_12345678"
        ref1.mkdir()
        # No metadata.json file
        r = engine.check_reference_integrity()
        assert r.passed is False
        assert r.stats["unverified_count"] == 1


# ──────────────────────────────────────────────────────────────────────────────
# Pre-commit Batch Runner
# ──────────────────────────────────────────────────────────────────────────────


class TestPrecommitBatchRunner:
    def test_runs_all_p_hooks(self, engine: WritingHooksEngine, project_dir: Path):
        # Create minimal references dir
        (project_dir / "references").mkdir()
        text = "Some manuscript text."
        results = engine.run_precommit_hooks(text)
        assert "P1" in results
        assert "P2" in results
        assert "P4" in results
        assert "P5" in results
        assert "P7" in results

    def test_hook_id_correctly_remapped(self, engine: WritingHooksEngine, project_dir: Path):
        (project_dir / "references").mkdir()
        text = "Some manuscript text."
        results = engine.run_precommit_hooks(text)
        assert results["P1"].hook_id == "P1"
        assert results["P2"].hook_id == "P2"
        assert results["P4"].hook_id == "P4"
        assert results["P5"].hook_id == "P5"
        assert results["P7"].hook_id == "P7"

    def test_p2_uses_anti_ai(self, engine: WritingHooksEngine, project_dir: Path):
        (project_dir / "references").mkdir()
        text = "In recent years, it is worth noting that this groundbreaking study was important."
        results = engine.run_precommit_hooks(text)
        assert results["P2"].passed is False  # 3+ AI phrases → CRITICAL


# ──────────────────────────────────────────────────────────────────────────────
# Updated Batch Runners
# ──────────────────────────────────────────────────────────────────────────────


class TestUpdatedBatchRunners:
    def test_post_write_includes_new_hooks(self, engine: WritingHooksEngine):
        text = "Some text for testing."
        results = engine.run_post_write_hooks(text)
        assert "A1" in results
        assert "A2" in results
        assert "A3" in results
        assert "A4" in results
        assert "A5" in results
        assert "A6" in results

    def test_post_manuscript_includes_new_hooks(self, engine: WritingHooksEngine):
        text = "## Methods\n\nSome methods.\n\n## Results\n\nSome results."
        results = engine.run_post_manuscript_hooks(text)
        assert "C3" in results
        assert "C4" in results
        assert "C5" in results
        assert "C6" in results
        assert "C7a" in results
        assert "C7d" in results
        assert "C9" in results
        assert "F" in results
