"""Tests for PipelineGateValidator — hard gate enforcement."""

import json

import pytest

from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
    GateCheck,
    GateResult,
    PipelineGateValidator,
)


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory structure."""
    p = tmp_path / "test-project"
    for d in ["drafts", "references", "data", "results", ".audit", ".memory", "exports"]:
        (p / d).mkdir(parents=True)
    return p


@pytest.fixture
def validator(project_dir):
    return PipelineGateValidator(project_dir)


def _add_prerequisites(project_dir, up_to_phase: int):
    """Add prerequisite artifacts needed so that validate_phase(up_to_phase) won't
    fail on prerequisite checks.

    Uses the same numeric comparison as _check_prerequisites in production code.
    Phase 65 (Evolution Gate) works correctly because 65 >= 7 (manuscript) and
    65 >= 9 (scorecard) are both True, while 65 == 11 (exports) is False.
    """
    if up_to_phase >= 2:
        pj = project_dir / "project.json"
        if not pj.is_file():
            pj.write_text('{"slug": "test"}')
    if up_to_phase >= 3:
        # Must meet paper-type minimum (default original-research = 20)
        refs = project_dir / "references"
        for i in range(20):
            ref_dir = refs / f"ref-{i}"
            ref_dir.mkdir(parents=True, exist_ok=True)
            meta = ref_dir / "metadata.json"
            if not meta.is_file():
                meta.write_text(f'{{"pmid": "0000{i}"}}')
    if up_to_phase >= 4:
        concept = project_dir / "concept.md"
        if not concept.is_file():
            concept.write_text("# NOVELTY\n\nNew idea\n\n# KEY SELLING POINTS\n\n- Point A")
        concept_review = project_dir / ".audit" / "concept-review.yaml"
        if not concept_review.is_file():
            concept_review.write_text(
                "metadata:\n"
                "  generated_at: '2026-01-01T00:00:00'\n"
                "review:\n"
                "  readiness: ready\n"
                "research_question:\n"
                "  canonical_question: Does intervention X improve outcome Y?\n"
                "claims_required:\n"
                "  - id: claim-1\n"
                "    text: Intervention X improves outcome Y.\n"
                "protected_content:\n"
                "  novelty_statement_locked:\n"
                "    present: true\n"
                "  selling_points_locked:\n"
                "    present: true\n"
            )
        concept_validation = project_dir / ".audit" / "concept-validation.md"
        if not concept_validation.is_file():
            concept_validation.write_text("# Concept Validation")
    if up_to_phase >= 5:
        concept = project_dir / "concept.md"
        if not concept.is_file():
            concept.write_text("# NOVELTY\n\nNew idea\n\n# KEY SELLING POINTS\n\n- Point A")
    if up_to_phase >= 7:
        ms = project_dir / "drafts" / "manuscript.md"
        if not ms.is_file():
            ms.write_text("# Manuscript")
    if up_to_phase >= 9:
        sc = project_dir / ".audit" / "quality-scorecard.md"
        if not sc.is_file():
            sc.write_text("# Scorecard")
    if up_to_phase == 11:
        exports = project_dir / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        (exports / "paper.docx").write_bytes(b"PK")
        (exports / "paper.pdf").write_bytes(b"%PDF")


class TestGateResult:
    def test_critical_failures(self):
        result = GateResult(
            phase=0,
            phase_name="Test",
            checks=[
                GateCheck(name="a", description="", passed=True),
                GateCheck(name="b", description="fail", passed=False, severity="CRITICAL"),
                GateCheck(name="c", description="warn", passed=False, severity="WARNING"),
            ],
            passed=False,
        )
        assert len(result.critical_failures) == 1
        assert len(result.warnings) == 1

    def test_to_markdown(self):
        result = GateResult(
            phase=7,
            phase_name="Review",
            checks=[GateCheck(name="test", description="desc", passed=False)],
            passed=False,
            timestamp="2026-01-01T00:00:00",
        )
        md = result.to_markdown()
        assert "❌ FAILED" in md
        assert "Phase 7" in md


class TestPhase0:
    def test_fail_no_journal_profile(self, validator):
        r = validator.validate_phase(0)
        assert not r.passed

    def test_pass_with_journal_profile(self, validator, project_dir):
        (project_dir / "journal-profile.yaml").write_text("type: original")
        r = validator.validate_phase(0)
        assert r.passed


class TestPhase1:
    def test_pass_with_dirs(self, validator):
        r = validator.validate_phase(1)
        assert r.passed  # fixture creates all dirs

    def test_fail_missing_dir(self, project_dir):
        import shutil

        shutil.rmtree(project_dir / ".audit")
        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(1)
        assert not r.passed


class TestPhase2:
    def test_fail_insufficient_refs(self, validator):
        r = validator.validate_phase(2)
        assert not r.passed
        ref_check = next(c for c in r.checks if c.name == "references_count")
        assert "0/" in ref_check.details  # "0/20 references found"

    def test_pass_with_refs_default_paper_type(self, validator, project_dir):
        """Default paper type is original-research, minimum 20 refs."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        for i in range(20):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True)
            (ref_dir / "metadata.json").write_text(f'{{"pmid": "0000{i}"}}')
        r = validator.validate_phase(2)
        assert r.passed

    def test_fail_below_paper_type_minimum(self, validator, project_dir):
        """10 refs is below the 20 minimum for original-research."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        for i in range(10):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True)
            (ref_dir / "metadata.json").write_text(f'{{"pmid": "0000{i}"}}')
        r = validator.validate_phase(2)
        assert not r.passed
        ref_check = next(c for c in r.checks if c.name == "references_count")
        assert "need 10 more" in ref_check.details

    def test_case_report_lower_minimum(self, validator, project_dir):
        """Case reports only need 8 refs (from journal-profile.yaml)."""
        import yaml

        (project_dir / "project.json").write_text('{"slug": "test"}')
        (project_dir / "journal-profile.yaml").write_text(
            yaml.dump({"paper": {"type": "case-report"}})
        )
        for i in range(8):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True)
            (ref_dir / "metadata.json").write_text(f'{{"pmid": "0000{i}"}}')
        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(2)
        assert r.passed

    def test_systematic_review_higher_minimum(self, validator, project_dir):
        """Systematic reviews need 40 refs — 20 is insufficient."""
        import yaml

        (project_dir / "project.json").write_text('{"slug": "test"}')
        (project_dir / "journal-profile.yaml").write_text(
            yaml.dump({"paper": {"type": "systematic-review"}})
        )
        for i in range(20):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True)
            (ref_dir / "metadata.json").write_text(f'{{"pmid": "0000{i}"}}')
        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(2)
        assert not r.passed
        ref_check = next(c for c in r.checks if c.name == "references_count")
        assert "systematic-review" in ref_check.description

    def test_journal_profile_override_minimum(self, validator, project_dir):
        """journal-profile.yaml minimum_reference_limits overrides defaults."""
        import yaml

        (project_dir / "project.json").write_text('{"slug": "test"}')
        profile = {
            "paper": {"type": "original-research"},
            "references": {"minimum_reference_limits": {"original-research": 25}},
        }
        (project_dir / "journal-profile.yaml").write_text(yaml.dump(profile))
        for i in range(22):
            ref_dir = project_dir / "references" / f"ref-{i}"
            ref_dir.mkdir(parents=True)
            (ref_dir / "metadata.json").write_text(f'{{"pmid": "0000{i}"}}')
        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(2)
        assert not r.passed  # 22 < 25

    def test_legacy_flat_md_refs_counted(self, validator, project_dir):
        """Legacy .md refs (without metadata.json) are still counted."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        # Use letter type with low minimum (5) for easy testing
        import yaml

        (project_dir / "journal-profile.yaml").write_text(yaml.dump({"paper": {"type": "letter"}}))
        for i in range(5):
            (project_dir / "references" / f"ref-{i}.md").write_text(f"# Ref {i}")
        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(2)
        assert r.passed


