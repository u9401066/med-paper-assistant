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
        assert "0 references" in ref_check.details

    def test_pass_with_refs(self, validator, project_dir):
        # Phase 2 prereqs: project.json
        (project_dir / "project.json").write_text('{"slug": "test"}')
        for i in range(10):
            (project_dir / "references" / f"ref-{i}.md").write_text(f"# Ref {i}")
        r = validator.validate_phase(2)
        assert r.passed


class TestPhase5:
    def test_fail_no_manuscript(self, validator):
        r = validator.validate_phase(5)
        assert not r.passed

    def test_fail_missing_sections(self, validator, project_dir):
        (project_dir / "drafts" / "manuscript.md").write_text("# Abstract\n\n## Introduction\n")
        r = validator.validate_phase(5)
        assert not r.passed  # missing Methods, Results, Discussion

    def test_pass_full_manuscript(self, validator, project_dir):
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
        assert len(status["phases"]) == 12

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
        assert prereq_checks[0].severity == "WARNING"

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

    def test_prereqs_are_warnings_not_blocking(self, validator, project_dir):
        """Prerequisite failures should be WARNING, not CRITICAL."""
        r = validator.validate_phase(5)
        prereq_fails = [c for c in r.checks if c.name.startswith("prereq:") and not c.passed]
        for c in prereq_fails:
            assert c.severity == "WARNING"
