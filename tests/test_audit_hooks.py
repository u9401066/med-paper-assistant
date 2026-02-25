"""Tests for hard audit hooks — MCP tool functions + validator enforcement."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

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

# ---------------------------------------------------------------------------
# We import the registration function so we can call the inner tool functions.
# register_audit_hook_tools(mcp) registers tools on a FastMCP instance AND
# returns a dict of callable tool functions.
# ---------------------------------------------------------------------------
from med_paper_assistant.interfaces.mcp.tools.review.audit_hooks import (
    register_audit_hook_tools,
)

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory structure."""
    p = tmp_path / "test-project"
    for d in ["drafts", "references", "data", "results", ".audit", ".memory", "exports"]:
        (p / d).mkdir(parents=True)
    return p


@pytest.fixture
def audit_dir(project_dir):
    return project_dir / ".audit"


@pytest.fixture
def validator(project_dir):
    return PipelineGateValidator(project_dir)


@pytest.fixture
def scorecard(audit_dir):
    return QualityScorecard(audit_dir)


@pytest.fixture
def tracker(audit_dir):
    return HookEffectivenessTracker(audit_dir)


@pytest.fixture
def engine(audit_dir, tracker, scorecard):
    return MetaLearningEngine(audit_dir, tracker, scorecard)


def _mock_project_context(project_dir: Path):
    """Return a mock for ensure_project_context that always succeeds with the given dir."""
    project_info = {
        "slug": "test-project",
        "name": "Test Project",
        "project_path": str(project_dir),
        "success": True,
    }
    return patch(
        "med_paper_assistant.interfaces.mcp.tools.review.audit_hooks.ensure_project_context",
        return_value=(True, "Working on project: Test Project", project_info),
    )


@pytest.fixture
def tool_funcs(project_dir):
    """Register audit hook tools on a mock MCP and return the callable functions."""
    from unittest.mock import MagicMock

    mock_mcp = MagicMock()
    # Capture inner functions: mcp.tool() returns a decorator, which is called with the func
    captured = {}

    def fake_tool(*args, **kwargs):
        def decorator(fn):
            captured[fn.__name__] = fn
            return fn

        return decorator

    mock_mcp.tool = fake_tool
    register_audit_hook_tools(mock_mcp)
    return captured


# ── MCP Tool: record_hook_event ───────────────────────────────────────


class TestRecordHookEventTool:
    """Test the record_hook_event MCP tool function directly."""

    def test_record_trigger(self, tool_funcs, project_dir, audit_dir):
        """Record a trigger event → file written, stats returned."""
        fn = tool_funcs["record_hook_event"]
        with _mock_project_context(project_dir):
            result = fn(hook_id="A1", event_type="trigger", project="test-project")

        assert "status: ok" in result
        assert "hook: A1" in result
        assert "event: trigger" in result

        # Verify persistence (YAML format)
        he_yaml = audit_dir / "hook-effectiveness.yaml"
        assert he_yaml.exists()
        data = yaml.safe_load(he_yaml.read_text())
        assert data["hooks"]["A1"]["trigger"] == 1

    def test_record_multiple_events(self, tool_funcs, project_dir, audit_dir):
        """Multiple events accumulate correctly."""
        fn = tool_funcs["record_hook_event"]
        with _mock_project_context(project_dir):
            fn(hook_id="B1", event_type="trigger")
            fn(hook_id="B1", event_type="fix")
            result = fn(hook_id="B1", event_type="pass")

        assert "status: ok" in result
        assert "hook: B1" in result
        # TOON stats row: triggers,passes,fixes,false_positives,...
        assert "1,1,1,0," in result

    def test_record_all_event_types(self, tool_funcs, project_dir, audit_dir):
        """All 4 valid event types accepted."""
        fn = tool_funcs["record_hook_event"]
        for evt in ("trigger", "pass", "fix", "false_positive"):
            with _mock_project_context(project_dir):
                result = fn(hook_id="C1", event_type=evt)
            assert "status: ok" in result

    def test_invalid_event_type(self, tool_funcs, project_dir):
        """Invalid event type → error before project context is even checked."""
        fn = tool_funcs["record_hook_event"]
        with _mock_project_context(project_dir):
            result = fn(hook_id="A1", event_type="invalid")
        assert "❌ Invalid event_type" in result
        assert "invalid" in result

    def test_no_project_context(self, tool_funcs):
        """No project active → error message."""
        fn = tool_funcs["record_hook_event"]
        with patch(
            "med_paper_assistant.interfaces.mcp.tools.review.audit_hooks.ensure_project_context",
            return_value=(False, "No project selected", None),
        ):
            result = fn(hook_id="A1", event_type="trigger")
        assert "❌" in result
        assert "No project selected" in result

    def test_record_feeds_phase6_gate(self, tool_funcs, project_dir, audit_dir, validator):
        """Events recorded via MCP tool → Phase 6 hook-effectiveness data check passes."""
        fn = tool_funcs["record_hook_event"]
        with _mock_project_context(project_dir):
            fn(hook_id="A1", event_type="trigger")
            fn(hook_id="A1", event_type="fix")
            fn(hook_id="B1", event_type="pass")

        # Also need scorecard data + .md files for full Phase 6
        for dim in DIMENSIONS:
            scorecard = QualityScorecard(audit_dir)
            scorecard.set_score(dim, 7, "ok")
        scorecard.generate_report()
        tracker = HookEffectivenessTracker(audit_dir)
        tracker.generate_report()

        r = validator.validate_phase(6)
        he_check = next(c for c in r.checks if c.name == "hook-effectiveness:data")
        assert he_check.passed, f"hook-effectiveness:data failed: {he_check.details}"


