"""Tests for DomainConstraintEngine — Triad-inspired JSON constraint system."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from med_paper_assistant.infrastructure.persistence.domain_constraint_engine import (
    BASE_CONSTRAINTS,
    ConstraintCategory,
    ConstraintViolation,
    DomainConstraintEngine,
)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    return tmp_path / "test-project"


@pytest.fixture
def engine(project_dir: Path) -> DomainConstraintEngine:
    """Create a DomainConstraintEngine for original-research."""
    project_dir.mkdir(parents=True, exist_ok=True)
    return DomainConstraintEngine(project_dir, paper_type="original-research")


@pytest.fixture
def case_engine(project_dir: Path) -> DomainConstraintEngine:
    """Create a DomainConstraintEngine for case-report."""
    project_dir.mkdir(parents=True, exist_ok=True)
    return DomainConstraintEngine(project_dir, paper_type="case-report")


# ── Base Constraints ──────────────────────────────────────────────


class TestBaseConstraints:
    """Test base constraint templates."""

    def test_base_has_original_research(self) -> None:
        assert "original-research" in BASE_CONSTRAINTS

    def test_base_has_case_report(self) -> None:
        assert "case-report" in BASE_CONSTRAINTS

    def test_base_has_systematic_review(self) -> None:
        assert "systematic-review" in BASE_CONSTRAINTS

    def test_original_research_has_constraints(self) -> None:
        constraints = BASE_CONSTRAINTS["original-research"]["constraints"]
        assert len(constraints) >= 10

    def test_case_report_has_fewer_constraints(self) -> None:
        or_count = len(BASE_CONSTRAINTS["original-research"]["constraints"])
        cr_count = len(BASE_CONSTRAINTS["case-report"]["constraints"])
        assert cr_count < or_count

    def test_constraints_have_required_fields(self) -> None:
        for paper_type, template in BASE_CONSTRAINTS.items():
            for c in template["constraints"]:
                assert "id" in c, f"Missing id in {paper_type}"
                assert "category" in c, f"Missing category in {paper_type}: {c}"
                assert "rule" in c, f"Missing rule in {paper_type}: {c}"
                assert "severity" in c, f"Missing severity in {paper_type}: {c}"
                assert "provenance" in c, f"Missing provenance in {paper_type}: {c}"
                assert c["severity"] in ("INFO", "WARNING", "CRITICAL")

    def test_constraint_ids_unique_per_type(self) -> None:
        for paper_type, template in BASE_CONSTRAINTS.items():
            ids = [c["id"] for c in template["constraints"]]
            assert len(ids) == len(set(ids)), f"Duplicate IDs in {paper_type}: {ids}"


# ── Get Active Constraints ────────────────────────────────────────


class TestGetActiveConstraints:
    """Test constraint loading and merging."""

    def test_returns_base_when_no_learned(self, engine: DomainConstraintEngine) -> None:
        constraints = engine.get_active_constraints()
        base_count = len(BASE_CONSTRAINTS["original-research"]["constraints"])
        assert len(constraints) == base_count

    def test_unknown_paper_type_returns_empty(self, project_dir: Path) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        eng = DomainConstraintEngine(project_dir, paper_type="nonexistent")
        assert eng.get_active_constraints() == []

    def test_learned_constraints_appended(self, engine: DomainConstraintEngine) -> None:
        base_count = len(engine.get_active_constraints())
        engine.evolve(
            constraint_id="L001",
            rule="no_passive_voice",
            category=ConstraintCategory.VOCABULARY,
            description="Avoid passive voice in Results",
            reason="test",
        )
        merged = engine.get_active_constraints()
        assert len(merged) == base_count + 1

    def test_severity_escalation(self, engine: DomainConstraintEngine) -> None:
        """Learned constraint can escalate severity of base constraint."""
        # V001 is WARNING in base
        engine._constraints_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "paper_type": "original-research",
            "constraints": [
                {
                    "id": "V001",
                    "category": "vocabulary",
                    "rule": "language_consistency",
                    "description": "Escalated",
                    "severity": "CRITICAL",
                    "provenance": "learned",
                }
            ],
        }
        engine._learned_path.write_text(json.dumps(data), encoding="utf-8")

        merged = engine.get_active_constraints()
        v001 = next(c for c in merged if c["id"] == "V001")
        assert v001["severity"] == "CRITICAL"

    def test_severity_cannot_weaken(self, engine: DomainConstraintEngine) -> None:
        """Learned constraint cannot weaken base severity."""
        # R001 is CRITICAL in base — trying to weaken to INFO
        engine._constraints_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "paper_type": "original-research",
            "constraints": [
                {
                    "id": "R001",
                    "category": "structural",
                    "rule": "required_sections",
                    "description": "Weakened",
                    "severity": "INFO",
                    "provenance": "learned",
                }
            ],
        }
        engine._learned_path.write_text(json.dumps(data), encoding="utf-8")

        merged = engine.get_active_constraints()
        r001 = next(c for c in merged if c["id"] == "R001")
        assert r001["severity"] == "CRITICAL"  # Unchanged

    def test_corrupt_learned_file_graceful(self, engine: DomainConstraintEngine) -> None:
        """Corrupt JSON doesn't crash, falls back to base only."""
        engine._constraints_dir.mkdir(parents=True, exist_ok=True)
        engine._learned_path.write_text("not valid json", encoding="utf-8")

        constraints = engine.get_active_constraints()
        base_count = len(BASE_CONSTRAINTS["original-research"]["constraints"])
        assert len(constraints) == base_count


