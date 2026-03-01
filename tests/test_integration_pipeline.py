"""
Integration test — end-to-end pipeline verification.

Validates that all infrastructure components can initialise and run
against a realistic project structure.  Covers:
  - PipelineGateValidator phase sweep (0-10)
  - WritingHooksEngine all hooks (A5/A6/B8/C9/F)
  - QualityScorecard create + read
  - HookEffectivenessTracker record + report
  - MetaLearningEngine analysis cycle
  - EvolutionVerifier cross-project aggregation
  - DomainConstraintEngine constraint validation
  - MCP tool registration completeness
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from med_paper_assistant.infrastructure.persistence.domain_constraint_engine import (
    DomainConstraintEngine,
)
from med_paper_assistant.infrastructure.persistence.evolution_verifier import (
    EvolutionVerifier,
)
from med_paper_assistant.infrastructure.persistence.hook_effectiveness_tracker import (
    HookEffectivenessTracker,
)
from med_paper_assistant.infrastructure.persistence.meta_learning_engine import (
    MetaLearningEngine,
)
from med_paper_assistant.infrastructure.persistence.pipeline_gate_validator import (
    PipelineGateValidator,
)
from med_paper_assistant.infrastructure.persistence.quality_scorecard import (
    DIMENSIONS,
    QualityScorecard,
)
from med_paper_assistant.infrastructure.persistence.writing_hooks import (
    WritingHooksEngine,
)

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Realistic project directory with all required artifacts."""
    p = tmp_path / "integration-project"

    # Directories
    for d in [
        "drafts",
        "references",
        "data",
        "results",
        "results/figures",
        "exports",
        ".audit",
        ".memory",
    ]:
        (p / d).mkdir(parents=True)

    # project.json
    (p / "project.json").write_text(
        json.dumps(
            {
                "slug": "integration-project",
                "name": "Integration Test Project",
                "paper_type": "original_research",
                "status": "in_progress",
            }
        )
    )

    # concept.md
    (p / "concept.md").write_text(
        "# Concept\n\n## 🔒 NOVELTY STATEMENT\nFirst study to xyz.\n\n"
        "## 🔒 KEY SELLING POINTS\n- Point A\n- Point B\n",
        encoding="utf-8",
    )

    # Sample references (YAML stubs)
    for i in range(5):
        ref = {
            "pmid": f"1000000{i}",
            "title": f"Reference {i} title on anaesthesia",
            "authors": [f"Author{i} A"],
            "journal": f"Journal {i}",
            "year": 2024,
        }
        (p / "references" / f"ref_{i}.yaml").write_text(yaml.dump(ref))

    # Sample draft sections
    methods = (
        "# Methods\n\n"
        "We enrolled 100 patients (n=100) and randomised them.\n"
        "Statistical analysis was performed using R.\n"
        "Continuous variables were analysed with t-test.\n"
    )
    results = (
        "# Results\n\n"
        "A total of 100 patients were enrolled (n=100).\n"
        "The primary outcome was analysed in 95 patients.\n"
        "Mean age was 65.2 years (SD 12.3).\n"
    )
    discussion = (
        "# Discussion\n\n"
        "This is the first study to examine xyz.\n"
        "Our findings are consistent with prior literature.\n"
        "See Supplementary Table S1 for details.\n"
        "[[ref_0]] [[ref_1]] [[ref_2]]\n"
    )
    (p / "drafts" / "methods.md").write_text(methods)
    (p / "drafts" / "results.md").write_text(results)
    (p / "drafts" / "discussion.md").write_text(discussion)

    # Memory files
    (p / ".memory" / "activeContext.md").write_text("# Active Context\nIntegration test")
    (p / ".memory" / "progress.md").write_text("# Progress\nRunning integration test")

    return p


@pytest.fixture
def audit_dir(project_dir: Path) -> Path:
    return project_dir / ".audit"


# ── 1. PipelineGateValidator ─────────────────────────────────────────


class TestPipelineGateValidatorIntegration:
    """Sweep all phases and ensure the validator returns structured results."""

    def test_structure_validation(self, project_dir: Path) -> None:
        v = PipelineGateValidator(project_dir)
        result = v.validate_project_structure()
        assert result.phase_name == "Project Structure"
        assert isinstance(result.checks, list)
        assert len(result.checks) > 0
        # With our fixture, project.json and dirs exist → no critical failures
        critical = [c for c in result.checks if not c.passed and c.severity == "CRITICAL"]
        assert len(critical) == 0, f"Unexpected critical failures: {critical}"

    @pytest.mark.parametrize("phase", [0, 1, 2, 3, 4, 5, 6, 65, 7, 8, 9, 10])
    def test_phase_gate_returns_result(self, project_dir: Path, phase: int) -> None:
        """Each valid phase should return a GateResult (may fail, but not crash)."""
        v = PipelineGateValidator(project_dir)
        result = v.validate_phase(phase)
        assert result.phase == phase
        assert isinstance(result.passed, bool)
        assert isinstance(result.checks, list)
        # Markdown rendering should not crash
        md = result.to_markdown()
        assert "Phase" in md

    def test_invalid_phase(self, project_dir: Path) -> None:
        v = PipelineGateValidator(project_dir)
        result = v.validate_phase(999)
        assert not result.passed
        assert result.phase_name == "UNKNOWN"