# ── MCP Tool: run_quality_audit ───────────────────────────────────────


class TestRunQualityAuditTool:
    """Test the run_quality_audit MCP tool function directly."""

    def test_full_audit(self, tool_funcs, project_dir, audit_dir):
        """Full 6-dimension audit → success report + files created."""
        fn = tool_funcs["run_quality_audit"]
        scores = json.dumps(
            {
                "citation_quality": 8,
                "methodology_reproducibility": 7,
                "text_quality": 8.5,
                "concept_consistency": 9,
                "format_compliance": 8,
                "figure_table_quality": 7,
            }
        )
        with _mock_project_context(project_dir):
            result = fn(scores=scores, project="test-project")

        assert "status: ok" in result
        assert "average_score:" in result
        assert "scored: 6/6" in result

        # Files created (YAML format)
        assert (audit_dir / "quality-scorecard.yaml").exists()
        assert (audit_dir / "quality-scorecard.md").exists()

    def test_insufficient_dimensions(self, tool_funcs, project_dir):
        """< 4 standard dimensions → rejected before project context."""
        fn = tool_funcs["run_quality_audit"]
        scores = json.dumps({"citation_quality": 8, "text_quality": 7})
        with _mock_project_context(project_dir):
            result = fn(scores=scores, project="test-project")

        assert "❌" in result
        assert "At least 4" in result

    def test_invalid_json_scores(self, tool_funcs, project_dir):
        """Malformed JSON → descriptive error."""
        fn = tool_funcs["run_quality_audit"]
        with _mock_project_context(project_dir):
            result = fn(scores="{not valid json", project="test-project")
        assert "❌ Invalid scores JSON" in result

    def test_empty_scores(self, tool_funcs, project_dir):
        """Empty dict → rejected."""
        fn = tool_funcs["run_quality_audit"]
        with _mock_project_context(project_dir):
            result = fn(scores="{}", project="test-project")
        assert "❌" in result
        assert "non-empty" in result

    def test_score_out_of_range(self, tool_funcs, project_dir):
        """Score > 10 → rejected."""
        fn = tool_funcs["run_quality_audit"]
        scores = json.dumps({dim: 11 for dim in DIMENSIONS})
        with _mock_project_context(project_dir):
            result = fn(scores=scores, project="test-project")
        assert "❌" in result
        assert "0-10" in result

    def test_score_negative(self, tool_funcs, project_dir):
        """Negative score → rejected."""
        fn = tool_funcs["run_quality_audit"]
        scores = json.dumps({dim: -1 for dim in DIMENSIONS})
        with _mock_project_context(project_dir):
            result = fn(scores=scores, project="test-project")
        assert "❌" in result
        assert "0-10" in result

    def test_non_numeric_score(self, tool_funcs, project_dir):
        """Non-numeric score → rejected."""
        fn = tool_funcs["run_quality_audit"]
        scores = json.dumps({DIMENSIONS[0]: "high"})
        with _mock_project_context(project_dir):
            result = fn(scores=scores, project="test-project")
        assert "❌" in result
        assert "must be a number" in result

    def test_audit_feeds_phase6_gate(self, tool_funcs, project_dir, audit_dir, validator):
        """run_quality_audit output → Phase 6 quality-scorecard:data check passes."""
        fn = tool_funcs["run_quality_audit"]
        scores = json.dumps({dim: 7 + i * 0.5 for i, dim in enumerate(DIMENSIONS)})
        with _mock_project_context(project_dir):
            fn(scores=scores)

        # Also need hook events for Phase 6
        tracker = HookEffectivenessTracker(audit_dir)
        tracker.record_event("A1", "trigger")
        tracker.generate_report()

        r = validator.validate_phase(6)
        qs_check = next(c for c in r.checks if c.name == "quality-scorecard:data")
        assert qs_check.passed, f"quality-scorecard:data failed: {qs_check.details}"

    def test_weak_dimensions_shown(self, tool_funcs, project_dir):
        """Low scores trigger weak dimension warning in output."""
        fn = tool_funcs["run_quality_audit"]
        scores = json.dumps(
            {
                "citation_quality": 3,  # weak
                "methodology_reproducibility": 4,  # weak
                "text_quality": 8,
                "concept_consistency": 8,
                "format_compliance": 8,
                "figure_table_quality": 8,
            }
        )
        with _mock_project_context(project_dir):
            result = fn(scores=scores)

        assert "weak_dimensions[" in result
        assert "citation_quality" in result

    def test_hook_effectiveness_included(self, tool_funcs, project_dir, audit_dir):
        """If hook events exist, audit report includes hook effectiveness table."""
        # Pre-populate hook events
        tracker = HookEffectivenessTracker(audit_dir)
        tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "fix")

        fn = tool_funcs["run_quality_audit"]
        scores = json.dumps({dim: 7 for dim in DIMENSIONS})
        with _mock_project_context(project_dir):
            result = fn(scores=scores)

        assert "hooks[" in result
        assert "A1" in result