# ── Evolve ────────────────────────────────────────────────────────


class TestEvolve:
    """Test constraint evolution."""

    def test_evolve_creates_constraints_dir(self, engine: DomainConstraintEngine) -> None:
        engine.evolve(
            constraint_id="L001",
            rule="test_rule",
            category=ConstraintCategory.STATISTICAL,
            description="Test constraint",
            reason="test",
        )
        assert engine._constraints_dir.is_dir()
        assert engine._learned_path.is_file()

    def test_evolve_adds_constraint(self, engine: DomainConstraintEngine) -> None:
        result = engine.evolve(
            constraint_id="L001",
            rule="no_passive_voice",
            category=ConstraintCategory.VOCABULARY,
            description="Avoid passive voice",
            severity="WARNING",
            reason="Detected in 3 projects",
            source_hook="A5",
        )
        assert result["id"] == "L001"
        assert result["provenance"] == "learned"
        assert result["source_hook"] == "A5"
        assert "learned_at" in result

        learned = engine._load_learned_constraints()
        assert len(learned) == 1

    def test_evolve_no_duplicates(self, engine: DomainConstraintEngine) -> None:
        engine.evolve(
            constraint_id="L001",
            rule="test",
            category=ConstraintCategory.VOCABULARY,
            description="Test",
            reason="first",
        )
        engine.evolve(
            constraint_id="L001",
            rule="test",
            category=ConstraintCategory.VOCABULARY,
            description="Test duplicate",
            reason="second",
        )
        learned = engine._load_learned_constraints()
        assert len(learned) == 1

    def test_evolve_logs_evolution(self, engine: DomainConstraintEngine) -> None:
        engine.evolve(
            constraint_id="L001",
            rule="test",
            category=ConstraintCategory.VOCABULARY,
            description="Test",
            reason="pattern found",
        )
        log = engine.get_evolution_history()
        assert len(log) == 1
        assert log[0]["action"] == "add"
        assert log[0]["constraint"]["id"] == "L001"

    def test_evolve_with_params(self, engine: DomainConstraintEngine) -> None:
        engine.evolve(
            constraint_id="L002",
            rule="max_acronyms",
            category=ConstraintCategory.VOCABULARY,
            description="Limit acronyms",
            params={"max_undefined_acronyms": 3},
            reason="too many undefined acronyms",
        )
        learned = engine._load_learned_constraints()
        assert learned[0]["params"]["max_undefined_acronyms"] == 3

    def test_multiple_evolutions(self, engine: DomainConstraintEngine) -> None:
        for i in range(5):
            engine.evolve(
                constraint_id=f"L{i:03d}",
                rule=f"rule_{i}",
                category=ConstraintCategory.VOCABULARY,
                description=f"Rule {i}",
                reason=f"Reason {i}",
            )
        learned = engine._load_learned_constraints()
        assert len(learned) == 5
        log = engine.get_evolution_history()
        assert len(log) == 5


# ── Validate Against Constraints ──────────────────────────────────


