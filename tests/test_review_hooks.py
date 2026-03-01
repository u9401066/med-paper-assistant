"""
Tests for ReviewHooksEngine (R1–R6).

Covers:
- R1: Review Report Depth
- R2: Author Response Completeness
- R3: EQUATOR Compliance Gate
- R4: Review-Fix Traceability
- R5: Post-Review Anti-AI Gate
- R6: Citation Budget Gate
- Batch runner: run_all()
"""

import json
import textwrap

import pytest

from med_paper_assistant.infrastructure.persistence.review_hooks import (
    MAX_DECLINE_RATIO,
    MIN_EQUATOR_ITEMS,
    MIN_PERSPECTIVES,
    MIN_REVIEW_REPORT_WORDS,
    ReviewHooksEngine,
)

# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory with audit dir and drafts."""
    audit = tmp_path / ".audit"
    audit.mkdir()
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    return tmp_path


@pytest.fixture
def engine(project_dir):
    """Create a ReviewHooksEngine for the temp project."""
    return ReviewHooksEngine(project_dir)


def _write_review_report(project_dir, round_num, content):
    """Helper to write a review report file."""
    path = project_dir / ".audit" / f"review-report-{round_num}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _write_author_response(project_dir, round_num, content):
    """Helper to write an author response file."""
    path = project_dir / ".audit" / f"author-response-{round_num}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _write_equator_compliance(project_dir, round_num, content):
    """Helper to write an EQUATOR compliance file."""
    path = project_dir / ".audit" / f"equator-compliance-{round_num}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _write_equator_na(project_dir, round_num, content):
    """Helper to write an EQUATOR N/A file."""
    path = project_dir / ".audit" / f"equator-na-{round_num}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _write_journal_profile(project_dir, max_refs=30, paper_type="original-research"):
    """Helper to write a journal-profile.yaml."""
    path = project_dir / "journal-profile.yaml"
    content = textwrap.dedent(f"""\
        paper:
          type: {paper_type}
        references:
          max_references: 40
          reference_limits:
            original-research: {max_refs}
            review-article: 50
            case-report: 15
    """)
    path.write_text(content, encoding="utf-8")


# ── R1: Review Report Depth ───────────────────────────────────────────


class TestR1ReviewReportDepth:
    """Tests for check_review_report_depth."""

    def test_missing_report_fails(self, engine):
        result = engine.check_review_report_depth(1)
        assert not result.passed
        assert result.critical_count == 1
        assert "not found" in result.issues[0].message

    def test_too_short_report_fails(self, engine, project_dir):
        _write_review_report(project_dir, 1, "Too short.")
        result = engine.check_review_report_depth(1)
        assert not result.passed
        assert any("too short" in i.message.lower() for i in result.issues)

    def test_good_report_passes(self, engine, project_dir):
        # 400+ words with multiple perspectives and severity
        content = textwrap.dedent("""\
            ---
            major: 3
            minor: 2
            optional: 1
            ---
            # Review Report Round 1

            ## Methodology Assessment
            The methodology section describes a retrospective cohort study design.
            However, several methodology concerns need addressing.
            The sample size calculation is missing.

            ## Domain Expert Perspective
            From a clinical domain perspective, the choice of outcome measures
            is reasonable but incomplete. The primary endpoint should include
            at least one patient-reported outcome. The clinical significance
            of the findings needs clarification.

            ## Statistical Review
            The statistical analysis plan has several gaps. The statistic methods
            used are appropriate for the primary outcome but not for secondary
            outcomes. Consider using mixed-effects models instead.

            ## Writing Quality
            The writing is generally clear but needs improvement in several areas.
            The abstract does not follow standard structure. Several paragraphs
            in the Discussion section are too long and should be split.

            ## Major Issues
            - major: Sample size calculation missing from Methods
            - major: Primary endpoint definition unclear
            - major: No sensitivity analysis described

            ## Minor Issues
            - minor: Abstract formatting does not follow journal guidelines
            - minor: Several abbreviations not defined at first use
        """)
        # Pad to ensure > 300 words
        content += "\n" + "Additional analysis text. " * 40
        _write_review_report(project_dir, 1, content)
        result = engine.check_review_report_depth(1)
        assert result.passed
        assert result.stats["report_words"] >= MIN_REVIEW_REPORT_WORDS
        assert result.stats["perspective_count"] >= MIN_PERSPECTIVES

    def test_missing_perspectives_fails(self, engine, project_dir):
        # Long enough but only mentions one perspective
        content = "# Review\n\n" + "This writing needs improvement. " * 30
        content += "\nmajor: 1\nminor: 1\n"
        _write_review_report(project_dir, 1, content)
        result = engine.check_review_report_depth(1)
        assert not result.passed
        assert any("perspective" in i.message.lower() for i in result.issues)

    def test_no_severity_classification_fails(self, engine, project_dir):
        # Long enough with perspectives but no severity
        content = textwrap.dedent("""\
            # Review Report

            ## Methodology
            Issues found here.

            ## Domain Analysis
            Issues found here.

            ## Statistical Review
            Issues found here.

            ## Writing Quality
            Issues found here.
        """)
        content += "\n" + "More analysis text here. " * 30
        _write_review_report(project_dir, 1, content)
        result = engine.check_review_report_depth(1)
        assert not result.passed
        assert any("severity" in i.message.lower() for i in result.issues)