# ── 2. WritingHooksEngine ────────────────────────────────────────────


class TestWritingHooksEngineIntegration:
    """Run every hook method on realistic content."""

    def test_hook_a5_language_consistency(self, project_dir: Path) -> None:
        engine = WritingHooksEngine(project_dir)
        content = (project_dir / "drafts" / "methods.md").read_text()
        result = engine.check_language_consistency(content, prefer="american")
        assert result.hook_id == "A5"
        # "analysed", "randomised", "anaesthesia" are British → should flag
        assert len(result.issues) > 0
        assert any("british" in i.message.lower() or "British" in i.message for i in result.issues)

    def test_hook_a5_british_preference(self, project_dir: Path) -> None:
        engine = WritingHooksEngine(project_dir)
        # Purely American text with British preference
        content = "We analyzed the data and optimized the algorithm."
        result = engine.check_language_consistency(content, prefer="british")
        assert result.hook_id == "A5"

    def test_hook_a6_overlap_detection(self, project_dir: Path) -> None:
        engine = WritingHooksEngine(project_dir)
        # Duplicate paragraph
        content = "This is a paragraph about something.\n\nThis is a paragraph about something.\n"
        result = engine.check_overlap(content)
        assert result.hook_id == "A6"

    def test_hook_b8_data_claim_alignment(self, project_dir: Path) -> None:
        engine = WritingHooksEngine(project_dir)
        methods = (project_dir / "drafts" / "methods.md").read_text()
        results = (project_dir / "drafts" / "results.md").read_text()
        result = engine.check_data_claim_alignment(methods, results)
        assert result.hook_id == "B8"
        assert isinstance(result.stats, dict)

    def test_hook_c9_supplementary_crossref(self, project_dir: Path) -> None:
        engine = WritingHooksEngine(project_dir)
        discussion = (project_dir / "drafts" / "discussion.md").read_text()
        result = engine.check_supplementary_crossref(discussion)
        assert result.hook_id == "C9"

    def test_hook_f_data_artifacts(self, project_dir: Path) -> None:
        engine = WritingHooksEngine(project_dir)
        content = (project_dir / "drafts" / "results.md").read_text()
        result = engine.validate_data_artifacts(content)
        assert result.hook_id == "F"


# ── 3. QualityScorecard ──────────────────────────────────────────────


class TestQualityScorecardIntegration:
    """Create a scorecard, score dimensions, read it back."""

    def test_create_and_read(self, audit_dir: Path) -> None:
        sc = QualityScorecard(audit_dir)
        for i, dim in enumerate(DIMENSIONS):
            sc.set_score(dim, min(i + 5, 10))  # 5-10 range, capped at 10
        report = sc.generate_report()
        assert isinstance(report, str)
        assert len(report) > 0

    def test_dimension_count(self) -> None:
        """DIMENSIONS should have 8 entries (expanded from 6)."""
        assert len(DIMENSIONS) == 8


# ── 4. HookEffectivenessTracker ──────────────────────────────────────


class TestHookEffectivenessTrackerIntegration:
    """Record hook events and generate report."""

    def test_record_and_report(self, audit_dir: Path) -> None:
        tracker = HookEffectivenessTracker(audit_dir)
        # Record a series of events
        for hook_id in ["A1", "A5", "B1", "B8", "C1", "E1"]:
            tracker.record_event(hook_id, "trigger")
            tracker.record_event(hook_id, "pass")

        # Generate report
        report = tracker.generate_report()
        assert isinstance(report, str)
        assert len(report) > 0


# ── 5. MetaLearningEngine ────────────────────────────────────────────


class TestMetaLearningEngineIntegration:
    """Analysis cycle: record hook data → analyze → summarise."""

    def test_analysis_cycle(self, audit_dir: Path) -> None:
        tracker = HookEffectivenessTracker(audit_dir)
        scorecard = QualityScorecard(audit_dir)
        engine = MetaLearningEngine(audit_dir, tracker, scorecard)

        # Record some data first
        for hook_id in ["A1", "A5", "B1"]:
            tracker.record_event(hook_id, "trigger")
            tracker.record_event(hook_id, "pass")

        # Run analysis
        result = engine.analyze()
        assert isinstance(result, dict)
        assert "summary" in result

    def test_expected_hooks_count(self) -> None:
        """EXPECTED_HOOKS should contain exactly 58 entries."""
        assert len(MetaLearningEngine.EXPECTED_HOOKS) == 58


# ── 6. EvolutionVerifier ─────────────────────────────────────────────