# ── MCP Tool: run_meta_learning ───────────────────────────────────────


class TestRunMetaLearningTool:
    """Test the run_meta_learning MCP tool function directly."""

    def test_basic_analysis(self, tool_funcs, project_dir, audit_dir):
        """Basic run with some data → success report + audit files."""
        # Seed some data
        tracker = HookEffectivenessTracker(audit_dir)
        tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "fix")
        scorecard = QualityScorecard(audit_dir)
        scorecard.set_score("text_quality", 7, "ok")

        fn = tool_funcs["run_meta_learning"]
        with _mock_project_context(project_dir):
            result = fn(project="test-project")

        assert "status: ok" in result
        assert "test-project" in result

        # Verify files created (YAML format)
        assert (audit_dir / "meta-learning-audit.yaml").exists()
        assert (audit_dir / "evolution-log.jsonl").exists()

        # Verify evolution-log has meta_learning event
        elog = (audit_dir / "evolution-log.jsonl").read_text()
        events = [json.loads(line) for line in elog.strip().splitlines()]
        ml_events = [e for e in events if e.get("event") == "meta_learning"]
        assert len(ml_events) >= 1
        assert "adjustments_count" in ml_events[-1]
        assert "lessons_count" in ml_events[-1]
        assert "suggestions_count" in ml_events[-1]

    def test_empty_data_still_produces_audit(self, tool_funcs, project_dir, audit_dir):
        """Even with no prior data, engine.analyze() should still produce valid audit."""
        fn = tool_funcs["run_meta_learning"]
        with _mock_project_context(project_dir):
            result = fn()

        assert "status: ok" in result
        assert (audit_dir / "meta-learning-audit.yaml").exists()

    def test_no_project_context(self, tool_funcs):
        """No project active → error."""
        fn = tool_funcs["run_meta_learning"]
        with patch(
            "med_paper_assistant.interfaces.mcp.tools.review.audit_hooks.ensure_project_context",
            return_value=(False, "No project selected", None),
        ):
            result = fn()
        assert "❌" in result
        assert "No project selected" in result

    def test_meta_learning_feeds_phase10_gate(self, tool_funcs, project_dir, audit_dir, validator):
        """run_meta_learning output → Phase 10 meta-learning-audit:data check passes."""
        # Seed minimal data
        tracker = HookEffectivenessTracker(audit_dir)
        tracker.record_event("A1", "pass")
        scorecard = QualityScorecard(audit_dir)
        scorecard.set_score("text_quality", 7, "ok")

        fn = tool_funcs["run_meta_learning"]
        with _mock_project_context(project_dir):
            fn()

        # Setup remaining Phase 10 requirements
        (audit_dir / "pipeline-run-20260101.md").write_text("# Run\n## D7\nretro\n## D8\nequator\n")
        (audit_dir / "hook-effectiveness.md").write_text("# HE\n")
        (project_dir / ".memory" / "activeContext.md").write_text("# Active")
        (project_dir / ".memory" / "progress.md").write_text("# Progress")

        r = validator.validate_phase(10)
        mla_check = next(c for c in r.checks if c.name == "meta-learning-audit:data")
        assert mla_check.passed, f"meta-learning-audit:data failed: {mla_check.details}"