# ── R2: Author Response Completeness ──────────────────────────────────


class TestR2AuthorResponseCompleteness:
    """Tests for check_author_response_completeness."""

    def test_missing_response_fails(self, engine):
        result = engine.check_author_response_completeness(1)
        assert not result.passed
        assert result.critical_count == 1

    def test_no_decisions_fails(self, engine, project_dir):
        _write_author_response(project_dir, 1, "We thank the reviewer for their comments.")
        result = engine.check_author_response_completeness(1)
        assert not result.passed
        assert any("no accept/decline" in i.message.lower() for i in result.issues)

    def test_good_response_passes(self, engine, project_dir):
        # Write matching review report
        report = textwrap.dedent("""\
            ---
            major: 2
            minor: 1
            ---
            # Review Report
            - major: Issue 1
            - major: Issue 2
            - minor: Issue 3
        """)
        _write_review_report(project_dir, 1, report)

        response = textwrap.dedent("""\
            # Author Response Round 1

            ## Issue 1: Sample size
            ACCEPT — We added sample size calculation to Methods (Section 2.3).
            Reference: [[smith2024_12345678]] provides supporting evidence.

            ## Issue 2: Endpoint definition
            ACCEPT — Clarified primary endpoint in Section 2.1 with reference
            to [[jones2023_87654321]].

            ## Issue 3: Abstract formatting
            ACCEPT — Reformatted abstract to follow journal guidelines.
        """)
        _write_author_response(project_dir, 1, response)
        result = engine.check_author_response_completeness(1)
        assert result.passed
        assert result.stats["accept_count"] == 3
        assert result.stats["decline_ratio"] == 0

    def test_too_many_declines_fails(self, engine, project_dir):
        report = textwrap.dedent("""\
            ---
            major: 3
            minor: 1
            ---
            - major: Issue 1
            - major: Issue 2
            - major: Issue 3
            - minor: Issue 4
        """)
        _write_review_report(project_dir, 1, report)

        response = textwrap.dedent("""\
            ## Issue 1
            DECLINE — We disagree with this assessment.
            ## Issue 2
            DECLINE — Not applicable to our study design.
            ## Issue 3
            DECLINE — This is outside scope.
            ## Issue 4
            ACCEPT — Fixed.
        """)
        _write_author_response(project_dir, 1, response)
        result = engine.check_author_response_completeness(1)
        assert not result.passed
        assert result.stats["decline_ratio"] > MAX_DECLINE_RATIO

    def test_incomplete_response_fails(self, engine, project_dir):
        report = textwrap.dedent("""\
            ---
            major: 3
            ---
            - major: Issue 1
            - major: Issue 2
            - major: Issue 3
        """)
        _write_review_report(project_dir, 1, report)

        response = textwrap.dedent("""\
            ## Issue 1
            ACCEPT — Fixed in manuscript.
        """)
        _write_author_response(project_dir, 1, response)
        result = engine.check_author_response_completeness(1)
        assert not result.passed
        assert any("1/3" in i.message for i in result.issues)

    def test_no_evidence_warning(self, engine, project_dir):
        response = textwrap.dedent("""\
            ## Issue 1
            ACCEPT — We agree and made changes.
            ## Issue 2
            ACCEPT — We revised accordingly.
        """)
        _write_author_response(project_dir, 1, response)
        result = engine.check_author_response_completeness(1)
        assert result.passed  # warnings don't fail
        assert result.warning_count >= 1
        assert any("evidence" in i.message.lower() for i in result.issues)


# ── R3: EQUATOR Compliance Gate ───────────────────────────────────────


