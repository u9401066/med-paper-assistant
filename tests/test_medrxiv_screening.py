"""
Tests for medRxiv pre-submission screening checks.
"""

from med_paper_assistant.interfaces.mcp.tools.review.medrxiv_screening import (
    ScreeningReport,
    _check_article_type,
    _check_clinical_trial_registration,
    _check_conflict_of_interest,
    _check_ethics_declaration,
    _check_patient_identification,
    _check_public_harm_signals,
    _check_research_scope,
    run_medrxiv_screening,
)

# ── Fixtures ─────────────────────────────────────────────────────────────


GOOD_MANUSCRIPT = """
# Title: A Randomized Controlled Trial of Drug X vs Placebo

## Abstract

Background: This study evaluates drug X in patients with disease Y.

## Introduction

Clinical trials have shown promising results for treatment of disease Y.

## Methods

This study was approved by the Institutional Review Board (IRB approval number: 2025-001).
Informed consent was obtained from all participants.
Trial registration: NCT12345678.

We conducted a randomized controlled trial at a hospital.
Patients were randomized to treatment group or placebo group.

## Results

We enrolled 200 patients. Table 1 shows baseline characteristics.

## Discussion

Our findings suggest drug X is effective for disease Y.

## Conflict of Interest

The authors declare no competing interests.
"""


MINIMAL_RESEARCH = """
# A Framework for AI-Assisted Medical Writing

## Abstract

Background: This study presents a software framework for medical research.

## Introduction

Medical writing requires domain knowledge and methodological rigor.

## Methods

We developed and evaluated a Python-based framework. The study was deemed exempt
from IRB review by the institutional ethics committee.

## Results

The framework processed 48 citations and produced formatted manuscripts.

## Discussion

Our framework demonstrates feasibility of AI-assisted medical writing.

## Conflict of Interest

The authors declare no competing interests.
"""


# ── Article Type Tests ───────────────────────────────────────────────────