# ── End-to-End: MCP Tools → Phase Gates ──────────────────────────────


class TestEndToEndAuditPipeline:
    """Full pipeline simulation: MCP tools → Phase 6 → Phase 10 gates."""

    def test_full_phase6_via_tools(self, tool_funcs, project_dir, audit_dir, validator):
        """
        Simulate Phase 5/6 workflow:
        1. record_hook_event × N (during Phase 5 writing)
        2. run_quality_audit (before Phase 6 gate)
        3. validate_phase_gate(6) → PASS
        """
        rec = tool_funcs["record_hook_event"]
        audit = tool_funcs["run_quality_audit"]

        with _mock_project_context(project_dir):
            # Phase 5: hooks fire during writing
            rec(hook_id="A1", event_type="trigger")
            rec(hook_id="A1", event_type="fix")
            rec(hook_id="A2", event_type="pass")
            rec(hook_id="B1", event_type="trigger")
            rec(hook_id="B1", event_type="fix")
            rec(hook_id="C1", event_type="pass")
            rec(hook_id="C2", event_type="trigger")
            rec(hook_id="C2", event_type="false_positive")

            # Phase 6: run audit
            scores = json.dumps({dim: 7.5 for dim in DIMENSIONS})
            audit_result = audit(scores=scores)

        assert "status: ok" in audit_result
        # Hook effectiveness should show the hooks we recorded
        assert "A1" in audit_result
        assert "B1" in audit_result

        # Validate Phase 6
        r = validator.validate_phase(6)
        assert r.passed, (
            f"Phase 6 failed: {[c.name + ': ' + c.details for c in r.critical_failures]}"
        )

    def test_full_phase10_via_tools(self, tool_funcs, project_dir, audit_dir, validator):
        """
        Simulate Phase 10 workflow:
        1. record_hook_event (carried over from Phase 5)
        2. run_quality_audit (from Phase 6)
        3. run_meta_learning (Phase 10 D-hooks)
        4. validate_phase_gate(10) → PASS
        """
        rec = tool_funcs["record_hook_event"]
        audit = tool_funcs["run_quality_audit"]
        meta = tool_funcs["run_meta_learning"]

        with _mock_project_context(project_dir):
            # Hooks from writing phases
            rec(hook_id="A1", event_type="trigger")
            rec(hook_id="A1", event_type="pass")
            rec(hook_id="B3", event_type="pass")

            # Quality audit
            scores = json.dumps({dim: 8 for dim in DIMENSIONS})
            audit(scores=scores)

            # Meta-learning
            meta_result = meta()

        assert "status: ok" in meta_result

        # Setup remaining Phase 10 requirements (non-MCP artifacts)
        (audit_dir / "pipeline-run-20260101.md").write_text(
            "# Pipeline Run\n## D7\nReview retro\n## D8\nEQUATOR retro\n"
        )
        (project_dir / ".memory" / "activeContext.md").write_text("# Active")
        (project_dir / ".memory" / "progress.md").write_text("# Progress")

        r = validator.validate_phase(10)
        assert r.passed, (
            f"Phase 10 failed: {[c.name + ': ' + c.details for c in r.critical_failures]}"
        )

    def test_phase6_fails_without_tool_calls(self, validator, audit_dir):
        """Phase 6 MUST fail if agent never called audit MCP tools."""
        # Only put .md files (agent could theoretically fake those)
        (audit_dir / "quality-scorecard.md").write_text("# Fake scorecard\n")
        (audit_dir / "hook-effectiveness.md").write_text("# Fake\n")

        r = validator.validate_phase(6)
        assert not r.passed
        data_checks = [c for c in r.checks if c.name.endswith(":data")]
        assert len(data_checks) == 2
        assert all(not c.passed for c in data_checks)

    def test_phase10_fails_without_meta_learning_tool(
        self, tool_funcs, project_dir, audit_dir, validator
    ):
        """Phase 10 MUST fail if agent never called run_meta_learning."""
        rec = tool_funcs["record_hook_event"]
        audit = tool_funcs["run_quality_audit"]

        with _mock_project_context(project_dir):
            rec(hook_id="A1", event_type="pass")
            audit(scores=json.dumps({dim: 8 for dim in DIMENSIONS}))
            # Deliberately skip run_meta_learning!

        (audit_dir / "pipeline-run-20260101.md").write_text("# Run\n## D7\nretro\n## D8\neq\n")
        (audit_dir / "evolution-log.jsonl").write_text(
            json.dumps({"event": "meta_learning"}) + "\n"
        )
        (project_dir / ".memory" / "activeContext.md").write_text("#")
        (project_dir / ".memory" / "progress.md").write_text("#")

        r = validator.validate_phase(10)
        assert not r.passed
        mla_check = next(c for c in r.checks if c.name == "meta-learning-audit:data")
        assert not mla_check.passed