class TestPhase3And4:
    def test_phase3_fails_without_concept_review_artifact(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=3)
        (project_dir / "concept.md").write_text(
            "# NOVELTY\n\nQuestion\n\n# KEY SELLING POINTS\n\n- Point A"
        )

        r = validator.validate_phase(3)

        assert not r.passed
        review_check = next(c for c in r.checks if c.name == "audit:concept-review.yaml")
        assert not review_check.passed

    def test_phase4_fails_without_complete_concept_review(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=3)
        (project_dir / ".audit" / "concept-review.yaml").write_text(
            "review:\n  readiness: ready\nclaims_required: []\n"
        )
        (project_dir / "manuscript-plan.yaml").write_text("title: draft\n")

        r = validator.validate_phase(4)

        assert not r.passed
        prereq_check = next(c for c in r.checks if c.name == "prereq:audit:concept-review.yaml")
        assert not prereq_check.passed

    def test_phase4_passes_with_complete_concept_review(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=4)
        (project_dir / "manuscript-plan.yaml").write_text("title: draft\n")

        r = validator.validate_phase(4)

        assert r.passed

    def test_phase3_blocks_revise_readiness_without_manual_override(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=4)
        (project_dir / ".audit" / "concept-review.yaml").write_text(
            "metadata:\n"
            "  generated_at: '2026-01-01T00:00:00'\n"
            "review:\n"
            "  readiness: revise\n"
            "research_question:\n"
            "  canonical_question: Does intervention X improve outcome Y?\n"
            "claims_required:\n"
            "  - id: claim-1\n"
            "    text: Intervention X improves outcome Y.\n"
            "protected_content:\n"
            "  novelty_statement_locked:\n"
            "    present: true\n"
            "  selling_points_locked:\n"
            "    present: true\n"
        )

        r = validator.validate_phase(3)

        assert not r.passed
        decision_check = next(c for c in r.checks if c.name == "concept-review-decision")
        assert decision_check.passed is False
        assert "manual approval required" in decision_check.details

    def test_phase4_allows_manual_override_for_revise_readiness(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=4)
        (project_dir / ".audit" / "concept-review.yaml").write_text(
            "metadata:\n"
            "  generated_at: '2026-01-01T00:00:00'\n"
            "review:\n"
            "  readiness: revise\n"
            "research_question:\n"
            "  canonical_question: Does intervention X improve outcome Y?\n"
            "claims_required:\n"
            "  - id: claim-1\n"
            "    text: Intervention X improves outcome Y.\n"
            "protected_content:\n"
            "  novelty_statement_locked:\n"
            "    present: true\n"
            "  selling_points_locked:\n"
            "    present: true\n"
        )
        (project_dir / ".audit" / "concept-review-override.yaml").write_text(
            "approved_to_proceed: true\n"
            "approved_by: human\n"
            "accepted_readiness: revise\n"
            "rationale: The concept is clinically meaningful despite weak novelty score.\n"
            "mode: human-collaboration\n"
        )
        (project_dir / "manuscript-plan.yaml").write_text("title: draft\n")

        r = validator.validate_phase(4)

        assert r.passed
        decision_check = next(c for c in r.checks if c.name == "concept-review-ready")
        assert "manual override" in decision_check.details


