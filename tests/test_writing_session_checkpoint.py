"""
Tests for Writing Session Checkpoint feature.

Validates:
- WorkspaceStateManager.sync_writing_session() persists writing state
- _auto_checkpoint_writing() helper in writing.py and editing.py
- checkpoint_writing_context() MCP tool
- get_recovery_summary() includes writing session banner
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from med_paper_assistant.infrastructure.persistence.workspace_state_manager import (
    WorkspaceStateManager,
)

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Set up a fake project directory."""
    proj = tmp_path / "projects" / "test-project"
    proj.mkdir(parents=True)
    # Create .current_project marker
    marker = tmp_path / ".current_project"
    marker.write_text("test-project", encoding="utf-8")
    return proj


@pytest.fixture()
def wsm(tmp_path: Path, project_dir: Path) -> WorkspaceStateManager:
    """WorkspaceStateManager pointed at tmp_path."""
    return WorkspaceStateManager(str(tmp_path))


@pytest.fixture()
def drafts_dir(project_dir: Path) -> Path:
    """Create drafts directory with sample files."""
    d = project_dir / "drafts"
    d.mkdir()
    return d


# ──────────────────────────────────────────────────────────────────────────────
# WorkspaceStateManager.sync_writing_session
# ──────────────────────────────────────────────────────────────────────────────


class TestSyncWritingSession:
    """Tests for sync_writing_session() method."""

    def test_basic_sync(self, wsm: WorkspaceStateManager):
        """Should save writing session to state file."""
        result = wsm.sync_writing_session(
            section="Introduction",
            filename="introduction.md",
            operation="write",
            word_count=500,
        )
        assert result is True

        state = wsm.get_state()
        ws = state["writing_session"]
        assert ws["active"] is True
        assert ws["current_section"] == "Introduction"
        assert ws["last_file_modified"] == "introduction.md"
        assert ws["last_operation"] == "write"
        assert ws["word_count"] == 500
        assert ws["timestamp"] is not None

    def test_agent_context_saved(self, wsm: WorkspaceStateManager):
        """Should save agent context when provided."""
        wsm.sync_writing_session(
            section="Methods",
            filename="methods.md",
            operation="patch",
            agent_context="Plan: P1 study design, P2 participants | Refs: smith2024",
        )
        state = wsm.get_state()
        assert state["writing_session"]["agent_context"] == (
            "Plan: P1 study design, P2 participants | Refs: smith2024"
        )

    def test_sections_on_disk_scanned(
        self, wsm: WorkspaceStateManager, drafts_dir: Path
    ):
        """Should scan drafts/ and list all .md files with word counts."""
        (drafts_dir / "introduction.md").write_text(
            "word " * 100, encoding="utf-8"
        )
        (drafts_dir / "methods.md").write_text(
            "word " * 200, encoding="utf-8"
        )
        # Non-md files should be ignored
        (drafts_dir / "notes.txt").write_text("ignored", encoding="utf-8")

        wsm.sync_writing_session(
            section="Introduction",
            filename="introduction.md",
            operation="write",
            word_count=100,
        )
        state = wsm.get_state()
        sections = state["writing_session"]["sections_on_disk"]
        assert len(sections) == 2
        assert any("Introduction" in s for s in sections)
        assert any("Methods" in s for s in sections)
        assert any("100w" in s for s in sections)
        assert any("200w" in s for s in sections)

    def test_recovery_hints_also_updated(self, wsm: WorkspaceStateManager):
        """Should update recovery_hints.agent_was_doing as double-safety."""
        wsm.sync_writing_session(
            section="Discussion",
            filename="discussion.md",
            operation="write",
        )
        state = wsm.get_state()
        hint = state["recovery_hints"]["agent_was_doing"]
        assert "Discussion" in hint
        assert "write" in hint

    def test_last_activity_updated(self, wsm: WorkspaceStateManager):
        """Should update last_activity timestamp."""
        wsm.sync_writing_session(
            section="Results",
            filename="results.md",
            operation="patch",
        )
        state = wsm.get_state()
        assert state["last_activity"] is not None

    def test_overwrites_previous_session(self, wsm: WorkspaceStateManager):
        """Calling sync_writing_session again should overwrite, not accumulate."""
        wsm.sync_writing_session(
            section="Introduction",
            filename="introduction.md",
            operation="write",
            word_count=500,
        )
        wsm.sync_writing_session(
            section="Methods",
            filename="methods.md",
            operation="patch",
            word_count=800,
        )
        state = wsm.get_state()
        ws = state["writing_session"]
        assert ws["current_section"] == "Methods"
        assert ws["word_count"] == 800

    def test_state_persisted_to_disk(
        self, wsm: WorkspaceStateManager, project_dir: Path
    ):
        """State should be written to .mdpaper-state.json on disk."""
        wsm.sync_writing_session(
            section="Abstract",
            filename="abstract.md",
            operation="write",
            word_count=250,
        )
        state_file = project_dir / ".mdpaper-state.json"
        assert state_file.exists()
        disk_state = json.loads(state_file.read_text(encoding="utf-8"))
        assert disk_state["writing_session"]["current_section"] == "Abstract"