# ── Phase 6 Enhanced Validator (data-level checks) ────────────────────


class TestPhase6Enhanced:
    """Phase 6 now validates actual data, not just file existence."""

    def test_fail_no_files(self, validator):
        """Phase 6 without any audit files must FAIL."""
        r = validator.validate_phase(6)
        assert not r.passed
        names = [c.name for c in r.critical_failures]
        assert "audit:quality-scorecard.md" in names
        assert "audit:hook-effectiveness.md" in names
        assert "quality-scorecard:data" in names
        assert "hook-effectiveness:data" in names

    def test_fail_empty_files_only(self, validator, audit_dir):
        """Files exist but with no data → still FAIL."""
        (audit_dir / "quality-scorecard.md").write_text("# Empty Scorecard\n")
        (audit_dir / "hook-effectiveness.md").write_text("# Empty\n")
        (audit_dir / "quality-scorecard.yaml").write_text(
            yaml.dump(
                {
                    "version": 1,
                    "scores": {},
                    "history": [],
                },
                default_flow_style=False,
            )
        )
        (audit_dir / "hook-effectiveness.yaml").write_text(
            yaml.dump(
                {
                    "version": 1,
                    "hooks": {},
                    "runs": [],
                },
                default_flow_style=False,
            )
        )

        r = validator.validate_phase(6)
        assert not r.passed
        md_checks = [c for c in r.checks if c.name.startswith("audit:")]
        assert all(c.passed for c in md_checks)
        qs_data = next(c for c in r.checks if c.name == "quality-scorecard:data")
        assert not qs_data.passed
        assert "0 dimensions scored" in qs_data.details

        he_data = next(c for c in r.checks if c.name == "hook-effectiveness:data")
        assert not he_data.passed

    def test_fail_insufficient_dimensions(self, validator, audit_dir):
        """Only 3 dimensions scored (need ≥4) → FAIL."""
        data = {
            "version": 1,
            "scores": {
                "citation_quality": {"score": 8, "explanation": "good"},
                "text_quality": {"score": 7, "explanation": "ok"},
                "format_compliance": {"score": 9, "explanation": "great"},
            },
            "history": [],
        }
        (audit_dir / "quality-scorecard.yaml").write_text(yaml.dump(data, default_flow_style=False))
        (audit_dir / "quality-scorecard.md").write_text("# Scorecard\n")
        (audit_dir / "hook-effectiveness.md").write_text("# HE\n")
        (audit_dir / "hook-effectiveness.yaml").write_text(
            yaml.dump(
                {
                    "version": 1,
                    "hooks": {"A1": {"trigger": 1, "pass": 2, "fix": 0, "false_positive": 0}},
                },
                default_flow_style=False,
            )
        )

        r = validator.validate_phase(6)
        assert not r.passed
        qs_data = next(c for c in r.checks if c.name == "quality-scorecard:data")
        assert not qs_data.passed
        assert "3 dimensions scored" in qs_data.details

    def test_pass_full_data(self, validator, audit_dir):
        """All dimensions scored + hook events → PASS."""
        scores_data = {
            "version": 1,
            "scores": {
                dim: {"score": 7 + i * 0.5, "explanation": f"Score for {dim}"}
                for i, dim in enumerate(DIMENSIONS)
            },
            "history": [],
        }
        (audit_dir / "quality-scorecard.yaml").write_text(
            yaml.dump(scores_data, default_flow_style=False)
        )
        (audit_dir / "quality-scorecard.md").write_text("# Scorecard\n## Scores\n")

        he_data = {
            "version": 1,
            "hooks": {
                "A1": {"trigger": 2, "pass": 5, "fix": 1, "false_positive": 0},
                "B1": {"trigger": 1, "pass": 3, "fix": 0, "false_positive": 0},
            },
            "runs": [],
        }
        (audit_dir / "hook-effectiveness.yaml").write_text(
            yaml.dump(he_data, default_flow_style=False)
        )
        (audit_dir / "hook-effectiveness.md").write_text("# HE\n## Summary\n")

        r = validator.validate_phase(6)
        assert r.passed
        qs_data = next(c for c in r.checks if c.name == "quality-scorecard:data")
        assert qs_data.passed
        assert "6 dimensions scored" in qs_data.details

        he_data_check = next(c for c in r.checks if c.name == "hook-effectiveness:data")
        assert he_data_check.passed
        assert "2 hooks with events" in he_data_check.details

    def test_pass_with_4_dimensions(self, validator, audit_dir):
        """Exactly 4 dimensions scored → PASS (minimum threshold)."""
        scores_data = {
            "version": 1,
            "scores": {
                dim: {"score": 7, "explanation": f"Score for {dim}"} for dim in DIMENSIONS[:4]
            },
            "history": [],
        }
        (audit_dir / "quality-scorecard.yaml").write_text(
            yaml.dump(scores_data, default_flow_style=False)
        )
        (audit_dir / "quality-scorecard.md").write_text("# Scorecard\n")

        he_data = {
            "version": 1,
            "hooks": {"C1": {"trigger": 1, "pass": 0, "fix": 1, "false_positive": 0}},
            "runs": [],
        }
        (audit_dir / "hook-effectiveness.yaml").write_text(
            yaml.dump(he_data, default_flow_style=False)
        )
        (audit_dir / "hook-effectiveness.md").write_text("# HE\n")

        r = validator.validate_phase(6)
        assert r.passed

    def test_corrupt_yaml_fails_gracefully(self, validator, audit_dir):
        """Corrupt YAML files → FAIL with descriptive error."""
        (audit_dir / "quality-scorecard.yaml").write_text("{invalid yaml: [")
        (audit_dir / "quality-scorecard.md").write_text("# Scorecard\n")
        (audit_dir / "hook-effectiveness.yaml").write_text("{invalid: [")
        (audit_dir / "hook-effectiveness.md").write_text("# HE\n")

        r = validator.validate_phase(6)
        assert not r.passed