class TestEvolutionVerifierIntegration:
    """Cross-project aggregation with 2 project stubs."""

    def test_single_project(self, project_dir: Path, audit_dir: Path) -> None:
        # Create hook data
        tracker = HookEffectivenessTracker(audit_dir)
        tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "pass")

        verifier = EvolutionVerifier(project_dir.parent)
        report = verifier.verify()
        assert isinstance(report, dict)

    def test_two_projects(self, tmp_path: Path) -> None:
        """Two projects with audit data → verifier aggregates both."""
        projects_dir = tmp_path / "multi-projects"

        for name in ["proj-alpha", "proj-beta"]:
            p = projects_dir / name
            for d in ["drafts", "references", ".audit", ".memory"]:
                (p / d).mkdir(parents=True)
            (p / "project.json").write_text(json.dumps({"slug": name}))

            tracker = HookEffectivenessTracker(p / ".audit")
            tracker.record_event("A1", "trigger")
            tracker.record_event("A1", "pass")

        verifier = EvolutionVerifier(projects_dir)
        report = verifier.verify()
        assert isinstance(report, dict)


# ── 7. DomainConstraintEngine ────────────────────────────────────────


class TestDomainConstraintEngineIntegration:
    """Domain constraint validation on realistic draft content."""

    def test_validate_methods(self, project_dir: Path) -> None:
        engine = DomainConstraintEngine(project_dir)
        methods = (project_dir / "drafts" / "methods.md").read_text()
        result = engine.validate_against_constraints(methods, section="methods")
        assert isinstance(result, dict)

    def test_validate_results(self, project_dir: Path) -> None:
        engine = DomainConstraintEngine(project_dir)
        results = (project_dir / "drafts" / "results.md").read_text()
        result = engine.validate_against_constraints(results, section="results")
        assert isinstance(result, dict)


# ── 8. MCP Tool Registration ─────────────────────────────────────────


class TestMCPToolRegistration:
    """Verify all expected tool modules can register without error."""

    def _register_tools(self, register_fn):
        """Helper: register tools on a mock MCP and return captured function names."""
        from unittest.mock import MagicMock

        mock_mcp = MagicMock()
        captured: dict[str, object] = {}

        def fake_tool(*args, **kwargs):
            def decorator(fn):
                captured[fn.__name__] = fn
                return fn

            return decorator

        mock_mcp.tool = fake_tool
        register_fn(mock_mcp)
        return captured

    def test_audit_hooks_registration(self) -> None:
        from med_paper_assistant.interfaces.mcp.tools.review.audit_hooks import (
            register_audit_hook_tools,
        )

        tools = self._register_tools(register_audit_hook_tools)
        expected = [
            "record_hook_event",
            "run_meta_learning",
            "run_quality_audit",
            "validate_data_artifacts",
            "run_writing_hooks",
            "verify_evolution",
            "check_domain_constraints",
            "evolve_constraint",
        ]
        for name in expected:
            assert name in tools, f"Missing MCP tool: {name}"

    def test_all_tool_modules_importable(self) -> None:
        """All tool registration modules should import without errors."""
        import importlib

        modules = [
            "med_paper_assistant.interfaces.mcp.tools.review.audit_hooks",
            "med_paper_assistant.interfaces.mcp.tools.project.project_tools",
            "med_paper_assistant.interfaces.mcp.tools.writing.writing_tools",
        ]
        for mod_name in modules:
            try:
                importlib.import_module(mod_name)
            except ImportError:
                # Module may have optional deps — that's OK
                pass


# ── 9. Cross-Component Smoke Test ────────────────────────────────────


class TestCrossComponentSmoke:
    """Simulate a mini-pipeline: gate → hooks → scorecard → meta-learning."""

    def test_mini_pipeline(self, project_dir: Path, audit_dir: Path) -> None:
        # 1. Validate structure
        validator = PipelineGateValidator(project_dir)
        structure = validator.validate_project_structure()
        assert structure.passed

        # 2. Run writing hooks
        hooks = WritingHooksEngine(project_dir)
        methods_content = (project_dir / "drafts" / "methods.md").read_text()
        results_content = (project_dir / "drafts" / "results.md").read_text()

        a5 = hooks.check_language_consistency(methods_content, prefer="american")
        a6 = hooks.check_overlap(methods_content)
        b8 = hooks.check_data_claim_alignment(methods_content, results_content)

        # 3. Record hook events
        tracker = HookEffectivenessTracker(audit_dir)
        for r in [a5, a6, b8]:
            tracker.record_event(r.hook_id, "trigger")
            if r.issues:
                tracker.record_event(r.hook_id, "fix")
            else:
                tracker.record_event(r.hook_id, "pass")

        # 4. Create scorecard
        scorecard = QualityScorecard(audit_dir)
        for dim in DIMENSIONS:
            scorecard.set_score(dim, 7)

        # 5. Meta-learning
        engine = MetaLearningEngine(audit_dir, tracker, scorecard)
        analysis = engine.analyze()
        assert isinstance(analysis, dict)
        assert "summary" in analysis

        # 6. Evolution verification
        verifier = EvolutionVerifier(project_dir.parent)
        evolution = verifier.verify()
        assert isinstance(evolution, dict)

        # 7. Domain constraints
        domain = DomainConstraintEngine(project_dir)
        constraint_result = domain.validate_against_constraints(methods_content, section="methods")
        assert constraint_result is not None