class TestR3EquatorCompliance:
    """Tests for check_equator_compliance."""

    def test_missing_both_files_fails(self, engine):
        result = engine.check_equator_compliance(1)
        assert not result.passed
        assert result.critical_count == 1
        assert "neither" in result.issues[0].message.lower()

    def test_compliance_with_enough_items_passes(self, engine, project_dir):
        content = textwrap.dedent("""\
            # STROBE Checklist

            - [x] Title and abstract
            - [x] Introduction: Background/rationale
            - [x] Methods: Study design
            - [x] Results: Main results
            - [x] Discussion: Key results
            - [ ] Other information: Funding
        """)
        _write_equator_compliance(project_dir, 1, content)
        result = engine.check_equator_compliance(1)
        assert result.passed
        assert result.stats["checklist_items"] >= MIN_EQUATOR_ITEMS

    def test_compliance_too_few_items_fails(self, engine, project_dir):
        content = textwrap.dedent("""\
            # CONSORT Checklist
            - [x] Title
            - [x] Abstract
        """)
        _write_equator_compliance(project_dir, 1, content)
        result = engine.check_equator_compliance(1)
        assert not result.passed
        assert result.stats["checklist_items"] < MIN_EQUATOR_ITEMS

    def test_na_with_justification_passes(self, engine, project_dir):
        content = textwrap.dedent("""\
            # EQUATOR Not Applicable

            This is a methodological paper that does not report
            empirical data from human subjects. Therefore, no
            EQUATOR reporting guideline (CONSORT, STROBE, PRISMA,
            CARE, etc.) is directly applicable to this study type.
        """)
        _write_equator_na(project_dir, 1, content)
        result = engine.check_equator_compliance(1)
        assert result.passed
        assert result.stats["type"] == "not_applicable"

    def test_na_too_brief_warns(self, engine, project_dir):
        _write_equator_na(project_dir, 1, "N/A")
        result = engine.check_equator_compliance(1)
        assert result.passed  # WARNING, not CRITICAL
        assert result.warning_count >= 1


# ── R4: Review-Fix Traceability ───────────────────────────────────────


class TestR4ReviewFixTraceability:
    """Tests for check_review_fix_traceability."""

    def test_accept_without_changes_fails(self, engine, project_dir):
        response = textwrap.dedent("""\
            ## Issue 1
            ACCEPT — Will fix this.
            ## Issue 2
            ACCEPT — Will fix this too.
        """)
        _write_author_response(project_dir, 1, response)
        result = engine.check_review_fix_traceability(1, issues_fixed=0, manuscript_changed=False)
        assert not result.passed
        assert any("not modified" in i.message.lower() for i in result.issues)

    def test_accept_with_changes_passes(self, engine, project_dir):
        response = textwrap.dedent("""\
            ## Issue 1
            ACCEPT — Changed paragraph 3 in Methods to add sample size.
            ## Issue 2
            ACCEPT — Updated Discussion to address limitation.
        """)
        _write_author_response(project_dir, 1, response)
        result = engine.check_review_fix_traceability(1, issues_fixed=2, manuscript_changed=True)
        assert result.passed

    def test_accept_with_zero_fixed_warns(self, engine, project_dir):
        response = textwrap.dedent("""\
            ## Issue 1
            ACCEPT — Changed something.
        """)
        _write_author_response(project_dir, 1, response)
        result = engine.check_review_fix_traceability(1, issues_fixed=0, manuscript_changed=True)
        assert result.passed  # WARNING only
        assert result.warning_count >= 1

    def test_no_response_file_still_passes(self, engine):
        """R4 can pass without response file (traceability just checks consistency)."""
        result = engine.check_review_fix_traceability(1, issues_fixed=0, manuscript_changed=False)
        assert result.passed  # No ACCEPTs found = nothing to trace


# ── R5: Post-Review Anti-AI Gate ──────────────────────────────────────


class TestR5PostReviewAntiAI:
    """Tests for check_post_review_anti_ai."""

    def test_clean_manuscript_passes(self, engine):
        content = textwrap.dedent("""\
            # Introduction
            We conducted a retrospective study examining outcomes.

            # Methods
            We reviewed medical records from 2020 to 2023.
        """)
        result = engine.check_post_review_anti_ai(content)
        assert result.passed
        assert result.stats["total_ai_issues"] == 0

    def test_ai_patterns_detected(self, engine):
        content = textwrap.dedent("""\
            # Introduction
            In the rapidly evolving landscape of medical research,
            it is crucial to delve into the intricate interplay
            between various factors. This groundbreaking study aims to
            shed light on these important considerations.
        """)
        result = engine.check_post_review_anti_ai(content)
        # Should detect AI patterns via A3/A3b — these phrases are strong AI signals
        assert result.stats["total_ai_issues"] > 0, (
            "Expected AI patterns to be detected in text with known AI phrases"
        )


# ── R6: Citation Budget Gate ──────────────────────────────────────────