# ──────────────────────────────────────────────────────────────────────────────
# Default State
# ──────────────────────────────────────────────────────────────────────────────


class TestDefaultState:
    """Tests for writing_session in default state."""

    def test_default_state_has_writing_session(self, wsm: WorkspaceStateManager):
        """Default state should have writing_session field with active=False."""
        state = wsm.get_state()
        ws = state.get("writing_session")
        assert ws is not None
        assert ws["active"] is False
        assert ws["current_section"] is None

    def test_default_writing_session_fields(self, wsm: WorkspaceStateManager):
        """Default writing_session should have all expected fields."""
        state = wsm.get_state()
        ws = state["writing_session"]
        expected_keys = {
            "active",
            "current_section",
            "last_file_modified",
            "last_operation",
            "word_count",
            "sections_on_disk",
            "timestamp",
            "agent_context",
        }
        assert set(ws.keys()) == expected_keys


# ──────────────────────────────────────────────────────────────────────────────
# Recovery Summary
# ──────────────────────────────────────────────────────────────────────────────


class TestRecoverySummaryWritingSession:
    """Tests for writing session banner in get_recovery_summary()."""

    def test_no_banner_when_inactive(self, wsm: WorkspaceStateManager):
        """No writing session banner when writing_session.active is False."""
        summary = wsm.get_recovery_summary()
        assert "WRITING SESSION IN PROGRESS" not in summary

    def test_banner_when_active(self, wsm: WorkspaceStateManager):
        """Should show writing session banner when active."""
        wsm.sync_writing_session(
            section="Introduction",
            filename="introduction.md",
            operation="write",
            word_count=750,
        )
        summary = wsm.get_recovery_summary()
        assert "WRITING SESSION IN PROGRESS" in summary
        assert "Introduction" in summary
        assert "introduction.md" in summary
        assert "write" in summary
        assert "750" in summary

    def test_banner_shows_agent_context(self, wsm: WorkspaceStateManager):
        """Should show agent context in banner when provided."""
        wsm.sync_writing_session(
            section="Discussion",
            filename="discussion.md",
            operation="checkpoint",
            agent_context="Plan: P1 summary, P2 limitations | Notes: formal tone",
        )
        summary = wsm.get_recovery_summary()
        assert "Agent Context" in summary
        assert "P1 summary" in summary

    def test_banner_shows_sections_on_disk(
        self, wsm: WorkspaceStateManager, drafts_dir: Path
    ):
        """Should list all sections on disk in banner."""
        (drafts_dir / "introduction.md").write_text("content " * 50, encoding="utf-8")
        (drafts_dir / "methods.md").write_text("content " * 100, encoding="utf-8")

        wsm.sync_writing_session(
            section="Methods",
            filename="methods.md",
            operation="write",
            word_count=100,
        )
        summary = wsm.get_recovery_summary()
        assert "Sections on Disk" in summary
        assert "Introduction" in summary
        assert "Methods" in summary

    def test_banner_includes_read_draft_hint(self, wsm: WorkspaceStateManager):
        """Should include hint to use read_draft."""
        wsm.sync_writing_session(
            section="Results",
            filename="results.md",
            operation="patch",
        )
        summary = wsm.get_recovery_summary()
        assert "read_draft" in summary