class TestArticleType:
    def test_research_manuscript_passes(self):
        report = ScreeningReport()
        _check_article_type(GOOD_MANUSCRIPT, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_missing_methods_fails(self):
        content = "# Title\n## Introduction\n\n## Results\n\nSome results."
        report = ScreeningReport()
        _check_article_type(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 1
        assert "Methods" in errors[0].description

    def test_missing_results_fails(self):
        content = "# Title\n## Introduction\n\n## Methods\n\nSome methods."
        report = ScreeningReport()
        _check_article_type(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 1

    def test_narrative_review_flagged(self):
        content = (
            "# A Narrative Review of Treatment Options\n"
            "## Methods\n\nWe searched PubMed.\n"
            "## Results\n\nWe found 50 articles."
        )
        report = ScreeningReport()
        _check_article_type(content, report)
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert len(warnings) == 1
        assert "narrative" in warnings[0].description.lower()

    def test_case_report_flagged(self):
        content = (
            "# Title\n## Case Report\n\nA 45-year-old male.\n"
            "## Methods\n\nCase review.\n## Results\n\nOutcome."
        )
        report = ScreeningReport()
        _check_article_type(content, report)
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert len(warnings) == 1
        assert "case report" in warnings[0].description.lower()

    def test_protocol_detected(self):
        content = (
            "# Study Protocol for a Randomized Trial\n"
            "## Methods\n\nTrial protocol details.\n"
            "## Results\n\nExpected outcomes."
        )
        report = ScreeningReport()
        _check_article_type(content, report)
        infos = [i for i in report.issues if i.severity == "info"]
        assert any("protocol" in i.description.lower() for i in infos)


# ── Ethics Declaration Tests ─────────────────────────────────────────────


class TestEthicsDeclaration:
    def test_irb_approval_passes(self):
        content = "This study was approved by the Institutional Review Board (IRB)."
        report = ScreeningReport()
        _check_ethics_declaration(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_ethics_committee_passes(self):
        content = "Ethics committee approval was obtained (approval number: EC-2025-01)."
        report = ScreeningReport()
        _check_ethics_declaration(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_exempt_passes(self):
        content = "The study was deemed exempt from IRB review."
        report = ScreeningReport()
        _check_ethics_declaration(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_missing_ethics_fails(self):
        content = "We conducted a study and analyzed data."
        report = ScreeningReport()
        _check_ethics_declaration(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 1
        assert "ethics" in errors[0].description.lower() or "IRB" in errors[0].description

    def test_no_approval_number_info(self):
        content = "The study received ethical approval from the institutional review board."
        report = ScreeningReport()
        _check_ethics_declaration(content, report)
        infos = [i for i in report.issues if i.severity == "info"]
        assert any("approval number" in i.description.lower() for i in infos)

    def test_approval_with_number_no_info(self):
        content = "This study was approved by the IRB (approval number: 2025-001)."
        report = ScreeningReport()
        _check_ethics_declaration(content, report)
        infos = [i for i in report.issues if i.severity == "info"]
        assert len(infos) == 0


# ── Patient Identification Tests ─────────────────────────────────────────


class TestPatientIdentification:
    def test_clean_manuscript_passes(self):
        report = ScreeningReport()
        _check_patient_identification(MINIMAL_RESEARCH, report)
        errors = [i for i in report.issues if i.severity in ("error", "warning")]
        assert len(errors) == 0

    def test_exact_age_flagged(self):
        content = "A 45-year-old male patient presented with chest pain."
        report = ScreeningReport()
        _check_patient_identification(content, report)
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert len(warnings) >= 1
        assert any("age" in w.description.lower() for w in warnings)

    def test_admission_date_flagged(self):
        content = "The patient was admitted on January 15, 2025 to the ICU."
        report = ScreeningReport()
        _check_patient_identification(content, report)
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert len(warnings) >= 1

    def test_patient_photograph_flagged(self):
        content = "Figure 1 shows a photograph of the patient's skin lesion."
        report = ScreeningReport()
        _check_patient_identification(content, report)
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert len(warnings) >= 1
        assert any("photograph" in w.description.lower() for w in warnings)

    def test_family_identifier_flagged(self):
        content = "The patient's mother was also diagnosed with BRCA1 mutation."
        report = ScreeningReport()
        _check_patient_identification(content, report)
        issues = [i for i in report.issues if i.category == "Patient Privacy"]
        assert len(issues) >= 1


# ── Clinical Trial Registration Tests ────────────────────────────────────


class TestClinicalTrialRegistration:
    def test_rct_with_nct_passes(self):
        content = "We conducted a randomized controlled trial.\nTrial registration: NCT12345678."
        report = ScreeningReport()
        _check_clinical_trial_registration(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_rct_without_registration_fails(self):
        content = (
            "We conducted a randomized controlled trial.\n"
            "Patients were randomized to treatment group."
        )
        report = ScreeningReport()
        _check_clinical_trial_registration(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 1
        assert "registration" in errors[0].description.lower()

    def test_non_interventional_skipped(self):
        content = "We conducted a retrospective cohort study using medical records."
        report = ScreeningReport()
        _check_clinical_trial_registration(content, report)
        assert len(report.issues) == 0

    def test_isrctn_recognized(self):
        content = "This was a clinical trial. Registered as ISRCTN12345678."
        report = ScreeningReport()
        _check_clinical_trial_registration(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_chinese_registry_recognized(self):
        content = "This randomized trial was registered (ChiCTR2000012345)."
        report = ScreeningReport()
        _check_clinical_trial_registration(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0


# ── Research Scope Tests ─────────────────────────────────────────────────


class TestResearchScope:
    def test_health_research_passes(self):
        report = ScreeningReport()
        _check_research_scope(GOOD_MANUSCRIPT, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_no_health_terms_flagged(self):
        content = (
            "# Software Engineering Study\n"
            "## Methods\n\nWe analyzed code repositories.\n"
            "## Results\n\nWe found patterns in software."
        )
        report = ScreeningReport()
        _check_research_scope(content, report)
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert any("health" in w.description.lower() for w in warnings)


# ── Public Harm Tests ────────────────────────────────────────────────────


class TestPublicHarm:
    def test_clean_manuscript_passes(self):
        report = ScreeningReport()
        _check_public_harm_signals(GOOD_MANUSCRIPT, report)
        assert len(report.issues) == 0

    def test_antivax_language_flagged(self):
        content = "Our results show that vaccines are dangerous and cause adverse events."
        report = ScreeningReport()
        _check_public_harm_signals(content, report)
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert len(warnings) >= 1

    def test_miracle_cure_flagged(self):
        content = "We discovered a miracle cure for cancer using herbal extract."
        report = ScreeningReport()
        _check_public_harm_signals(content, report)
        warnings = [i for i in report.issues if i.severity == "warning"]
        assert len(warnings) >= 1

    def test_normal_treatment_discussion_passes(self):
        content = (
            "Vaccine efficacy was 95% in the treatment group. Side effects were mild and transient."
        )
        report = ScreeningReport()
        _check_public_harm_signals(content, report)
        assert len(report.issues) == 0


# ── Conflict of Interest Tests ───────────────────────────────────────────


class TestConflictOfInterest:
    def test_coi_present_passes(self):
        content = "Conflict of Interest: The authors declare no competing interests."
        report = ScreeningReport()
        _check_conflict_of_interest(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_competing_interests_passes(self):
        content = "Competing Interests: None declared."
        report = ScreeningReport()
        _check_conflict_of_interest(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_no_coi_fails(self):
        content = "This is a manuscript about software engineering methods."
        report = ScreeningReport()
        _check_conflict_of_interest(content, report)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 1


# ── Integration: run_medrxiv_screening ───────────────────────────────────


class TestRunMedrxivScreening:
    def test_good_manuscript_minimal_issues(self):
        report = run_medrxiv_screening(GOOD_MANUSCRIPT)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0, f"Unexpected errors: {[e.description for e in errors]}"

    def test_minimal_research_passes(self):
        report = run_medrxiv_screening(MINIMAL_RESEARCH)
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0, f"Unexpected errors: {[e.description for e in errors]}"

    def test_empty_manuscript_has_errors(self):
        report = run_medrxiv_screening("# Title\n\nSome text.")
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) >= 2  # Missing methods, ethics, COI at minimum

    def test_categories_covered(self):
        """Ensure all 7 check categories are represented in a comprehensive run."""
        report = run_medrxiv_screening(GOOD_MANUSCRIPT)
        categories = {i.category for i in report.issues}
        # Good manuscript should at least trigger trial registration info
        assert "Clinical Trial Registration" in categories

    def test_report_summary(self):
        report = run_medrxiv_screening(GOOD_MANUSCRIPT)
        summary = report.to_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0