# ── Phase 10 Enhanced Validator ───────────────────────────────────────


class TestPhase10Enhanced:
    """Phase 10 now validates meta-learning audit data, not just files."""

    def test_fail_no_meta_learning_audit(self, validator, audit_dir):
        """Phase 10 without meta-learning-audit.json must FAIL on data check."""
        (audit_dir / "pipeline-run-20260101.md").write_text("# Run\n## D7\nretro\n## D8\nequator\n")
        (audit_dir / "hook-effectiveness.md").write_text("# HE\n")
        (audit_dir / "evolution-log.jsonl").write_text(
            json.dumps({"event": "meta_learning"}) + "\n"
        )

        r = validator.validate_phase(10)
        assert not r.passed
        mla_check = next(c for c in r.checks if c.name == "meta-learning-audit:data")
        assert not mla_check.passed
        assert "MISSING" in mla_check.details

    def test_fail_empty_meta_learning_audit(self, validator, audit_dir):
        """Empty meta-learning-audit.json → FAIL."""
        (audit_dir / "pipeline-run-20260101.md").write_text("# Run\n## D7\n\n## D8\n")
        (audit_dir / "hook-effectiveness.md").write_text("# HE\n")
        (audit_dir / "evolution-log.jsonl").write_text(
            json.dumps({"event": "meta_learning"}) + "\n"
        )
        (audit_dir / "meta-learning-audit.yaml").write_text("[]")

        r = validator.validate_phase(10)
        assert not r.passed
        mla_check = next(c for c in r.checks if c.name == "meta-learning-audit:data")
        assert not mla_check.passed
        assert "empty" in mla_check.details

    def test_fail_audit_missing_counts(self, validator, audit_dir):
        """Audit entry without required count fields → FAIL."""
        (audit_dir / "pipeline-run-20260101.md").write_text("# Run\n## D7\n\n## D8\n")
        (audit_dir / "hook-effectiveness.md").write_text("# HE\n")
        (audit_dir / "evolution-log.jsonl").write_text(
            json.dumps({"event": "meta_learning"}) + "\n"
        )
        (audit_dir / "meta-learning-audit.yaml").write_text(
            yaml.dump([{"timestamp": "2026-01-01", "data": "incomplete"}], default_flow_style=False)
        )

        r = validator.validate_phase(10)
        assert not r.passed
        mla_check = next(c for c in r.checks if c.name == "meta-learning-audit:data")
        assert not mla_check.passed
        assert "missing analysis counts" in mla_check.details

    def test_pass_full_phase_10(self, validator, project_dir, audit_dir):
        """Complete Phase 10 with valid meta-learning data → PASS."""
        (audit_dir / "pipeline-run-20260101.md").write_text(
            "# Pipeline Run\n## D7\nReview retro\n## D8\nEQUATOR retro\n"
        )
        (audit_dir / "hook-effectiveness.md").write_text("# Hook Effectiveness\n")
        (audit_dir / "evolution-log.jsonl").write_text(
            json.dumps({"event": "meta_learning"}) + "\n"
        )
        audit_entry = {
            "timestamp": "2026-01-01T00:00:00",
            "run_number": 0,
            "adjustments_count": 2,
            "lessons_count": 3,
            "suggestions_count": 1,
            "adjustments": [],
            "lessons": [],
            "suggestions": [],
        }
        (audit_dir / "meta-learning-audit.yaml").write_text(
            yaml.dump([audit_entry], default_flow_style=False)
        )

        (project_dir / ".memory" / "activeContext.md").write_text("# Active")
        (project_dir / ".memory" / "progress.md").write_text("# Progress")

        r = validator.validate_phase(10)
        assert r.passed

        mla_check = next(c for c in r.checks if c.name == "meta-learning-audit:data")
        assert mla_check.passed
        assert "1 analysis entries" in mla_check.details
        assert "adj=2" in mla_check.details
        assert "lessons=3" in mla_check.details