class TestPhase5:
    def test_fail_no_manuscript(self, validator):
        r = validator.validate_phase(5)
        assert not r.passed

    def test_fail_missing_sections(self, validator, project_dir):
        (project_dir / "drafts" / "manuscript.md").write_text("# Abstract\n\n## Introduction\n")
        r = validator.validate_phase(5)
        assert not r.passed  # missing Methods, Results, Discussion

    def test_pass_full_manuscript(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=5)
        content = "\n".join(
            [
                "# Title",
                "## Abstract",
                "text",
                "## Introduction",
                "text",
                "## Methods",
                "text",
                "## Results",
                "text",
                "## Discussion",
                "text",
            ]
        )
        (project_dir / "drafts" / "manuscript.md").write_text(content)
        r = validator.validate_phase(5)
        assert r.passed

    def test_fail_required_planned_asset_missing_from_manifest(self, validator, project_dir):
        import yaml

        _add_prerequisites(project_dir, up_to_phase=5)
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
        (project_dir / "drafts" / "manuscript.md").write_text(
            "\n".join(
                [
                    "# Title",
                    "## Abstract",
                    "text",
                    "## Introduction",
                    "text",
                    "## Methods",
                    "See Figure 1.",
                    "## Results",
                    "text",
                    "## Discussion",
                    "text",
                ]
            )
        )

        r = validator.validate_phase(5)
        assert not r.passed
        failed = next(c for c in r.checks if c.name == "asset-plan:fig-1:registered")
        assert failed.passed is False

    def test_fail_required_planned_figure_without_exportable_asset(self, validator, project_dir):
        import yaml

        _add_prerequisites(project_dir, up_to_phase=5)
        (project_dir / "results" / "figures").mkdir(parents=True)
        (project_dir / "results" / "figures" / "study-flow.drawio").write_text("xml")
        (project_dir / "results" / "manifest.json").write_text(
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
        (project_dir / "drafts" / "manuscript.md").write_text(
            "\n".join(
                [
                    "# Title",
                    "## Abstract",
                    "text",
                    "## Introduction",
                    "text",
                    "## Methods",
                    "![Figure 1. Study flow diagram](../results/figures/study-flow.drawio)",
                    "**Figure 1.** Study flow diagram",
                    "See Figure 1.",
                    "## Results",
                    "text",
                    "## Discussion",
                    "text",
                ]
            )
        )

        r = validator.validate_phase(5)
        assert not r.passed
        failed = next(c for c in r.checks if c.name == "asset-plan:fig-1:exportable")
        assert failed.passed is False

    def test_pass_required_planned_assets_when_registered_and_placed(self, validator, project_dir):
        import yaml

        _add_prerequisites(project_dir, up_to_phase=5)
        (project_dir / "results" / "figures").mkdir(parents=True)
        (project_dir / "results" / "tables").mkdir(parents=True)
        (project_dir / "results" / "figures" / "study-flow.drawio").write_text("xml")
        (project_dir / "results" / "figures" / "study-flow.png").write_bytes(b"png")
        (project_dir / "results" / "tables" / "baseline.md").write_text("| a | b |")
        (project_dir / ".audit" / "data-artifacts.yaml").write_text(
            yaml.dump(
                {
                    "artifacts": [
                        {"id": "fig-1", "kind": "figure"},
                        {"id": "table-1", "kind": "table"},
                    ]
                }
            )
        )
        (project_dir / "results" / "manifest.json").write_text(
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
        (project_dir / "drafts" / "manuscript.md").write_text(
            "\n".join(
                [
                    "# Title",
                    "## Abstract",
                    "text",
                    "## Introduction",
                    "text",
                    "## Methods",
                    "![Figure 1. Study flow diagram](../results/figures/study-flow.png)",
                    "**Figure 1.** Study flow diagram",
                    "See Figure 1.",
                    "## Results",
                    "**Table 1.** Baseline characteristics of study participants",
                    "See Table 1 for baseline characteristics.",
                    "## Discussion",
                    "text",
                ]
            )
        )

        r = validator.validate_phase(5)
        assert r.passed


class TestPhase7:
    """Phase 7 is the most critical gate — tests the review loop enforcement."""

    def test_fail_no_review_artifacts(self, validator):
        """Without any review artifacts, Phase 7 must FAIL."""
        r = validator.validate_phase(7)
        assert not r.passed
        names = [c.name for c in r.critical_failures]
        assert "audit-loop:state" in names
        assert "review:rounds_completed" in names

    def test_fail_partial_round(self, validator, project_dir):
        """Even with loop state but missing artifacts, must FAIL."""
        audit = project_dir / ".audit"
        state = {
            "config": {"max_rounds": 3},
            "rounds": [{"round": 1, "verdict": "continue"}],
        }
        (audit / "audit-loop-review.json").write_text(json.dumps(state))
        # Missing review-report-1.md, author-response-1.md, equator
        r = validator.validate_phase(7)
        assert not r.passed
        names = [c.name for c in r.critical_failures]
        assert "review:review-report-1.md" in names
        assert "review:author-response-1.md" in names

    def test_pass_complete_review(self, validator, project_dir):
        """Full review loop with all artifacts should PASS."""
        _add_prerequisites(project_dir, up_to_phase=7)
        audit = project_dir / ".audit"
        state = {
            "config": {"max_rounds": 3},
            "rounds": [
                {"round": 1, "verdict": "continue"},
                {"round": 2, "verdict": "quality_met"},
            ],
        }
        (audit / "audit-loop-review.json").write_text(json.dumps(state))
        for i in [1, 2]:
            (audit / f"review-report-{i}.md").write_text(f"# Round {i}")
            (audit / f"author-response-{i}.md").write_text(f"# Response {i}")
            (audit / f"equator-compliance-{i}.md").write_text(f"# EQUATOR {i}")

        # evolution-log with review_round events
        entries = [
            json.dumps({"event": "review_round", "round": 1}),
            json.dumps({"event": "review_round", "round": 2}),
        ]
        (audit / "evolution-log.jsonl").write_text("\n".join(entries) + "\n")

        r = validator.validate_phase(7)
        assert r.passed


class TestPhase65:
    def test_fail_no_baseline(self, validator, project_dir):
        r = validator.validate_phase(65)
        assert not r.passed

    def test_pass_with_baseline(self, validator, project_dir):
        _add_prerequisites(project_dir, up_to_phase=65)
        audit = project_dir / ".audit"
        entries = [json.dumps({"event": "baseline", "round": 0})]
        (audit / "evolution-log.jsonl").write_text("\n".join(entries) + "\n")
        (audit / "quality-scorecard.md").write_text("# Scorecard")
        r = validator.validate_phase(65)
        assert r.passed


class TestHeartbeat:
    def test_heartbeat_returns_status(self, validator):
        status = validator.get_pipeline_status()
        assert "completion_pct" in status
        assert "phases" in status
        assert len(status["phases"]) == 13

    def test_heartbeat_reflects_progress(self, validator, project_dir):
        # Add journal-profile → Phase 0 passes
        (project_dir / "journal-profile.yaml").write_text("type: original")
        status = validator.get_pipeline_status()
        phase_0 = [p for p in status["phases"] if p["phase"] == 0][0]
        assert phase_0["passed"] is True


class TestGateLogging:
    def test_gate_validation_logged(self, validator, project_dir):
        validator.validate_phase(0)
        log_file = project_dir / ".audit" / "gate-validations.jsonl"
        assert log_file.is_file()
        entry = json.loads(log_file.read_text().strip().split("\n")[0])
        assert entry["phase"] == 0
        assert "passed" in entry


class TestProjectStructure:
    """Tests for validate_project_structure — independent of pipeline."""

    def test_empty_project_reports_missing(self, project_dir):
        """Bare project dir should fail on project.json and concept."""
        # Remove the dirs that the fixture auto-creates
        import shutil

        from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
            PipelineGateValidator,
        )

        for d in project_dir.iterdir():
            if d.is_dir():
                shutil.rmtree(d)
        v = PipelineGateValidator(project_dir)
        r = v.validate_project_structure()
        assert r.phase == -1
        assert r.phase_name == "Project Structure"
        # project.json missing → CRITICAL → overall fail
        pj_check = next(c for c in r.checks if c.name == "project.json")
        assert not pj_check.passed

    def test_complete_project_passes(self, validator, project_dir):
        """Project with all required dirs + project.json passes."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        (project_dir / "concept.md").write_text("# Concept")
        (project_dir / ".memory" / "activeContext.md").write_text("# Active")
        (project_dir / ".memory" / "progress.md").write_text("# Progress")
        r = validator.validate_project_structure()
        assert r.passed

    def test_concept_in_drafts_accepted(self, validator, project_dir):
        """concept.md in drafts/ should also pass."""
        (project_dir / "project.json").write_text('{"slug": "test"}')
        (project_dir / "drafts" / "concept.md").write_text("# Concept")
        r = validator.validate_project_structure()
        concept_check = next(c for c in r.checks if c.name == "concept.md")
        assert concept_check.passed


class TestPrerequisiteChecks:
    """Tests for _check_prerequisites prepended in validate_phase for phase > 1."""

    def test_phase_1_no_prereqs(self, validator, project_dir):
        """Phase 1 should NOT have prerequisite checks."""
        r = validator.validate_phase(1)
        prereq_checks = [c for c in r.checks if c.name.startswith("prereq:")]
        assert len(prereq_checks) == 0

    def test_phase_2_has_project_json_prereq(self, validator, project_dir):
        """Phase 2 should prepend prereq:project.json check."""
        r = validator.validate_phase(2)
        prereq_checks = [c for c in r.checks if c.name.startswith("prereq:")]
        assert len(prereq_checks) == 1
        assert prereq_checks[0].name == "prereq:project.json"
        assert prereq_checks[0].severity == "CRITICAL"

    def test_phase_5_has_concept_prereq(self, validator, project_dir):
        """Phase 5 should check concept.md prerequisite."""
        r = validator.validate_phase(5)
        prereq_names = [c.name for c in r.checks if c.name.startswith("prereq:")]
        assert "prereq:project.json" in prereq_names
        assert "prereq:references" in prereq_names
        assert "prereq:concept.md" in prereq_names

    def test_phase_7_has_manuscript_prereq(self, validator, project_dir):
        """Phase 7 should check manuscript.md prerequisite."""
        r = validator.validate_phase(7)
        prereq_names = [c.name for c in r.checks if c.name.startswith("prereq:")]
        assert "prereq:manuscript.md" in prereq_names

    def test_prereqs_are_critical_blocking(self, validator, project_dir):
        """Prerequisite failures should be CRITICAL — blocking phase progression."""
        r = validator.validate_phase(5)
        prereq_fails = [c for c in r.checks if c.name.startswith("prereq:") and not c.passed]
        assert len(prereq_fails) > 0
        for c in prereq_fails:
            assert c.severity == "CRITICAL"
