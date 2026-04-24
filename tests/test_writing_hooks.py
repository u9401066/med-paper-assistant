"""
Tests for WritingHooksEngine — Code-Enforced Hooks.

Validates:
  - A1: Word count compliance (section word count vs target)
  - A2: Citation density (wikilinks per N words)
  - A3: Anti-AI pattern detection (forbidden phrases)
  - A4: Wikilink format validation
  - A5: Language consistency (British vs American English detection)
  - A6: Overlap detection (internal paragraph similarity via n-grams)
  - A7: Reference sufficiency (saved refs >= minimum for paper type)
  - B2: Protected content post-write (delegates to P5 with B2 hook_id)
  - B8: Data-claim alignment (statistical tests, p-values, CI, software)
  - B9: Section tense consistency (Methods/Results → past tense)
  - B10: Paragraph quality (length, structure, single-sentence detection)
  - B11: Results interpretive language guard (no speculation in Results)
  - B12: Introduction funnel structure (context → gap → objective)
  - B13: Discussion structure completeness (findings, limitations, implications)
  - B14: Ethical & registration statements (IRB, consent, trial reg.)
  - B15: Hedging language density (excessive may/might/could)
  - B16: Effect size & statistical reporting (p-values, CIs, effect sizes)
  - C2: Submission checklist (required documents from journal-profile.yaml)
  - C3: N-value consistency (sample sizes across sections)
  - C4: Abbreviation first-use (defined at first occurrence)
  - C5: Wikilink resolvable (mapped to saved references)
  - C6: Total word count (manuscript total vs journal limit)
  - C7a: Figure/table count limits
  - C7d: Cross-reference orphan/phantom detection
  - C9: Supplementary cross-reference (text refs ↔ supplementary files)
  - F:  Data artifact validation (wrapper around DataArtifactTracker)
  - P5: Protected content (🔒 blocks in concept.md)
  - P6: Memory sync gate (memory file staleness check)
  - P7: Reference integrity (verified metadata)
  - Batch runners: run_post_write_hooks, run_post_section_hooks,
                   run_post_manuscript_hooks, run_precommit_hooks
"""

import json
from pathlib import Path

import pytest
import yaml

from med_paper_assistant.infrastructure.persistence.data_artifact_tracker import DataArtifactTracker
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
# Body Word Count Helpers
# ──────────────────────────────────────────────────────────────────────────────


class TestBodyWordCountHelpers:
    def test_strip_markdown_tables(self, engine: WritingHooksEngine):
        text = "Some prose.\n| col1 | col2 |\n|------|------|\n| val1 | val2 |\nMore prose."
        result = engine._strip_markdown_tables(text)
        assert "| col1 |" not in result
        assert "Some prose." in result
        assert "More prose." in result

    def test_extract_body_word_count_excludes_abstract(self, engine: WritingHooksEngine):
        text = (
            "## Abstract\n\nabstract words here\n\n"
            "## Introduction\n\nintro words here\n\n"
            "## Methods\n\nmethods words here\n\n"
            "## References\n\nref words here"
        )
        info = engine._extract_body_word_count(text)
        # Only Introduction and Methods are body
        assert info["body_words"] == 6  # "intro words here" + "methods words here"
        assert "Abstract" in info["excluded_sections"]
        assert "References" in info["excluded_sections"]
        body_names = [s["section"] for s in info["breakdown"]]
        assert "Introduction" in body_names
        assert "Methods" in body_names
        assert "Abstract" not in body_names

    def test_extract_body_excludes_tables(self, engine: WritingHooksEngine):
        text = "## Results\n\nprose text here\n| a | b |\n|---|---|\n| 1 | 2 |"
        info = engine._extract_body_word_count(text)
        assert info["body_words"] == 3  # "prose text here"

    def test_custom_body_sections_from_profile(self, tmp_path: Path):
        """Journal profile can override body sections."""
        d = tmp_path / "custom-profile"
        d.mkdir()
        (d / ".audit").mkdir()
        profile = {
            "word_limits": {"total_manuscript": 5000},
            "paper": {
                "sections": [
                    {"name": "Abstract", "word_limit": 250, "counts_toward_total": False},
                    {"name": "Introduction", "word_limit": 800, "counts_toward_total": True},
                    {"name": "Methods", "word_limit": 1500, "counts_toward_total": True},
                    {"name": "Acknowledgments", "word_limit": 200, "counts_toward_total": True},
                ],
            },
        }
        with open(d / "journal-profile.yaml", "w") as f:
            yaml.dump(profile, f)
        eng = WritingHooksEngine(d)
        text = (
            "## Abstract\n\nabstract here\n\n"
            "## Introduction\n\nintro here\n\n"
            "## Methods\n\nmethods here\n\n"
            "## Acknowledgments\n\nacknowledge here"
        )
        info = eng._extract_body_word_count(text)
        body_names = [s["section"] for s in info["breakdown"]]
        assert "Introduction" in body_names
        assert "Methods" in body_names
        assert "Acknowledgments" in body_names  # custom override
        assert "Abstract" not in body_names


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

    def test_journal_profile_locale_en_gb_prefers_british(self, project_dir: Path):
        (project_dir / "journal-profile.yaml").write_text(
            yaml.dump({"locale": "en-GB", "journal": {"name": "British Journal of Anaesthesia"}}),
            encoding="utf-8",
        )
        engine = WritingHooksEngine(project_dir)
        text = "The randomised trial analysed paediatric anaesthesia outcomes."

        r = engine.check_language_consistency(text, prefer="american")

        assert r.passed is True
        assert r.stats["preferred_variant"] == "british"


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