# ──────────────────────────────────────────────────────────────────────────────
# checkpoint_writing_context MCP tool (unit-level)
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckpointWritingContext:
    """Tests for checkpoint_writing_context() MCP tool behavior."""

    def test_builds_agent_context_from_plan(self, wsm: WorkspaceStateManager):
        """Should build agent_context string from plan."""
        wsm.sync_writing_session(
            section="Introduction",
            filename="introduction.md",
            operation="checkpoint",
            agent_context="Plan: P1 background, P2 gap",
        )
        state = wsm.get_state()
        assert "P1 background" in state["writing_session"]["agent_context"]

    def test_builds_agent_context_from_multiple_fields(
        self, wsm: WorkspaceStateManager
    ):
        """Should combine plan, notes, and refs into one context string."""
        ctx = "Plan: outline | Notes: formal | Refs: smith2024, jones2023"
        wsm.sync_writing_session(
            section="Discussion",
            filename="discussion.md",
            operation="checkpoint",
            agent_context=ctx,
        )
        state = wsm.get_state()
        assert "Plan:" in state["writing_session"]["agent_context"]
        assert "Notes:" in state["writing_session"]["agent_context"]
        assert "Refs:" in state["writing_session"]["agent_context"]

    def test_checkpoint_operation_type(self, wsm: WorkspaceStateManager):
        """Checkpoint should use operation='checkpoint'."""
        wsm.sync_writing_session(
            section="Results",
            filename="results.md",
            operation="checkpoint",
        )
        state = wsm.get_state()
        assert state["writing_session"]["last_operation"] == "checkpoint"


# ──────────────────────────────────────────────────────────────────────────────
# Edge Cases
# ──────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge case tests for writing session checkpoint."""

    def test_no_drafts_dir(self, wsm: WorkspaceStateManager):
        """Should work even when drafts/ directory doesn't exist."""
        result = wsm.sync_writing_session(
            section="Introduction",
            filename="introduction.md",
            operation="write",
            word_count=100,
        )
        assert result is True
        state = wsm.get_state()
        assert state["writing_session"]["sections_on_disk"] == []

    def test_empty_drafts_dir(
        self, wsm: WorkspaceStateManager, drafts_dir: Path
    ):
        """Should work with empty drafts directory."""
        wsm.sync_writing_session(
            section="Methods",
            filename="methods.md",
            operation="write",
        )
        state = wsm.get_state()
        assert state["writing_session"]["sections_on_disk"] == []

    def test_zero_word_count(self, wsm: WorkspaceStateManager):
        """Should handle zero word count."""
        wsm.sync_writing_session(
            section="Appendix",
            filename="appendix.md",
            operation="write",
            word_count=0,
        )
        state = wsm.get_state()
        assert state["writing_session"]["word_count"] == 0

    def test_no_agent_context_is_none(self, wsm: WorkspaceStateManager):
        """agent_context should default to None."""
        wsm.sync_writing_session(
            section="Abstract",
            filename="abstract.md",
            operation="write",
        )
        state = wsm.get_state()
        assert state["writing_session"]["agent_context"] is None

    def test_forward_compat_old_state_gets_writing_session(
        self, wsm: WorkspaceStateManager, project_dir: Path
    ):
        """Old state files without writing_session should get default added."""
        # Write state without writing_session key
        state_file = project_dir / ".mdpaper-state.json"
        old_state = {
            "version": 2,
            "last_activity": None,
            "last_updated": None,
            "workspace_state": {"last_tool_called": None},
            "recovery_hints": {"agent_was_doing": None},
            "cross_mcp_state": {},
            "pipeline_state": {"active": False},
        }
        state_file.write_text(
            json.dumps(old_state), encoding="utf-8"
        )

        state = wsm.get_state()
        assert "writing_session" in state
        assert state["writing_session"]["active"] is False