# ── Integration: infrastructure → gate ────────────────────────────────


class TestMetaLearningEngineIntegration:
    """Verify MetaLearningEngine.analyze() produces data that passes Phase 10 gate."""

    def test_engine_analyze_creates_valid_audit(
        self, engine, tracker, scorecard, audit_dir, project_dir, validator
    ):
        """Running engine.analyze() should produce audit file that passes Phase 10 data check."""
        tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "fix")
        tracker.record_event("B1", "pass")
        scorecard.set_score("citation_quality", 7, "Good coverage")
        scorecard.set_score("text_quality", 6, "Needs improvement")

        result = engine.analyze()
        assert "adjustments" in result
        assert "lessons" in result
        assert "suggestions" in result
        assert "audit_trail" in result

        mla_yaml = audit_dir / "meta-learning-audit.yaml"
        assert mla_yaml.is_file()
        data = yaml.safe_load(mla_yaml.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) >= 1

        entry = data[-1]
        assert "adjustments_count" in entry
        assert "lessons_count" in entry
        assert "suggestions_count" in entry

    def test_engine_output_passes_phase10_gate(
        self, engine, tracker, scorecard, audit_dir, project_dir
    ):
        """End-to-end: engine analyze → evolution log → Phase 10 passes."""
        tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "pass")
        tracker.generate_report()

        for dim in DIMENSIONS:
            scorecard.set_score(dim, 7, "Adequate")
        scorecard.generate_report()

        engine.analyze()

        elog = audit_dir / "evolution-log.jsonl"
        with open(elog, "a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "meta_learning"}) + "\n")

        (audit_dir / "pipeline-run-20260101.md").write_text(
            "# Pipeline Run\n## D7\nReview retro content\n## D8\nEQUATOR retro content\n"
        )

        mem_dir = project_dir / ".memory"
        mem_dir.mkdir(exist_ok=True)
        (mem_dir / "activeContext.md").write_text("# Active Context")
        (mem_dir / "progress.md").write_text("# Progress")

        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(10)
        assert r.passed, (
            f"Phase 10 failed: {[c.name + ': ' + c.details for c in r.critical_failures]}"
        )


class TestQualityScorecardIntegration:
    """Verify QualityScorecard produces data that passes Phase 6 gate."""

    def test_scorecard_set_scores_passes_phase6(self, scorecard, tracker, audit_dir, project_dir):
        """Setting ≥4 scores + recording hook events → Phase 6 passes."""
        for dim in DIMENSIONS:
            scorecard.set_score(dim, 7.5, f"Score for {dim}")
        scorecard.generate_report()

        tracker.record_event("A1", "trigger")
        tracker.record_event("A1", "fix")
        tracker.record_event("C1", "pass")
        tracker.generate_report()

        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(6)
        assert r.passed, (
            f"Phase 6 failed: {[c.name + ': ' + c.details for c in r.critical_failures]}"
        )


class TestHookEffectivenessTrackerEvents:
    """Verify tracker events & data validation in Phase 6."""

    def test_single_event_sufficient(self, tracker, scorecard, audit_dir, project_dir):
        """A single hook event should satisfy the hook-effectiveness data check."""
        tracker.record_event("A1", "pass")
        tracker.generate_report()

        for dim in DIMENSIONS[:4]:
            scorecard.set_score(dim, 7, "ok")
        scorecard.generate_report()

        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(6)
        he_check = next(c for c in r.checks if c.name == "hook-effectiveness:data")
        assert he_check.passed

    def test_zero_count_events_not_counted(self, audit_dir, project_dir):
        """Hooks with all-zero counts should not be counted as having events."""
        he_data = {
            "version": 1,
            "hooks": {"A1": {"trigger": 0, "pass": 0, "fix": 0, "false_positive": 0}},
            "runs": [],
        }
        (audit_dir / "hook-effectiveness.yaml").write_text(
            yaml.dump(he_data, default_flow_style=False)
        )
        (audit_dir / "hook-effectiveness.md").write_text("# HE\n")
        (audit_dir / "quality-scorecard.md").write_text("# QS\n")

        v = PipelineGateValidator(project_dir)
        r = v.validate_phase(6)
        he_check = next(c for c in r.checks if c.name == "hook-effectiveness:data")
        assert not he_check.passed
        assert "0 hooks with events" in he_check.details