class TestValidateAgainstConstraints:
    """Test content validation (Sand Spreader)."""

    def test_clean_content_passes(self, engine: DomainConstraintEngine) -> None:
        content = """## Introduction
        This is research about medical devices.

        ## Methods
        We conducted a study of patients.

        ## Results
        The findings show improvement.

        ## Discussion
        Our results suggest efficacy.

        ## Conclusion
        We conclude that the device works.
        """
        result = engine.validate_against_constraints(content, section="manuscript")
        assert result["critical_count"] == 0
        assert result["passed"] is True

    def test_ai_vocabulary_detected(self, engine: DomainConstraintEngine) -> None:
        content = "It is worth noting that this study delve into the multifaceted aspects."
        result = engine.validate_against_constraints(content, section="introduction")
        violations = result["violations"]
        ai_violations = [v for v in violations if v["rule"] == "anti_ai_vocabulary"]
        assert len(ai_violations) >= 2  # "it is worth noting" and "delve into"

    def test_word_count_too_low(self, engine: DomainConstraintEngine) -> None:
        content = "Short text."
        result = engine.validate_against_constraints(content, section="manuscript")
        wc_violations = [v for v in result["violations"] if v["rule"] == "word_count_range"]
        assert len(wc_violations) == 1
        assert "below minimum" in wc_violations[0]["message"]

    def test_word_count_too_high(self, engine: DomainConstraintEngine) -> None:
        content = "word " * 6000  # 6000 words
        result = engine.validate_against_constraints(content, section="manuscript")
        wc_violations = [v for v in result["violations"] if v["rule"] == "word_count_range"]
        assert len(wc_violations) == 1
        assert "exceeds maximum" in wc_violations[0]["message"]

    def test_missing_required_section(self, engine: DomainConstraintEngine) -> None:
        content = """## Introduction
        Research content.

        ## Methods
        Study methods.

        ## Discussion
        Discussion points.
        """
        result = engine.validate_against_constraints(content, section="manuscript")
        missing = [v for v in result["violations"] if v["rule"] == "required_sections"]
        section_names = [v["message"] for v in missing]
        assert any("Results" in m for m in section_names)
        assert any("Conclusion" in m for m in section_names)

    def test_result_includes_counts(self, engine: DomainConstraintEngine) -> None:
        result = engine.validate_against_constraints("test", section="manuscript")
        assert "total_constraints" in result
        assert "base_constraints" in result
        assert "learned_constraints" in result
        assert result["learned_constraints"] == 0

    def test_case_report_different_sections(self, case_engine: DomainConstraintEngine) -> None:
        """Case report requires different sections than original-research."""
        content = """## Introduction
        Case intro.

        ## Case Presentation
        Patient story.

        ## Discussion
        Discussion.

        ## Conclusion
        Conclusions.
        """
        result = case_engine.validate_against_constraints(content, section="manuscript")
        missing = [v for v in result["violations"] if v["rule"] == "required_sections"]
        assert len(missing) == 0  # All required sections present

    def test_learned_constraint_validated(self, engine: DomainConstraintEngine) -> None:
        """Learned constraint should also be checked during validation."""
        engine.evolve(
            constraint_id="L001",
            rule="anti_ai_vocabulary",
            category=ConstraintCategory.VOCABULARY,
            description="Extra forbidden phrase",
            params={"forbidden_patterns": ["it goes without saying"]},
            reason="test",
        )
        content = "It goes without saying that the results were significant."
        result = engine.validate_against_constraints(content, section="introduction")
        ai_viol = [v for v in result["violations"] if v["constraint_id"] == "L001"]
        assert len(ai_viol) == 1


# ── Constraint Summary ────────────────────────────────────────────


class TestConstraintSummary:
    """Test constraint summary reporting."""

    def test_summary_structure(self, engine: DomainConstraintEngine) -> None:
        summary = engine.get_constraint_summary()
        assert "paper_type" in summary
        assert "total_constraints" in summary
        assert "by_category" in summary
        assert "by_severity" in summary
        assert "by_provenance" in summary

    def test_summary_counts_match(self, engine: DomainConstraintEngine) -> None:
        summary = engine.get_constraint_summary()
        total_by_sev = sum(summary["by_severity"].values())
        assert total_by_sev == summary["total_constraints"]

    def test_summary_includes_learned(self, engine: DomainConstraintEngine) -> None:
        engine.evolve(
            constraint_id="L001",
            rule="test",
            category=ConstraintCategory.BOUNDARY,
            description="Test",
            reason="test",
        )
        summary = engine.get_constraint_summary()
        assert summary["by_provenance"]["learned"] == 1
        assert summary["evolution_events"] == 1


# ── ConstraintViolation ──────────────────────────────────────────


class TestConstraintViolation:
    """Test ConstraintViolation dataclass."""

    def test_to_dict(self) -> None:
        v = ConstraintViolation(
            constraint_id="S001",
            rule="test_rule",
            category="statistical",
            severity="CRITICAL",
            message="Test message",
            section="methods",
            suggestion="Fix it",
        )
        d = v.to_dict()
        assert d["constraint_id"] == "S001"
        assert d["severity"] == "CRITICAL"
        assert d["suggestion"] == "Fix it"


# ── Evolution History ─────────────────────────────────────────────


class TestEvolutionHistory:
    """Test evolution history tracking."""

    def test_empty_when_no_evolution(self, engine: DomainConstraintEngine) -> None:
        assert engine.get_evolution_history() == []

    def test_tracks_all_evolutions(self, engine: DomainConstraintEngine) -> None:
        for i in range(3):
            engine.evolve(
                constraint_id=f"L{i:03d}",
                rule=f"rule_{i}",
                category=ConstraintCategory.VOCABULARY,
                description=f"Rule {i}",
                reason=f"Pattern from project {i}",
            )
        history = engine.get_evolution_history()
        assert len(history) == 3
        assert all(h["action"] == "add" for h in history)

    def test_corrupt_evolution_log_graceful(self, engine: DomainConstraintEngine) -> None:
        engine._constraints_dir.mkdir(parents=True, exist_ok=True)
        engine._evolution_log_path.write_text("not json", encoding="utf-8")
        assert engine.get_evolution_history() == []