class TestR6CitationBudget:
    """Tests for check_citation_budget."""

    def test_no_journal_profile_passes(self, engine):
        content = "Some text with [[author2024_12345678]] reference."
        result = engine.check_citation_budget(content)
        assert result.passed
        assert result.stats["max_refs"] == "not_configured"

    def test_under_budget_passes(self, engine, project_dir):
        _write_journal_profile(project_dir, max_refs=10)
        # Reload engine to pick up journal profile
        engine = ReviewHooksEngine(project_dir)

        refs = " ".join(f"[[author{i:04d}_1234567{i}]]" for i in range(5))
        content = f"# Introduction\n\n{refs}\n"
        result = engine.check_citation_budget(content)
        assert result.passed
        assert result.stats["total_refs"] == 5
        assert result.stats["over_budget"] == 0

    def test_over_budget_fails(self, engine, project_dir):
        _write_journal_profile(project_dir, max_refs=3)
        engine = ReviewHooksEngine(project_dir)

        refs = " ".join(f"[[author{i:04d}_1234567{i}]]" for i in range(6))
        content = f"# Introduction\n\n{refs}\n"
        result = engine.check_citation_budget(content)
        assert not result.passed
        assert result.stats["over_budget"] == 3
        assert result.critical_count >= 1

    def test_at_limit_warns(self, engine, project_dir):
        _write_journal_profile(project_dir, max_refs=5)
        engine = ReviewHooksEngine(project_dir)

        refs = " ".join(f"[[author{i:04d}_1234567{i}]]" for i in range(5))
        content = f"# Introduction\n\n{refs}\n"
        result = engine.check_citation_budget(content)
        assert result.passed  # At limit, just warning
        assert result.warning_count >= 1

    def test_trim_suggestions_provided(self, engine, project_dir):
        _write_journal_profile(project_dir, max_refs=2)
        engine = ReviewHooksEngine(project_dir)

        # Write citation_decisions.json with priorities
        decisions = {
            "author0000_12345670": {"priority": 5, "justification": "Key foundational paper"},
            "author0001_12345671": {"priority": 1, "justification": "Minor supporting ref"},
            "author0002_12345672": {"priority": 3, "justification": "Moderately important"},
        }
        decisions_path = project_dir / "citation_decisions.json"
        decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

        refs = " ".join(f"[[author{i:04d}_1234567{i}]]" for i in range(3))
        content = f"# Introduction\n\n{refs}\n"
        result = engine.check_citation_budget(content)
        assert not result.passed
        # Should suggest trimming lowest priority first
        trim_msgs = [i.message for i in result.issues if "trim candidate" in i.message.lower()]
        assert len(trim_msgs) >= 1
        # The lowest priority (author0001) should be first trim candidate
        assert "author0001" in trim_msgs[0]

    def test_unique_refs_counted(self, engine, project_dir):
        _write_journal_profile(project_dir, max_refs=10)
        engine = ReviewHooksEngine(project_dir)

        # Same ref cited multiple times should count as 1
        content = textwrap.dedent("""\
            # Introduction
            As shown by [[author2024_12345678]], this is important.

            # Discussion
            Consistent with [[author2024_12345678]], our findings suggest...
            Also see [[smith2023_87654321]].
        """)
        result = engine.check_citation_budget(content)
        assert result.stats["total_refs"] == 2  # Not 3


# ── Batch Runner ──────────────────────────────────────────────────────


class TestRunAll:
    """Tests for run_all batch runner."""

    def test_run_all_returns_all_hooks(self, engine, project_dir):
        # Create all needed files for round 1
        _write_review_report(project_dir, 1, "# Review\n" + "methodology domain statistic writing\n" * 40 + "major: 2\nminor: 1\n")
        _write_author_response(project_dir, 1, "# Response\nACCEPT — Changed method. Reference [[x2024_12345678]].\nACCEPT — Updated.\n")
        _write_equator_compliance(project_dir, 1, "\n".join(f"- [x] Item {i}" for i in range(7)))

        ms = project_dir / "drafts" / "manuscript.md"
        ms.write_text("# Title\n\nContent here.\n", encoding="utf-8")

        results = engine.run_all(
            round_num=1,
            issues_fixed=2,
            manuscript_changed=True,
            manuscript_content=ms.read_text(encoding="utf-8"),
        )
        # Should have R1-R6
        assert "R1" in results
        assert "R2" in results
        assert "R3" in results
        assert "R4" in results
        assert "R5" in results
        assert "R6" in results

    def test_run_all_without_manuscript_skips_r5_r6(self, engine, project_dir):
        _write_review_report(project_dir, 1, "# Short review\nmajor:1\n")
        _write_author_response(project_dir, 1, "ACCEPT — fixed\n")

        results = engine.run_all(round_num=1, manuscript_content="")
        assert "R1" in results
        assert "R2" in results
        assert "R3" in results
        assert "R4" in results
        assert "R5" not in results  # skipped
        assert "R6" not in results  # skipped