class TestHookC14:
    def test_strong_claim_without_evidence_is_critical(self, engine: WritingHooksEngine):
        text = "This approach fundamentally changes the geometry of transnasal airway rescue."

        r = engine.check_claim_evidence_alignment(text)

        assert r.passed is False
        assert any(issue.hook_id == "C14" and issue.severity == "CRITICAL" for issue in r.issues)
        assert r.stats["by_claim_type"]["magnitude"] == 1

    def test_strong_claim_with_citation_passes(self, engine: WritingHooksEngine):
        text = (
            "This approach fundamentally changes the geometry of transnasal airway rescue "
            "in selected patients [@wang2022_36424554]."
        )

        r = engine.check_claim_evidence_alignment(text)

        assert r.passed is True
        assert r.stats["strong_claims_without_evidence"] == 0

    def test_claim_type_severity_distinguishes_causality_and_magnitude(
        self, engine: WritingHooksEngine
    ):
        causal = engine.check_claim_evidence_alignment("This directly proves causality.")
        hedgy = engine.check_claim_evidence_alignment("The effect was dramatically larger.")

        assert causal.passed is False
        assert causal.stats["by_claim_type"]["causality"] >= 1
        assert any(issue.severity == "CRITICAL" for issue in causal.issues)
        assert hedgy.passed is True
        assert hedgy.stats["by_claim_type"]["magnitude"] == 1
        assert any(issue.severity == "WARNING" for issue in hedgy.issues)


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

    def test_missing_asset_review_receipt_is_reported(
        self, engine: WritingHooksEngine, project_dir: Path
    ):
        """Figure/table captions without review receipts should fail Hook F."""
        results_dir = project_dir / "results"
        (results_dir / "figures").mkdir(parents=True)
        (results_dir / "figures" / "outcome.png").write_bytes(b"png")
        (results_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "figures": [
                        {
                            "number": 1,
                            "filename": "outcome.png",
                            "caption": "Primary outcome by treatment arm",
                        }
                    ],
                    "tables": [],
                }
            )
        )

        tracker = DataArtifactTracker(project_dir / ".audit", project_dir)
        tracker.record_artifact(
            tool_name="create_plot",
            artifact_type="figure",
            parameters={"plot_type": "bar"},
            output_path="results/figures/outcome.png",
            data_source="study.csv",
            provenance_code="print('plot')",
        )

        r = engine.validate_data_artifacts("See Figure 1 for the primary outcome.")
        assert r.passed is False
        assert any(i.hook_id == "F1" and "review receipt" in i.message for i in r.issues)

    def test_user_manifest_schema_is_recognised(self, project_dir: Path):
        """Root data-artifacts.yaml plus data-artifacts/manifest.yaml should be accepted."""
        (project_dir / "results" / "figures").mkdir(parents=True)
        (project_dir / "results" / "figures" / "flow.png").write_bytes(b"png")
        (project_dir / "data-artifacts").mkdir()
        (project_dir / "data-artifacts" / "manifest.yaml").write_text(
            yaml.dump(
                {
                    "figures": [
                        {
                            "number": 1,
                            "filename": "flow.png",
                            "caption": "Participant flow diagram",
                        }
                    ],
                    "tables": [],
                }
            ),
            encoding="utf-8",
        )
        (project_dir / "data-artifacts.yaml").write_text(
            yaml.dump(
                {
                    "figures": [
                        {
                            "filename": "flow.png",
                            "caption": "Participant flow diagram",
                            "output_path": "results/figures/flow.png",
                            "provenance_code": "print('manual manifest')",
                        }
                    ],
                    "asset_reviews": [
                        {
                            "asset_type": "figure",
                            "asset_path": "results/figures/flow.png",
                            "observations": ["Two-arm flow", "Counts are shown"],
                            "rationale": "Caption matches the displayed flow.",
                            "proposed_caption": "Participant flow diagram",
                            "timestamp": "2026-04-23T00:00:00",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        tracker = DataArtifactTracker(project_dir / ".audit", project_dir)
        validation = tracker.validate_cross_references("See Figure 1.")

        assert validation["summary"]["total_artifacts"] == 1
        assert validation["summary"]["manifest_figures"] == 1
        assert not any(i["category"] == "phantom_reference" for i in validation["issues"])

    def test_data_anchor_without_primary_provenance_is_critical(
        self, engine: WritingHooksEngine, project_dir: Path
    ):
        """Data anchors cannot be trusted when they only come from agent/concept inference."""
        (project_dir / "data-artifacts.yaml").write_text(
            yaml.dump(
                {
                    "data_anchors": {
                        "screened": {
                            "value": 112,
                            "source": "concept.md agent inference",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        r = engine.validate_data_artifacts("We screened 112 patients.")

        assert r.passed is False
        assert r.stats["data_anchors"] == 1
        assert any(
            issue.hook_id == "F4" and "agent/generated source" in issue.message
            for issue in r.issues
        )

    def test_data_anchor_pending_asset_aware_source_is_critical(
        self, engine: WritingHooksEngine, project_dir: Path
    ):
        """A scanned DOCX must be ingested before its numbers can back data anchors."""
        (project_dir / ".audit" / "source-materials.yaml").write_text(
            yaml.dump(
                {
                    "schema": "mdpaper.source_materials.v1",
                    "materials": [
                        {
                            "id": "source-001",
                            "filename": "20240112 table.docx",
                            "relative_path": "20240112 table.docx",
                            "ingestion": {
                                "status": "pending_asset_aware",
                                "required": True,
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (project_dir / "data-artifacts.yaml").write_text(
            yaml.dump(
                {
                    "data_anchors": {
                        "screened": {
                            "value": 112,
                            "source_material_id": "source-001",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        r = engine.validate_data_artifacts("We screened 112 patients.")

        assert r.passed is False
        assert any(
            issue.hook_id == "F4" and "requires asset-aware ingestion" in issue.message
            for issue in r.issues
        )

    def test_data_anchor_with_ready_source_material_passes(
        self, engine: WritingHooksEngine, project_dir: Path
    ):
        """Ready/native source materials can support numeric data anchors."""
        (project_dir / ".audit" / "source-materials.yaml").write_text(
            yaml.dump(
                {
                    "schema": "mdpaper.source_materials.v1",
                    "materials": [
                        {
                            "id": "source-001",
                            "filename": "screening.csv",
                            "relative_path": "data/screening.csv",
                            "ingestion": {
                                "status": "ready_for_context",
                                "required": False,
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (project_dir / "data-artifacts.yaml").write_text(
            yaml.dump(
                {
                    "data_anchors": {
                        "screened": {
                            "value": 112,
                            "source_material_id": "source-001",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        r = engine.validate_data_artifacts("We screened 112 patients.")

        assert r.passed is True
        assert r.stats["data_anchors"] == 1


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

    def test_filler_phrase_detected(self, engine: WritingHooksEngine):
        text = "In order to understand the results, due to the fact that the data was limited."
        r = engine.check_anti_ai_patterns(text)
        assert r.stats["total_matches"] >= 1

    def test_chatbot_artifact_detected(self, engine: WritingHooksEngine):
        text = "The results were significant. I hope this helps with your understanding."
        r = engine.check_anti_ai_patterns(text)
        assert r.stats["total_matches"] >= 1

    def test_generic_conclusion_detected(self, engine: WritingHooksEngine):
        text = "The future looks bright for this therapy. Exciting times lie ahead."
        r = engine.check_anti_ai_patterns(text)
        assert r.stats["total_matches"] >= 2

    def test_copula_avoidance_phrase_detected(self, engine: WritingHooksEngine):
        text = "This method serves as a foundation. The result stands as a benchmark."
        r = engine.check_anti_ai_patterns(text)
        assert r.stats["total_matches"] >= 2

    def test_significance_inflation_detected(self, engine: WritingHooksEngine):
        text = "This left an indelible mark on the field and its evolving landscape."
        r = engine.check_anti_ai_patterns(text)
        assert r.stats["total_matches"] >= 2


# ──────────────────────────────────────────────────────────────────────────────
# Hook A3b: Structural AI Writing Signals (new checks 6-9)
# ──────────────────────────────────────────────────────────────────────────────


class TestHookA3bExtended:
    """Tests for the new humanizer-based structural checks added to A3b."""

    def _make_long_text(self, base: str, repeat: int = 30) -> str:
        """Create text long enough to pass the 200-char minimum."""
        return (base + " ") * repeat

    def test_negative_parallelism_warning(self, engine: WritingHooksEngine):
        text = self._make_long_text(
            "This approach is not just effective, it's revolutionary. "
            "The method is not only fast, but also accurate. "
            "The drug is not merely safe, but transformative. "
            "Results show improvement."
        )
        r = engine.check_ai_writing_signals(text)
        assert r.stats["neg_parallelism_count"] >= 3
        assert any("parallelism" in i.message.lower() for i in r.issues)

    def test_negative_parallelism_low_count_ok(self, engine: WritingHooksEngine):
        # 1 instance should not trigger warning (threshold is >2)
        filler = " ".join(["The patient showed rapid recovery."] * 25)
        text = "This approach is not just effective, it's also efficient. " + filler
        r = engine.check_ai_writing_signals(text)
        assert not any("parallelism" in i.message.lower() for i in r.issues)

    def test_copula_avoidance_warning(self, engine: WritingHooksEngine):
        text = self._make_long_text(
            "The hospital serves as a referral center. "
            "This drug functions as an antagonist. "
            "The protocol stands as a model. "
            "ECMO acts as life support."
        )
        r = engine.check_ai_writing_signals(text)
        assert r.stats["copula_avoidance_count"] >= 4
        assert any("copula" in i.message.lower() for i in r.issues)

    def test_em_dash_overuse_warning(self, engine: WritingHooksEngine):
        text = self._make_long_text(
            "The drug — a novel compound — showed efficacy. "
            "Patients — both young and old — responded well. "
            "The protocol — designed carefully — reduced errors. "
        )
        r = engine.check_ai_writing_signals(text)
        assert r.stats["em_dash_count"] >= 6

    def test_em_dash_normal_ok(self, engine: WritingHooksEngine):
        filler = " ".join(["Patients recovered quickly."] * 25)
        text = (
            "The results were significant. "
            "One notable finding — the rapid onset — was unexpected. " + filler
        )
        r = engine.check_ai_writing_signals(text)
        assert not any("em dash" in i.message.lower() for i in r.issues)

    def test_false_range_warning(self, engine: WritingHooksEngine):
        text = self._make_long_text(
            "The impact ranges from clinical to administrative. "
            "From surgery to rehabilitation, care must be holistic. "
            "Outcomes vary from excellent to poor. "
            "Benefits span from cost savings to quality improvement. "
            "Issues range from staffing to equipment. "
        )
        r = engine.check_ai_writing_signals(text)
        assert r.stats["false_range_count"] >= 5

    def test_stats_contain_new_fields(self, engine: WritingHooksEngine):
        text = self._make_long_text("Normal academic text with varied sentences.")
        r = engine.check_ai_writing_signals(text)
        assert "neg_parallelism_count" in r.stats
        assert "copula_avoidance_count" in r.stats
        assert "em_dash_count" in r.stats
        assert "false_range_count" in r.stats


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
        # Build body sections summing to ~4000 words (under 5000 limit)
        intro = " ".join(["word"] * 800)
        methods = " ".join(["word"] * 1200)
        results = " ".join(["word"] * 1200)
        discussion = " ".join(["word"] * 800)
        text = f"## Introduction\n\n{intro}\n\n## Methods\n\n{methods}\n\n## Results\n\n{results}\n\n## Discussion\n\n{discussion}"
        r = engine_with_profile.check_total_word_count(text)
        assert r.passed is True
        assert r.hook_id == "C6"

    def test_over_limit_warning(self, engine_with_profile: WritingHooksEngine):
        # Limit is 5000, 15% over → WARNING
        intro = " ".join(["word"] * 1500)
        methods = " ".join(["word"] * 1500)
        results = " ".join(["word"] * 1500)
        discussion = " ".join(["word"] * 1300)
        text = f"## Introduction\n\n{intro}\n\n## Methods\n\n{methods}\n\n## Results\n\n{results}\n\n## Discussion\n\n{discussion}"
        r = engine_with_profile.check_total_word_count(text)
        assert r.passed is True  # WARNING-only
        assert any(i.severity == "WARNING" for i in r.issues)

    def test_way_over_limit_critical(self, engine_with_profile: WritingHooksEngine):
        # Limit is 5000, >20% over → CRITICAL
        intro = " ".join(["word"] * 2000)
        methods = " ".join(["word"] * 1500)
        results = " ".join(["word"] * 1500)
        discussion = " ".join(["word"] * 1500)
        text = f"## Introduction\n\n{intro}\n\n## Methods\n\n{methods}\n\n## Results\n\n{results}\n\n## Discussion\n\n{discussion}"
        r = engine_with_profile.check_total_word_count(text)
        assert r.passed is False
        assert any(i.severity == "CRITICAL" for i in r.issues)

    def test_excludes_abstract_and_references(self, engine_with_profile: WritingHooksEngine):
        """Body = Intro+Methods+Results+Discussion only. Abstract & References excluded."""
        abstract = " ".join(["abstract_word"] * 3000)
        body = " ".join(["word"] * 1000)
        refs = " ".join(["reference"] * 5000)
        text = (
            f"## Abstract\n\n{abstract}\n\n"
            f"## Introduction\n\n{body}\n\n"
            f"## Methods\n\n{body}\n\n"
            f"## Results\n\n{body}\n\n"
            f"## Discussion\n\n{body}\n\n"
            f"## References\n\n{refs}"
        )
        r = engine_with_profile.check_total_word_count(text)
        assert r.passed is True  # Only 4000 body words, under 5000 limit
        assert r.stats["body_words"] == 4000
        assert "Abstract" in r.stats["excluded_sections"]
        assert "References" in r.stats["excluded_sections"]
        assert r.stats["counting_method"] == "body_only (ICMJE convention)"

    def test_excludes_tables_from_word_count(self, engine_with_profile: WritingHooksEngine):
        """Markdown tables are display items and should not count."""
        table_rows = "| col1 | col2 |\n|------|------|\n| val1 | val2 |\n" * 500
        prose = " ".join(["word"] * 1000)
        text = (
            f"## Introduction\n\n{prose}\n\n"
            f"## Methods\n\n{prose}\n\n"
            f"## Results\n\n{prose}\n{table_rows}\n\n"
            f"## Discussion\n\n{prose}"
        )
        r = engine_with_profile.check_total_word_count(text)
        # Should be ~4000 words from prose; tables not counted
        assert r.stats["body_words"] == 4000

    def test_no_limit_configured(self, engine: WritingHooksEngine):
        r = engine.check_total_word_count("## Introduction\n\nsome text")
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
# Hook C7b: Asset Plan Coverage
# ──────────────────────────────────────────────────────────────────────────────


class TestHookC7b:
    def test_missing_planned_asset_is_critical(self, engine: WritingHooksEngine, project_dir: Path):
        (project_dir / "manuscript-plan.yaml").write_text(
            yaml.dump(
                {
                    "asset_plan": [
                        {
                            "id": "fig-1",
                            "type": "flow_diagram",
                            "section": "Methods",
                            "caption": "Study flow diagram",
                        }
                    ]
                }
            )
        )

        text = "## Methods\n\nSee Figure 1.\n\n## Results\n\ntext"
        r = engine.check_asset_plan_coverage(text)
        assert r.passed is False
        assert any("missing from manifest.json" in issue.message for issue in r.issues)

    def test_missing_exportable_companion_is_critical(
        self,
        engine: WritingHooksEngine,
        project_dir: Path,
    ):
        results_dir = project_dir / "results"
        (results_dir / "figures").mkdir(parents=True)
        (results_dir / "figures" / "study-flow.drawio").write_text("xml")
        (results_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "figures": [
                        {
                            "number": 1,
                            "filename": "study-flow.drawio",
                            "caption": "Study flow diagram",
                        }
                    ]
                }
            )
        )
        (project_dir / "manuscript-plan.yaml").write_text(
            yaml.dump(
                {
                    "asset_plan": [
                        {
                            "id": "fig-1",
                            "type": "flow_diagram",
                            "section": "Methods",
                            "caption": "Study flow diagram",
                        }
                    ]
                }
            )
        )

        text = (
            "## Methods\n\n"
            "![Figure 1. Study flow diagram](../results/figures/study-flow.drawio)\n\n"
            "**Figure 1.** Study flow diagram\n\n"
            "See Figure 1.\n\n"
            "## Results\n\ntext"
        )
        r = engine.check_asset_plan_coverage(text)
        assert r.passed is False
        assert any("lacks an exportable rendered asset" in issue.message for issue in r.issues)

    def test_registered_and_placed_assets_pass(self, engine: WritingHooksEngine, project_dir: Path):
        results_dir = project_dir / "results"
        (results_dir / "figures").mkdir(parents=True)
        (results_dir / "tables").mkdir(parents=True)
        (results_dir / "figures" / "study-flow.drawio").write_text("xml")
        (results_dir / "figures" / "study-flow.png").write_bytes(b"png")
        (results_dir / "tables" / "baseline.md").write_text("| a | b |")
        (results_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "figures": [
                        {
                            "number": 1,
                            "filename": "study-flow.drawio",
                            "caption": "Study flow diagram",
                        }
                    ],
                    "tables": [
                        {
                            "number": 1,
                            "filename": "baseline.md",
                            "caption": "Baseline characteristics of study participants",
                        }
                    ],
                }
            )
        )
        (project_dir / "manuscript-plan.yaml").write_text(
            yaml.dump(
                {
                    "asset_plan": [
                        {
                            "id": "fig-1",
                            "type": "flow_diagram",
                            "section": "Methods",
                            "caption": "Study flow diagram",
                        },
                        {
                            "id": "table-1",
                            "type": "table_one",
                            "section": "Results",
                            "caption": "Baseline characteristics of study participants",
                        },
                    ]
                }
            )
        )

        text = (
            "## Methods\n\n"
            "![Figure 1. Study flow diagram](../results/figures/study-flow.png)\n\n"
            "**Figure 1.** Study flow diagram\n\n"
            "See Figure 1.\n\n"
            "## Results\n\n"
            "**Table 1.** Baseline characteristics of study participants\n\n"
            "See Table 1 for baseline characteristics."
        )
        r = engine.check_asset_plan_coverage(text)
        assert r.passed is True
        assert r.stats["required_assets"] == 2
        assert r.stats["manifest_matches"] == 2


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
        (project_dir / "concept.md").write_text(concept, encoding="utf-8")
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
        (project_dir / "concept.md").write_text(concept, encoding="utf-8")
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
        assert "P6" in results
        assert "P7" in results

    def test_hook_id_correctly_remapped(self, engine: WritingHooksEngine, project_dir: Path):
        (project_dir / "references").mkdir()
        text = "Some manuscript text."
        results = engine.run_precommit_hooks(text)
        assert results["P1"].hook_id == "P1"
        assert results["P2"].hook_id == "P2"
        assert results["P4"].hook_id == "P4"
        assert results["P5"].hook_id == "P5"
        assert results["P6"].hook_id == "P6"
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
        assert "A7" in results
        assert "B2" in results

    def test_post_manuscript_includes_new_hooks(self, engine: WritingHooksEngine):
        text = "## Methods\n\nSome methods.\n\n## Results\n\nSome results."
        results = engine.run_post_manuscript_hooks(text)
        assert "C2" in results
        assert "C3" in results
        assert "C4" in results
        assert "C5" in results
        assert "C6" in results
        assert "C7a" in results
        assert "C7b" in results
        assert "C7d" in results
        assert "C9" in results
        assert "F" in results


# ──────────────────────────────────────────────────────────────────────────────
# G9: Git Status Check
# ──────────────────────────────────────────────────────────────────────────────


class TestGitStatusCheck:
    """G9: Code-Enforced git status hook."""

    def test_no_git_dir(self, engine: WritingHooksEngine):
        """No .git directory → WARNING, still passes."""
        r = engine.check_git_status()
        assert r.hook_id == "G9"
        assert r.passed is True
        assert any(i.severity == "WARNING" and ".git" in i.message for i in r.issues)

    def test_clean_repo(self, tmp_path: Path):
        """Clean git repo → PASS, no issues."""
        import subprocess

        repo = tmp_path / "clean-repo"
        repo.mkdir()
        (repo / ".audit").mkdir()
        subprocess.run(["git", "init"], cwd=str(repo), capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"], cwd=str(repo), capture_output=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo), capture_output=True)
        (repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo), capture_output=True)

        e = WritingHooksEngine(repo)
        r = e.check_git_status()
        assert r.hook_id == "G9"
        assert r.passed is True
        assert r.stats["dirty_files"] == 0

    def test_dirty_repo(self, tmp_path: Path):
        """Uncommitted files → WARNING, passes for paper-first workflows."""
        import subprocess

        repo = tmp_path / "dirty-repo"
        repo.mkdir()
        (repo / ".audit").mkdir()
        subprocess.run(["git", "init"], cwd=str(repo), capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"], cwd=str(repo), capture_output=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo), capture_output=True)
        (repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo), capture_output=True)

        # Create dirty file
        (repo / "dirty.txt").write_text("uncommitted")

        e = WritingHooksEngine(repo)
        r = e.check_git_status()
        assert r.hook_id == "G9"
        assert r.passed is True
        assert r.stats["dirty_files"] >= 1
        assert any(i.severity == "WARNING" and "uncommitted" in i.message for i in r.issues)

    def test_git_not_found(self, engine: WritingHooksEngine):
        """Git command not available → WARNING, passes."""
        from unittest.mock import patch as mock_patch

        with mock_patch(
            "subprocess.run",
            side_effect=FileNotFoundError("git not found"),
        ):
            # Need a .git dir so we get past the dir check
            (engine._project_dir / ".git").mkdir(exist_ok=True)
            r = engine.check_git_status()
            assert r.passed is True
            assert any(i.severity == "WARNING" for i in r.issues)


# ──────────────────────────────────────────────────────────────────────────────
# Hook B9: Section Tense Consistency
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckSectionTense:
    """Tests for check_section_tense (B9)."""

    def test_past_tense_methods_passes(self, engine: WritingHooksEngine):
        """Methods written in past tense → PASS."""
        content = (
            "We measured blood pressure every 4 hours. Patients received the intervention on day 1."
        )
        r = engine.check_section_tense(content, section="Methods")
        assert r.hook_id == "B9"
        assert r.passed is True
        assert len(r.issues) == 0

    def test_present_tense_methods_fails(self, engine: WritingHooksEngine):
        """Methods using present tense study verbs → issues."""
        content = "We measure blood pressure. We analyze the data using SPSS. We collect samples every morning."
        r = engine.check_section_tense(content, section="Methods")
        assert r.hook_id == "B9"
        assert r.stats["present_verbs"] >= 2
        assert any("past tense" in i.message.lower() for i in r.issues)

    def test_present_tense_results_fails(self, engine: WritingHooksEngine):
        """Results using present tense → issues."""
        content = "The result shows a significant difference. The analysis indicates a trend. The data demonstrate efficacy."
        r = engine.check_section_tense(content, section="Results")
        assert r.hook_id == "B9"
        assert len(r.issues) >= 1

    def test_non_target_section_no_issues(self, engine: WritingHooksEngine):
        """Introduction section → no tense issues raised."""
        content = "We analyze data regularly in clinical settings."
        r = engine.check_section_tense(content, section="Introduction")
        assert r.passed is True
        assert len(r.issues) == 0


# ──────────────────────────────────────────────────────────────────────────────
# Hook B10: Paragraph Quality
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckParagraphQuality:
    """Tests for check_paragraph_quality (B10)."""

    def test_normal_paragraphs_pass(self, engine: WritingHooksEngine):
        """Well-structured paragraphs → PASS."""
        content = "This is the first sentence. This is the second sentence. And this is the third.\n\nAnother paragraph here. With two sentences."
        r = engine.check_paragraph_quality(content, section="Methods")
        assert r.hook_id == "B10"
        assert r.passed is True

    def test_very_long_paragraph_warns(self, engine: WritingHooksEngine):
        """Paragraph > 250 words → WARNING."""
        # Generate a long paragraph
        long_para = " ".join(["This is a test sentence with several words."] * 40)
        r = engine.check_paragraph_quality(long_para, section="Introduction")
        assert any(i.severity == "WARNING" and "long" in i.message.lower() for i in r.issues)

    def test_single_sentence_paragraph_info(self, engine: WritingHooksEngine):
        """Single-sentence paragraph in non-Results section → INFO."""
        content = "This is a standalone sentence that forms its own paragraph and has enough words."
        r = engine.check_paragraph_quality(content, section="Discussion")
        assert any(i.severity == "INFO" for i in r.issues)


# ──────────────────────────────────────────────────────────────────────────────
# Hook B11: Results Interpretive Language Guard
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckResultsInterpretation:
    """Tests for check_results_interpretation (B11)."""

    def test_objective_results_pass(self, engine: WritingHooksEngine):
        """Objective results text → PASS."""
        content = "## Results\n\nThe mean age was 65.2 years. Blood pressure was significantly lower in the treatment group (p = 0.003)."
        r = engine.check_results_interpretation(content)
        assert r.hook_id == "B11"
        assert r.passed is True

    def test_interpretive_language_detected(self, engine: WritingHooksEngine):
        """Interpretive language in Results → issues."""
        content = "## Results\n\nThe decrease in blood pressure, suggesting that the drug is effective, was observed. Interestingly, the older group showed better outcomes. This finding implies a dose-response relationship."
        r = engine.check_results_interpretation(content)
        assert r.hook_id == "B11"
        assert r.stats["interpretive_count"] >= 2
        assert len(r.issues) >= 1

    def test_no_results_section_passes(self, engine: WritingHooksEngine):
        """No Results section → PASS (nothing to check)."""
        content = "## Introduction\n\nSome text here suggesting interesting patterns."
        r = engine.check_results_interpretation(content)
        assert r.passed is True

    def test_speculative_language_caught(self, engine: WritingHooksEngine):
        """'We believe', 'possibly' in Results → caught."""
        content = "## Results\n\nThe effect was possibly due to age. We believe these outcomes reflect true efficacy."
        r = engine.check_results_interpretation(content)
        assert r.stats["interpretive_count"] >= 1


# ──────────────────────────────────────────────────────────────────────────────
# Hook B12: Introduction Funnel Structure
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckIntroStructure:
    """Tests for check_intro_structure (B12)."""

    def test_complete_intro_passes(self, engine: WritingHooksEngine):
        """Well-structured Introduction → mostly PASS."""
        content = """## Introduction

Diabetes is a leading cause of morbidity worldwide, affecting approximately 463 million people globally.

Several studies have examined the role of intensive insulin therapy [[smith2020_12345678]]. Prior randomized trials demonstrated modest improvements in glycemic control [[jones2021_23456789]].

However, no study has examined the long-term effects of this approach in elderly populations. The optimal dosing regimen remains unclear.

This study aimed to evaluate the efficacy and safety of intensive insulin therapy in patients over 75 years of age.
"""
        r = engine.check_intro_structure(content)
        assert r.hook_id == "B12"
        assert r.stats.get("has_objective") is True
        assert r.stats.get("has_gap_statement") is True

    def test_missing_objective_warns(self, engine: WritingHooksEngine):
        """No objective statement in last paragraph → WARNING."""
        content = """## Introduction

Some background context about the disease.

More background with evidence.

However, no prior study exists.

This is a general conclusion without any aim or objective statement.
"""
        r = engine.check_intro_structure(content)
        # Should warn about missing objective
        assert any("objective" in i.message.lower() for i in r.issues)

    def test_results_preview_fails(self, engine: WritingHooksEngine):
        """Results mentioned in Introduction → CRITICAL."""
        content = """## Introduction

Some context.

We found that the treatment significantly reduced mortality.

This study aimed to investigate the treatment.
"""
        r = engine.check_intro_structure(content)
        assert r.passed is False
        assert any(i.severity == "CRITICAL" and "results" in i.message.lower() for i in r.issues)

    def test_too_few_paragraphs_warns(self, engine: WritingHooksEngine):
        """Introduction with only 1-2 paragraphs → WARNING."""
        content = """## Introduction

Very short introduction with just one paragraph about the topic. We aimed to study this.
"""
        r = engine.check_intro_structure(content)
        assert any("paragraph" in i.message.lower() for i in r.issues)


# ──────────────────────────────────────────────────────────────────────────────
# Hook B13: Discussion Structure Completeness
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckDiscussionStructure:
    """Tests for check_discussion_structure (B13)."""

    def test_complete_discussion_passes(self, engine: WritingHooksEngine):
        """Discussion with all required elements → PASS."""
        content = """## Discussion

Our study demonstrated that intensive therapy improved outcomes significantly. The principal finding was a 30% reduction in mortality.

Consistent with Smith et al. [[smith2020_12345678]], we observed similar trends. Jones et al. [[jones2021_23456789]] reported comparable results. In contrast to Lee et al. [[lee2022_34567890]], our findings suggest a stronger effect.

These findings have important clinical implications. The approach may improve patient outcomes in routine practice. Future studies should examine long-term adherence.

This study has several limitations. First, the single-center design limits generalizability. Second, the relatively small sample size may reduce statistical power.

In conclusion, intensive therapy appears to be a promising approach.
"""
        r = engine.check_discussion_structure(content)
        assert r.hook_id == "B13"
        assert r.passed is True
        assert r.stats.get("has_limitations") is True

    def test_missing_limitations_critical(self, engine: WritingHooksEngine):
        """Discussion without limitations → CRITICAL."""
        content = """## Discussion

Our study found significant improvements.

This is consistent with prior literature [[smith2020_12345678]] [[jones2021_23456789]] [[lee2022_34567890]].

The clinical implications are broad. Future research should expand on this approach.
"""
        r = engine.check_discussion_structure(content)
        assert r.passed is False
        assert any(i.severity == "CRITICAL" and "limitation" in i.message.lower() for i in r.issues)

    def test_few_citations_warns(self, engine: WritingHooksEngine):
        """Discussion with < 3 citations → WARNING."""
        content = """## Discussion

Our study demonstrated improvement. This study has several limitations including small sample size.
"""
        r = engine.check_discussion_structure(content)
        assert any("citation" in i.message.lower() for i in r.issues)


# ──────────────────────────────────────────────────────────────────────────────
# Hook B14: Ethical & Registration Statements
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckEthicalStatements:
    """Tests for check_ethical_statements (B14)."""

    def test_complete_ethics_passes(self, engine: WritingHooksEngine):
        """Ethics + consent + registration present → PASS."""
        content = """## Methods

This study was approved by the Institutional Review Board of XYZ Hospital (approval no. 2024-001).
Written informed consent was obtained from all participants.
This randomized trial was registered at ClinicalTrials.gov (NCT12345678).
"""
        r = engine.check_ethical_statements(content)
        assert r.hook_id == "B14"
        assert r.passed is True

    def test_missing_ethics_critical(self, engine: WritingHooksEngine):
        """No ethics statement → CRITICAL."""
        content = "We performed a retrospective chart review of 100 patients."
        r = engine.check_ethical_statements(content)
        assert r.passed is False
        assert any(i.severity == "CRITICAL" and "ethical" in i.message.lower() for i in r.issues)

    def test_missing_consent_warns(self, engine: WritingHooksEngine):
        """Ethics present but no consent → WARNING."""
        content = "This study was approved by the ethics committee of University Hospital."
        r = engine.check_ethical_statements(content)
        assert any("consent" in i.message.lower() for i in r.issues)

    def test_rct_without_registration_critical(self, engine: WritingHooksEngine):
        """Randomized trial without registration → CRITICAL."""
        content = """This was approved by the IRB. Written informed consent was obtained.
Patients were randomized to treatment or placebo in a 1:1 ratio."""
        r = engine.check_ethical_statements(content)
        assert r.passed is False
        assert any("registration" in i.message.lower() for i in r.issues)

    def test_consent_waiver_accepted(self, engine: WritingHooksEngine):
        """Consent waiver is acceptable."""
        content = """This study was approved by the IRB. The requirement for informed consent was waived due to the retrospective design."""
        r = engine.check_ethical_statements(content)
        assert r.stats.get("has_informed_consent") is True


# ──────────────────────────────────────────────────────────────────────────────
# Hook B15: Hedging Language Density
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckHedgingDensity:
    """Tests for check_hedging_density (B15)."""

    def test_minimal_hedging_passes(self, engine: WritingHooksEngine):
        """Text with minimal hedging → PASS."""
        content = (
            "The treatment reduced mortality by 30%. Blood pressure was lower in the intervention group. Results were statistically significant. "
            * 10
        )
        r = engine.check_hedging_density(content)
        assert r.hook_id == "B15"
        assert r.passed is True

    def test_excessive_hedging_fails(self, engine: WritingHooksEngine):
        """Text saturated with hedging → CRITICAL."""
        content = (
            "This may be important. It could have implications. Perhaps the treatment might be effective. It appears to suggest benefit. "
            * 10
        )
        r = engine.check_hedging_density(content)
        assert not r.passed or any(i.severity in ("WARNING", "CRITICAL") for i in r.issues)
        assert r.stats["hedge_count"] >= 5

    def test_short_text_skipped(self, engine: WritingHooksEngine):
        """Very short text (< 100 words) → skipped, PASS."""
        content = "May be. Could be. Possibly perhaps."
        r = engine.check_hedging_density(content)
        assert r.passed is True  # Too short to evaluate


# ──────────────────────────────────────────────────────────────────────────────
# Hook B16: Effect Size & Statistical Reporting
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckEffectSizeReporting:
    """Tests for check_effect_size_reporting (B16)."""

    def test_complete_reporting_passes(self, engine: WritingHooksEngine):
        """Proper stats with effect size + CI → PASS."""
        content = """## Results

The odds ratio was OR = 2.3, 95% CI 1.2-4.5, p = 0.013. The hazard ratio was HR = 0.72, 95% CI 0.55-0.94, p = 0.016.
"""
        r = engine.check_effect_size_reporting(content)
        assert r.hook_id == "B16"
        assert r.passed is True
        assert r.stats["effect_size_count"] >= 2

    def test_p_zero_critical(self, engine: WritingHooksEngine):
        """p = 0.000 is statistically incorrect → CRITICAL."""
        content = "## Results\n\nThe difference was significant (p = 0.000)."
        r = engine.check_effect_size_reporting(content)
        assert r.passed is False
        assert any(i.severity == "CRITICAL" and "0.000" in i.message for i in r.issues)

    def test_p_values_without_effect_size_warns(self, engine: WritingHooksEngine):
        """Many p-values but no effect sizes → WARNING."""
        content = "## Results\n\nGroup A vs B (p = 0.003). Variable X was significant (p = 0.012). Variable Y was also significant (p = 0.045)."
        r = engine.check_effect_size_reporting(content)
        assert any("effect size" in i.message.lower() for i in r.issues)

    def test_effect_size_without_ci_warns(self, engine: WritingHooksEngine):
        """Effect sizes present but no CI → WARNING."""
        content = "## Results\n\nThe odds ratio was OR = 2.3. Another analysis showed HR = 0.85."
        r = engine.check_effect_size_reporting(content)
        assert any("confidence interval" in i.message.lower() for i in r.issues)

    def test_no_results_section_passes(self, engine: WritingHooksEngine):
        """No Results section → PASS."""
        content = "## Introduction\n\nSome text with p = 0.05."
        r = engine.check_effect_size_reporting(content)
        assert r.passed is True


# ──────────────────────────────────────────────────────────────────────────────
# A7: Reference Sufficiency
# ──────────────────────────────────────────────────────────────────────────────


class TestA7ReferenceSufficiency:
    """Tests for Hook A7 — Code-Enforced reference count minimum."""

    def test_pass_with_sufficient_refs(self, project_dir: Path):
        """A7 passes when saved references >= minimum."""
        refs = project_dir / "references"
        refs.mkdir()
        for i in range(20):
            rd = refs / f"ref_{i}"
            rd.mkdir()
            (rd / "metadata.json").write_text("{}")
        engine = WritingHooksEngine(project_dir)
        r = engine.check_reference_sufficiency()
        assert r.passed is True
        assert r.hook_id == "A7"
        assert any("met" in i.message for i in r.issues)

    def test_fail_with_insufficient_refs(self, project_dir: Path):
        """A7 fails (CRITICAL) when saved references < minimum."""
        refs = project_dir / "references"
        refs.mkdir()
        for i in range(5):
            rd = refs / f"ref_{i}"
            rd.mkdir()
            (rd / "metadata.json").write_text("{}")
        engine = WritingHooksEngine(project_dir)
        r = engine.check_reference_sufficiency()
        assert r.passed is False
        assert r.hook_id == "A7"
        assert any(i.severity == "CRITICAL" for i in r.issues)
        assert any("5/20" in i.message for i in r.issues)  # default type = original-research (20)

    def test_fail_with_no_refs_dir(self, project_dir: Path):
        """A7 fails when references directory doesn't exist."""
        engine = WritingHooksEngine(project_dir)
        r = engine.check_reference_sufficiency()
        assert r.passed is False
        assert any("0/" in i.message for i in r.issues)

    def test_paper_type_original_research(self, project_dir: Path):
        """A7 uses paper-type-specific minimum (original-research = 20)."""
        profile = {"paper": {"type": "original-research"}}
        with open(project_dir / "journal-profile.yaml", "w") as f:
            yaml.dump(profile, f)
        refs = project_dir / "references"
        refs.mkdir()
        for i in range(15):
            rd = refs / f"ref_{i}"
            rd.mkdir()
            (rd / "metadata.json").write_text("{}")
        engine = WritingHooksEngine(project_dir)
        r = engine.check_reference_sufficiency()
        assert r.passed is False  # 15 < 20
        assert any("original-research" in i.message for i in r.issues)

    def test_paper_type_case_report(self, project_dir: Path):
        """A7 passes for case-report with lower minimum (8)."""
        profile = {"paper": {"type": "case-report"}}
        with open(project_dir / "journal-profile.yaml", "w") as f:
            yaml.dump(profile, f)
        refs = project_dir / "references"
        refs.mkdir()
        for i in range(8):
            rd = refs / f"ref_{i}"
            rd.mkdir()
            (rd / "metadata.json").write_text("{}")
        engine = WritingHooksEngine(project_dir)
        r = engine.check_reference_sufficiency()
        assert r.passed is True  # 8 >= 8
        assert any("case-report" in i.message for i in r.issues)

    def test_paper_type_systematic_review(self, project_dir: Path):
        """A7 systematic-review needs 40 references."""
        profile = {"paper": {"type": "systematic-review"}}
        with open(project_dir / "journal-profile.yaml", "w") as f:
            yaml.dump(profile, f)
        refs = project_dir / "references"
        refs.mkdir()
        for i in range(30):
            rd = refs / f"ref_{i}"
            rd.mkdir()
            (rd / "metadata.json").write_text("{}")
        engine = WritingHooksEngine(project_dir)
        r = engine.check_reference_sufficiency()
        assert r.passed is False  # 30 < 40
        assert any("need 10 more" in i.message for i in r.issues)

    def test_legacy_flat_md_refs(self, project_dir: Path):
        """A7 counts flat .md files as fallback when no metadata.json found."""
        # Set paper type to letter (min 5) to test with fewer files
        profile = {"paper": {"type": "letter"}}
        with open(project_dir / "journal-profile.yaml", "w") as f:
            yaml.dump(profile, f)
        refs = project_dir / "references"
        refs.mkdir()
        for i in range(6):
            (refs / f"ref_{i}.md").write_text("# Ref")
        engine = WritingHooksEngine(project_dir)
        r = engine.check_reference_sufficiency()
        assert r.passed is True  # 6 >= 5 (letter)

    def test_in_run_post_write_hooks(self, project_dir: Path):
        """A7 is included in run_post_write_hooks batch runner."""
        engine = WritingHooksEngine(project_dir)
        results = engine.run_post_write_hooks("Some text.")
        assert "A7" in results
        assert results["A7"].hook_id == "A7"
        # No refs → should fail
        assert results["A7"].passed is False


# ──────────────────────────────────────────────────────────────────────────────
# Hook B2: Protected Content (post-write, delegates to P5)
# ──────────────────────────────────────────────────────────────────────────────


class TestHookB2:
    """B2: Protected content integrity — runs after every write (delegates to P5)."""

    def test_b2_returns_correct_hook_id(self, engine: WritingHooksEngine, project_dir: Path):
        """B2 result has hook_id='B2', not 'P5'."""
        concept = (
            "# Concept\n\n"
            "## NOVELTY STATEMENT \U0001f512\n\n"
            "This study is novel.\n\n"
            "## KEY SELLING POINTS \U0001f512\n\n"
            "1. First point\n"
        )
        (project_dir / "concept.md").write_text(concept, encoding="utf-8")
        r = engine._run_b2_protected_content()
        assert r.hook_id == "B2"
        assert r.passed is True
        assert r.stats["protected_blocks_found"] == 2

    def test_b2_empty_block_critical_with_b2_id(
        self, engine: WritingHooksEngine, project_dir: Path
    ):
        """Empty protected block → CRITICAL with hook_id='B2' (not P5)."""
        concept = (
            "# Concept\n\n"
            "## NOVELTY STATEMENT \U0001f512\n\n"
            "[placeholder]\n\n"
            "## KEY SELLING POINTS \U0001f512\n\n"
            "1. Valid content\n"
        )
        (project_dir / "concept.md").write_text(concept, encoding="utf-8")
        r = engine._run_b2_protected_content()
        assert r.hook_id == "B2"
        assert r.passed is False
        assert all(i.hook_id == "B2" for i in r.issues)
        assert any(i.severity == "CRITICAL" for i in r.issues)

    def test_b2_no_concept_file_passes(self, engine: WritingHooksEngine):
        """No concept.md → PASS (same as P5 behavior)."""
        r = engine._run_b2_protected_content()
        assert r.hook_id == "B2"
        assert r.passed is True

    def test_b2_in_post_write_batch(self, engine: WritingHooksEngine):
        """B2 is included in run_post_write_hooks batch runner."""
        results = engine.run_post_write_hooks("Some text.")
        assert "B2" in results
        assert results["B2"].hook_id == "B2"


# ──────────────────────────────────────────────────────────────────────────────
# Hook C2: Submission Checklist
# ──────────────────────────────────────────────────────────────────────────────


class TestHookC2:
    """C2: Verify required submission documents exist."""

    def test_no_journal_profile_passes(self, engine: WritingHooksEngine):
        """No journal-profile.yaml → PASS (skipped)."""
        r = engine.check_submission_checklist("Some content.")
        assert r.hook_id == "C2"
        assert r.passed is True
        assert "No journal-profile" in r.stats.get("note", "")

    def test_no_required_documents_passes(self, project_dir: Path):
        """Profile exists but no required_documents → PASS."""
        profile = {"word_limits": {"total_manuscript": 5000}}
        with open(project_dir / "journal-profile.yaml", "w") as f:
            yaml.dump(profile, f)
        engine = WritingHooksEngine(project_dir)
        r = engine.check_submission_checklist("Some content.")
        assert r.hook_id == "C2"
        assert r.passed is True

    def test_all_required_docs_found_in_content(self, project_dir: Path):
        """Required documents found via content pattern matching → PASS."""
        profile = {
            "required_documents": {
                "conflict_of_interest": True,
                "funding_statement": True,
                "ethics_statement": True,
            }
        }
        with open(project_dir / "journal-profile.yaml", "w") as f:
            yaml.dump(profile, f)
        engine = WritingHooksEngine(project_dir)
        content = (
            "The authors declare no conflict of interest.\n"
            "This study was supported by Grant No. 12345.\n"
            "The study was approved by the Institutional Review Board.\n"
        )
        r = engine.check_submission_checklist(content)
        assert r.hook_id == "C2"
        assert r.passed is True
        assert r.stats["missing_count"] == 0
        assert r.stats["found_count"] == 3

    def test_missing_required_doc_warns(self, project_dir: Path):
        """Required document not found → WARNING per missing item."""
        profile = {
            "required_documents": {
                "cover_letter": True,
                "highlights": True,
            }
        }
        with open(project_dir / "journal-profile.yaml", "w") as f:
            yaml.dump(profile, f)
        engine = WritingHooksEngine(project_dir)
        r = engine.check_submission_checklist("No relevant content here.")
        assert r.hook_id == "C2"
        assert r.passed is False
        assert r.stats["missing_count"] == 2
        assert "cover_letter" in r.stats["missing_docs"]
        assert "highlights" in r.stats["missing_docs"]
        assert all(i.severity == "WARNING" for i in r.issues)

    def test_file_existence_satisfies(self, project_dir: Path):
        """File found in project dir → satisfies the requirement."""
        profile = {"required_documents": {"cover_letter": True}}
        with open(project_dir / "journal-profile.yaml", "w") as f:
            yaml.dump(profile, f)
        (project_dir / "cover-letter.md").write_text("Dear Editor,\n")
        engine = WritingHooksEngine(project_dir)
        r = engine.check_submission_checklist("No content match here.")
        assert r.passed is True
        assert "cover_letter" in r.stats["found_docs"]

    def test_false_requirement_skipped(self, project_dir: Path):
        """required_documents entry with False → not checked."""
        profile = {
            "required_documents": {
                "cover_letter": True,
                "highlights": False,
            }
        }
        with open(project_dir / "journal-profile.yaml", "w") as f:
            yaml.dump(profile, f)
        (project_dir / "cover-letter.md").write_text("Dear Editor,\n")
        engine = WritingHooksEngine(project_dir)
        r = engine.check_submission_checklist("")
        assert r.passed is True
        assert r.stats["required_count"] == 1  # Only cover_letter counted

    def test_c2_in_post_manuscript_batch(self, engine: WritingHooksEngine):
        """C2 is included in run_post_manuscript_hooks batch runner."""
        results = engine.run_post_manuscript_hooks("## Methods\n\nSome methods.")
        assert "C2" in results
        assert results["C2"].hook_id == "C2"

    def test_dict_required_documents_format(self, project_dir: Path):
        """required_documents with dict values (required: true/false)."""
        profile = {
            "required_documents": {
                "cover_letter": {"required": True},
                "highlights": {"required": False},
            }
        }
        with open(project_dir / "journal-profile.yaml", "w") as f:
            yaml.dump(profile, f)
        engine = WritingHooksEngine(project_dir)
        r = engine.check_submission_checklist("")
        # cover_letter required but not found
        assert r.passed is False
        assert r.stats["required_count"] == 1


# ──────────────────────────────────────────────────────────────────────────────
# Hook P6: Memory Sync Gate
# ──────────────────────────────────────────────────────────────────────────────


class TestHookP6:
    """P6: Verify memory files updated before commit."""

    def test_no_memory_files_passes(self, engine: WritingHooksEngine):
        """No memory dirs/files → PASS (nothing to check)."""
        r = engine.check_memory_sync()
        assert r.hook_id == "P6"
        assert r.passed is True
        assert "No memory files" in r.stats.get("note", "")

    def test_fresh_memory_passes(self, project_dir: Path):
        """Recently updated memory files → PASS."""
        mem = project_dir / ".memory"
        mem.mkdir()
        (mem / "activeContext.md").write_text("# Active Context\nUpdated now.")
        engine = WritingHooksEngine(project_dir)
        r = engine.check_memory_sync()
        assert r.hook_id == "P6"
        assert r.passed is True
        assert r.stats["files_checked"] >= 1
        assert len(r.stats["fresh_files"]) >= 1

    def test_stale_memory_warns(self, project_dir: Path):
        """All memory files older than 2 hours → WARNING."""
        import os
        import time

        mem = project_dir / ".memory"
        mem.mkdir()
        fpath = mem / "activeContext.md"
        fpath.write_text("# Active Context\nOld content.")
        # Set mtime to 3 hours ago
        old_time = time.time() - 10800
        os.utime(fpath, (old_time, old_time))

        engine = WritingHooksEngine(project_dir)
        r = engine.check_memory_sync()
        assert r.hook_id == "P6"
        assert r.passed is False
        assert len(r.stats["stale_files"]) >= 1
        assert any(i.severity == "WARNING" for i in r.issues)
        assert any("stale" in i.message.lower() for i in r.issues)

    def test_mixed_fresh_stale_passes(self, project_dir: Path):
        """At least one fresh memory file → PASS (not all stale)."""
        import os
        import time

        mem = project_dir / ".memory"
        mem.mkdir()
        # Stale file
        stale = mem / "activeContext.md"
        stale.write_text("Old content.")
        old_time = time.time() - 10800
        os.utime(stale, (old_time, old_time))
        # Fresh file — create a workspace-level memory-bank for this
        # The engine walks up to find .git, so create .git in project_dir
        (project_dir / ".git").mkdir(exist_ok=True)
        mb = project_dir / "memory-bank"
        mb.mkdir()
        (mb / "activeContext.md").write_text("Fresh content.")

        engine = WritingHooksEngine(project_dir)
        r = engine.check_memory_sync()
        assert r.hook_id == "P6"
        # At least one fresh → passes (stale_files AND fresh_files both exist)
        assert r.passed is True

    def test_p6_in_precommit_batch(self, engine: WritingHooksEngine, project_dir: Path):
        """P6 is included in run_precommit_hooks batch runner."""
        (project_dir / "references").mkdir()
        results = engine.run_precommit_hooks("Some text.")
        assert "P6" in results
        assert results["P6"].hook_id == "P6"
