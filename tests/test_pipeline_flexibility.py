"""
Tests for Pipeline Flexibility features:
- Phase regression (Phase 7 → Phase 5)
- Pause/resume with edit detection
- Per-section user approval in Phase 5
- REWRITE_NEEDED verdict in AutonomousAuditLoop
"""

from pathlib import Path

import pytest

from med_paper_assistant.infrastructure.persistence.autonomous_audit_loop import (
    AuditLoopConfig,
    AutonomousAuditLoop,
    RoundVerdict,
    Severity,
)
from med_paper_assistant.infrastructure.persistence.checkpoint_manager import CheckpointManager

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project directory structure."""
    p = tmp_path / "test-project"
    p.mkdir()
    (p / ".audit").mkdir()
    (p / "drafts").mkdir()
    (p / "references").mkdir()
    return p


@pytest.fixture()
def ckpt(project_dir: Path) -> CheckpointManager:
    return CheckpointManager(project_dir / ".audit", project_dir=project_dir)


@pytest.fixture()
def loop(project_dir: Path) -> AutonomousAuditLoop:
    config = AuditLoopConfig(max_rounds=3, quality_threshold=7.0, context="review")
    return AutonomousAuditLoop(str(project_dir / ".audit"), config=config)


def _write_manuscript(
    project_dir: Path, content: str = "# Manuscript\n\n## Methods\n\nSome methods."
) -> None:
    (project_dir / "drafts" / "manuscript.md").write_text(content, encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# A. Phase Regression Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestPhaseRegression:
    """Tests for pipeline phase regression (Phase 7 → Phase 5)."""

    def test_save_phase_regression_updates_state(self, ckpt: CheckpointManager):
        """Regression should update phase pointers and create regression context."""
        # First, simulate getting to Phase 7
        ckpt.save_phase_completion(5, "WRITING")
        ckpt.save_phase_completion(6, "AUDIT")
        ckpt.save_phase_completion(7, "REVIEW")

        # Regress to Phase 5
        ckpt.save_phase_regression(
            from_phase=7,
            to_phase=5,
            reason="Methods section needs major rewrite",
            sections_to_rewrite=["Methods"],
        )

        state = ckpt.load()
        assert state is not None
        assert state["status"] == "regression"
        assert state["last_completed_phase"] == 4  # to_phase - 1
        assert state["current_phase"] == 5

        regression = state["regression_context"]
        assert regression["from_phase"] == 7
        assert regression["to_phase"] == 5
        assert regression["sections_to_rewrite"] == ["Methods"]
        assert regression["regression_count"] == 1

    def test_regression_count_increments(self, ckpt: CheckpointManager):
        """Multiple regressions should increment the count."""
        ckpt.save_phase_regression(7, 5, "first regression", ["Methods"])
        ckpt.save_phase_regression(7, 5, "second regression", ["Results"])

        state = ckpt.load()
        assert state["regression_context"]["regression_count"] == 2

    def test_regression_clears_section_approval(self, ckpt: CheckpointManager):
        """Regression should clear approval for sections being rewritten."""
        # Approve sections
        ckpt.save_section_progress("Methods", 1000, approval_status="approved")
        ckpt.save_section_progress("Results", 800, approval_status="approved")

        # Regress — Methods needs rewrite
        ckpt.save_phase_regression(7, 5, "rewrite needed", ["Methods"])

        state = ckpt.load()
        assert state["section_progress"]["Methods"]["approval_status"] == "pending"
        assert state["section_progress"]["Results"]["approval_status"] == "approved"

    def test_clear_regression_context(self, ckpt: CheckpointManager):
        """clear_regression_context should remove the regression data."""
        ckpt.save_phase_regression(7, 5, "test", ["Methods"])
        ckpt.clear_regression_context()

        state = ckpt.load()
        assert "regression_context" not in state

    def test_regression_recorded_in_history(self, ckpt: CheckpointManager):
        """Regression should appear in checkpoint history."""
        ckpt.save_phase_regression(7, 5, "test reason", ["Methods"])

        state = ckpt.load()
        regression_events = [h for h in state["history"] if h["action"] == "phase_regression"]
        assert len(regression_events) == 1
        assert regression_events[0]["from_phase"] == 7
        assert regression_events[0]["to_phase"] == 5


# ──────────────────────────────────────────────────────────────────────────────
# B. Pause/Resume Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestPauseResume:
    """Tests for pipeline pause/resume with edit detection."""

    def test_pause_saves_state(self, ckpt: CheckpointManager, project_dir: Path):
        """Pausing should set status to 'paused' and record draft hashes."""
        _write_manuscript(project_dir)
        ckpt.save_phase_start(5, "WRITING")
        ckpt.save_pause(reason="user wants to edit")

        state = ckpt.load()
        assert state["status"] == "paused"
        assert "pause_state" in state
        assert state["pause_state"]["reason"] == "user wants to edit"
        assert "manuscript.md" in state["pause_state"]["draft_hashes"]

    def test_resume_no_changes(self, ckpt: CheckpointManager, project_dir: Path):
        """Resuming without edits should report no changes."""
        _write_manuscript(project_dir)
        ckpt.save_phase_start(5, "WRITING")
        ckpt.save_pause()

        result = ckpt.resume_from_pause()
        assert result["changed"] is False
        assert result["changed_files"] == []

    def test_resume_detects_changes(self, ckpt: CheckpointManager, project_dir: Path):
        """Resuming after editing should detect changed files."""
        _write_manuscript(project_dir)
        ckpt.save_phase_start(5, "WRITING")
        ckpt.save_pause()

        # Simulate user editing the manuscript
        _write_manuscript(project_dir, "# Modified Manuscript\n\nNew content here.")

        result = ckpt.resume_from_pause()
        assert result["changed"] is True
        assert "manuscript.md" in result["changed_files"]

    def test_resume_detects_new_files(self, ckpt: CheckpointManager, project_dir: Path):
        """Resuming should detect new draft files created during pause."""
        _write_manuscript(project_dir)
        ckpt.save_phase_start(5, "WRITING")
        ckpt.save_pause()

        # Add a new draft file
        (project_dir / "drafts" / "supplement.md").write_text("# Supplement", encoding="utf-8")

        result = ckpt.resume_from_pause()
        assert result["changed"] is True
        assert "supplement.md" in result["changed_files"]

    def test_resume_sets_status_to_in_progress(self, ckpt: CheckpointManager, project_dir: Path):
        """After resume, status should change back to in_progress."""
        _write_manuscript(project_dir)
        ckpt.save_phase_start(5, "WRITING")
        ckpt.save_pause()
        ckpt.resume_from_pause()

        state = ckpt.load()
        assert state["status"] == "in_progress"

    def test_resume_when_not_paused(self, ckpt: CheckpointManager):
        """Resuming when not paused should return empty result gracefully."""
        result = ckpt.resume_from_pause()
        assert result["changed"] is False
        assert result["phase_at_pause"] == -1

    def test_pause_resume_recorded_in_history(self, ckpt: CheckpointManager, project_dir: Path):
        """Pause and resume should appear in checkpoint history."""
        _write_manuscript(project_dir)
        ckpt.save_phase_start(5, "WRITING")
        ckpt.save_pause()
        ckpt.resume_from_pause()

        state = ckpt.load()
        actions = [h["action"] for h in state["history"]]
        assert "pipeline_paused" in actions
        assert "pipeline_resumed" in actions


# ──────────────────────────────────────────────────────────────────────────────
# C. Section Approval Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestSectionApproval:
    """Tests for per-section user approval in Phase 5."""

    def test_section_starts_pending(self, ckpt: CheckpointManager):
        """New sections should start with pending status."""
        ckpt.save_section_progress("Methods", 1000)

        state = ckpt.load()
        assert state["section_progress"]["Methods"]["approval_status"] == "pending"

    def test_section_approve(self, ckpt: CheckpointManager):
        """Approving a section should set status to approved."""
        ckpt.save_section_progress("Methods", 1000, approval_status="approved")

        state = ckpt.load()
        assert state["section_progress"]["Methods"]["approval_status"] == "approved"

    def test_section_revision_requested(self, ckpt: CheckpointManager):
        """Requesting revision should set status and record feedback."""
        ckpt.save_section_progress(
            "Methods",
            1000,
            approval_status="revision_requested",
            user_feedback="Add more detail about sample size",
        )

        state = ckpt.load()
        section = state["section_progress"]["Methods"]
        assert section["approval_status"] == "revision_requested"
        assert section["user_feedback"] == "Add more detail about sample size"
        assert section["revision_count"] == 1

    def test_revision_count_increments(self, ckpt: CheckpointManager):
        """Multiple revision requests should increment the count."""
        ckpt.save_section_progress("Methods", 1000, approval_status="revision_requested")
        ckpt.save_section_progress("Methods", 1100, approval_status="revision_requested")

        state = ckpt.load()
        assert state["section_progress"]["Methods"]["revision_count"] == 2

    def test_all_sections_approved(self, ckpt: CheckpointManager):
        """all_sections_approved should return True only when all are approved."""
        ckpt.save_section_progress("Methods", 1000, approval_status="approved")
        ckpt.save_section_progress("Results", 800, approval_status="pending")
        assert ckpt.all_sections_approved() is False

        ckpt.save_section_progress("Results", 800, approval_status="approved")
        assert ckpt.all_sections_approved() is True

    def test_all_sections_approved_empty(self, ckpt: CheckpointManager):
        """all_sections_approved should return False when no sections exist."""
        assert ckpt.all_sections_approved() is False

    def test_get_section_approval_status(self, ckpt: CheckpointManager):
        """get_section_approval_status should return all section statuses."""
        ckpt.save_section_progress("Methods", 1000, approval_status="approved")
        ckpt.save_section_progress("Results", 800, approval_status="pending")

        statuses = ckpt.get_section_approval_status()
        assert statuses == {"Methods": "approved", "Results": "pending"}

    def test_recovery_summary_shows_approval(self, ckpt: CheckpointManager):
        """Recovery summary should show section approval status."""
        ckpt.save_phase_start(5, "WRITING")
        ckpt.save_section_progress("Methods", 1000, approval_status="approved")
        ckpt.save_section_progress("Results", 800, approval_status="pending")

        summary = ckpt.get_recovery_summary()
        assert "Methods: approved" in summary
        assert "Results: pending" in summary


# ──────────────────────────────────────────────────────────────────────────────
# D. REWRITE_NEEDED Verdict Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestRewriteNeededVerdict:
    """Tests for REWRITE_NEEDED verdict in AutonomousAuditLoop."""

    def test_rewrite_needed_enum_exists(self):
        """REWRITE_NEEDED should be a valid RoundVerdict."""
        assert RoundVerdict.REWRITE_NEEDED.value == "rewrite_needed"

    def test_request_rewrite_sets_state(self, loop: AutonomousAuditLoop):
        """request_rewrite should mark sections for rewriting."""
        loop.start_round()
        loop.record_issue("B1", Severity.CRITICAL, "Concept inconsistency", "Rewrite section")
        loop.request_rewrite(["Methods"], "Methods needs full rewrite")

        assert loop.is_completed
        assert loop.rewrite_sections == ["Methods"]
        assert loop.rewrite_reason == "Methods needs full rewrite"

    def test_request_rewrite_saves_round_record(self, loop: AutonomousAuditLoop):
        """request_rewrite should save a round record with REWRITE_NEEDED verdict."""
        loop.start_round()
        loop.request_rewrite(["Methods"], "Needs rewrite")

        status = loop.get_status()
        assert status["latest_verdict"] == "rewrite_needed"

    def test_request_rewrite_empty_sections_raises(self, loop: AutonomousAuditLoop):
        """request_rewrite with no sections should raise ValueError."""
        loop.start_round()
        with pytest.raises(ValueError, match="at least one section"):
            loop.request_rewrite([], "no sections")

    def test_rewrite_state_persists(self, loop: AutonomousAuditLoop, project_dir: Path):
        """Rewrite state should be saved and loadable."""
        loop.start_round()
        loop.request_rewrite(["Methods", "Results"], "Both need rewrite")
        loop.save()

        # Load in a new instance
        config = AuditLoopConfig(max_rounds=3, quality_threshold=7.0, context="review")
        loop2 = AutonomousAuditLoop(str(project_dir / ".audit"), config=config)
        loaded = loop2.load()

        assert loaded is True
        assert loop2.rewrite_sections == ["Methods", "Results"]
        assert loop2.rewrite_reason == "Both need rewrite"
        assert loop2.is_completed

    def test_reset_clears_rewrite_state(self, loop: AutonomousAuditLoop):
        """reset should clear rewrite state."""
        loop.start_round()
        loop.request_rewrite(["Methods"], "Needs rewrite")
        loop.reset()

        assert loop.rewrite_sections == []
        assert loop.rewrite_reason == ""
        assert not loop.is_completed


# ──────────────────────────────────────────────────────────────────────────────
# E. Integration: Recovery Summary Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestRecoverySummaryIntegration:
    """Tests for recovery summary with new features."""

    def test_recovery_summary_shows_regression(self, ckpt: CheckpointManager):
        """Recovery summary should show regression context."""
        ckpt.save_phase_regression(7, 5, "Methods needs rewrite", ["Methods"])

        summary = ckpt.get_recovery_summary()
        assert "Regression Active" in summary
        assert "Phase 7" in summary
        assert "Phase 5" in summary
        assert "Methods" in summary

    def test_recovery_summary_shows_pause(self, ckpt: CheckpointManager, project_dir: Path):
        """Recovery summary should show pause state."""
        _write_manuscript(project_dir)
        ckpt.save_phase_start(5, "WRITING")
        ckpt.save_pause("user editing")

        summary = ckpt.get_recovery_summary()
        assert "Pipeline Paused" in summary
        assert "user editing" in summary


# ──────────────────────────────────────────────────────────────────────────────
# F. Draft Hash Computation Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestDraftHashComputation:
    """Tests for _compute_draft_hashes helper."""

    def test_compute_hashes_empty_dir(self, ckpt: CheckpointManager, project_dir: Path):
        """Empty drafts dir should return empty dict."""
        hashes = ckpt._compute_draft_hashes()
        assert hashes == {}

    def test_compute_hashes_with_files(self, ckpt: CheckpointManager, project_dir: Path):
        """Should compute hashes for .md files in drafts/."""
        _write_manuscript(project_dir)
        (project_dir / "drafts" / "concept.md").write_text("# Concept", encoding="utf-8")

        hashes = ckpt._compute_draft_hashes()
        assert "manuscript.md" in hashes
        assert "concept.md" in hashes
        assert len(hashes) == 2

    def test_hashes_change_on_edit(self, ckpt: CheckpointManager, project_dir: Path):
        """Edited files should produce different hashes."""
        _write_manuscript(project_dir, "Original content")
        h1 = ckpt._compute_draft_hashes()

        _write_manuscript(project_dir, "Modified content")
        h2 = ckpt._compute_draft_hashes()

        assert h1["manuscript.md"] != h2["manuscript.md"]

    def test_non_md_files_excluded(self, ckpt: CheckpointManager, project_dir: Path):
        """Non-.md files should not be included in hashes."""
        _write_manuscript(project_dir)
        (project_dir / "drafts" / "image.png").write_bytes(b"\x89PNG")

        hashes = ckpt._compute_draft_hashes()
        assert "image.png" not in hashes
        assert "manuscript.md" in hashes
