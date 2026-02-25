"""
Tests for DraftSnapshotManager and CheckpointManager.

These two infrastructure services provide version control safety nets
independent of git, ensuring draft changes and pipeline state survive
even when the agent forgets to commit.
"""

import json
import time
from pathlib import Path

import pytest

from med_paper_assistant.infrastructure.persistence.checkpoint_manager import CheckpointManager
from med_paper_assistant.infrastructure.persistence.draft_snapshot_manager import (
    DraftSnapshotManager,
)

# ──────────────────────────────────────────────────────────────────────────────
# DraftSnapshotManager Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestDraftSnapshotManager:
    """Tests for automatic draft snapshotting."""

    @pytest.fixture()
    def drafts_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / "drafts"
        d.mkdir()
        return d

    @pytest.fixture()
    def snap_mgr(self, drafts_dir: Path) -> DraftSnapshotManager:
        return DraftSnapshotManager(str(drafts_dir))

    def _write_draft(self, drafts_dir: Path, filename: str, content: str) -> Path:
        f = drafts_dir / filename
        f.write_text(content, encoding="utf-8")
        return f

    # --- snapshot_before_write ---

    def test_snapshot_new_file_returns_none(self, snap_mgr: DraftSnapshotManager):
        """No snapshot needed for files that don't exist yet."""
        result = snap_mgr.snapshot_before_write("nonexistent.md")
        assert result is None

    def test_snapshot_creates_copy(self, snap_mgr: DraftSnapshotManager, drafts_dir: Path):
        """Snapshot should create a copy of the existing file."""
        self._write_draft(drafts_dir, "intro.md", "# Introduction\n\nOriginal content.")
        snap_path = snap_mgr.snapshot_before_write("intro.md", reason="test")

        assert snap_path is not None
        assert Path(snap_path).is_file()
        assert Path(snap_path).read_text(encoding="utf-8") == "# Introduction\n\nOriginal content."

    def test_snapshot_metadata_created(self, snap_mgr: DraftSnapshotManager, drafts_dir: Path):
        """Snapshot should have accompanying .meta.json."""
        self._write_draft(drafts_dir, "intro.md", "Hello")
        snap_path = snap_mgr.snapshot_before_write("intro.md", reason="create_draft")

        meta_path = Path(snap_path).with_suffix(".meta.json")
        assert meta_path.is_file()

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["original"] == "intro.md"
        assert meta["reason"] == "create_draft"
        assert meta["size_bytes"] == len("Hello".encode("utf-8"))
        assert "timestamp" in meta

    def test_snapshot_in_dot_snapshots_dir(self, snap_mgr: DraftSnapshotManager, drafts_dir: Path):
        """Snapshots should go into .snapshots/ subdirectory."""
        self._write_draft(drafts_dir, "methods.md", "Methods content")
        snap_mgr.snapshot_before_write("methods.md")

        assert (drafts_dir / ".snapshots" / "methods").is_dir()

    def test_multiple_snapshots(self, snap_mgr: DraftSnapshotManager, drafts_dir: Path):
        """Multiple snapshots should create unique files."""
        self._write_draft(drafts_dir, "intro.md", "v1")
        snap1 = snap_mgr.snapshot_before_write("intro.md")
        time.sleep(1.1)  # Ensure different timestamp
        self._write_draft(drafts_dir, "intro.md", "v2")
        snap2 = snap_mgr.snapshot_before_write("intro.md")

        assert snap1 != snap2
        assert Path(snap1).read_text(encoding="utf-8") == "v1"
        assert Path(snap2).read_text(encoding="utf-8") == "v2"

    # --- list_snapshots ---

    def test_list_snapshots_empty(self, snap_mgr: DraftSnapshotManager):
        assert snap_mgr.list_snapshots("nonexistent.md") == []

    def test_list_snapshots_returns_entries(self, snap_mgr: DraftSnapshotManager, drafts_dir: Path):
        self._write_draft(drafts_dir, "intro.md", "v1")
        snap_mgr.snapshot_before_write("intro.md")
        time.sleep(1.1)
        self._write_draft(drafts_dir, "intro.md", "v2")
        snap_mgr.snapshot_before_write("intro.md")

        snaps = snap_mgr.list_snapshots("intro.md")
        assert len(snaps) == 2
        # Newest first
        assert "path" in snaps[0]
        assert "timestamp" in snaps[0]

    # --- restore_snapshot ---

    def test_restore_snapshot(self, snap_mgr: DraftSnapshotManager, drafts_dir: Path):
        self._write_draft(drafts_dir, "intro.md", "Original")
        snap_path = snap_mgr.snapshot_before_write("intro.md")

        # Overwrite the draft
        self._write_draft(drafts_dir, "intro.md", "Modified content")

        # Restore
        restored = snap_mgr.restore_snapshot("intro.md", snap_path)
        assert Path(restored).read_text(encoding="utf-8") == "Original"

    def test_restore_creates_pre_restore_snapshot(
        self, snap_mgr: DraftSnapshotManager, drafts_dir: Path
    ):
        """Restoring should snapshot the current before overwriting."""
        self._write_draft(drafts_dir, "intro.md", "v1")
        snap_path = snap_mgr.snapshot_before_write("intro.md")
        self._write_draft(drafts_dir, "intro.md", "v2")

        snap_mgr.restore_snapshot("intro.md", snap_path)

        # Should have 2 snapshots: original + pre-restore
        snaps = snap_mgr.list_snapshots("intro.md")
        assert len(snaps) == 2
        reasons = {s["reason"] for s in snaps}
        assert "pre-restore" in reasons

    def test_restore_nonexistent_raises(self, snap_mgr: DraftSnapshotManager):
        with pytest.raises(FileNotFoundError):
            snap_mgr.restore_snapshot("intro.md", "/nonexistent/snap.md")

    # --- get_diff_summary ---

    def test_diff_summary(self, snap_mgr: DraftSnapshotManager, drafts_dir: Path):
        self._write_draft(drafts_dir, "intro.md", "line1\nline2\nline3")
        snap_path = snap_mgr.snapshot_before_write("intro.md")
        self._write_draft(drafts_dir, "intro.md", "line1\nline2_modified\nline3\nline4")

        diff = snap_mgr.get_diff_summary("intro.md", snap_path)
        assert diff["current_lines"] == 4
        assert diff["snapshot_lines"] == 3
        assert diff["added_lines"] > 0

    # --- snapshot_count ---

    def test_snapshot_count(self, snap_mgr: DraftSnapshotManager, drafts_dir: Path):
        assert snap_mgr.snapshot_count("intro.md") == 0

        self._write_draft(drafts_dir, "intro.md", "v1")
        snap_mgr.snapshot_before_write("intro.md")
        assert snap_mgr.snapshot_count("intro.md") == 1

    # --- cleanup ---

    def test_cleanup_respects_max(self, drafts_dir: Path):
        """Cleanup should remove oldest snapshots beyond max."""
        mgr = DraftSnapshotManager(str(drafts_dir), max_snapshots=3)
        self._write_draft(drafts_dir, "intro.md", "initial")

        for i in range(5):
            self._write_draft(drafts_dir, "intro.md", f"version {i}")
            mgr.snapshot_before_write("intro.md")
            time.sleep(1.1)

        assert mgr.snapshot_count("intro.md") == 3

    # --- snapshots_dir property ---

    def test_snapshots_dir_property(self, snap_mgr: DraftSnapshotManager, drafts_dir: Path):
        assert snap_mgr.snapshots_dir == drafts_dir / ".snapshots"


# ──────────────────────────────────────────────────────────────────────────────
# CheckpointManager Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckpointManager:
    """Tests for pipeline checkpoint save/restore."""

    @pytest.fixture()
    def audit_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / ".audit"
        d.mkdir()
        return d

    @pytest.fixture()
    def ckpt(self, audit_dir: Path) -> CheckpointManager:
        return CheckpointManager(audit_dir)

    # --- basic operations ---

    def test_no_checkpoint_initially(self, ckpt: CheckpointManager):
        assert ckpt.exists() is False
        assert ckpt.load() is None

    def test_save_phase_completion(self, ckpt: CheckpointManager):
        ckpt.save_phase_completion(
            phase=2,
            phase_name="LITERATURE_SEARCH",
            outputs={"refs_saved": 15},
        )

        state = ckpt.load()
        assert state is not None
        assert state["last_completed_phase"] == 2
        assert state["last_phase_name"] == "LITERATURE_SEARCH"
        assert state["status"] == "phase_completed"
        assert state["phase_outputs"]["P2"]["refs_saved"] == 15

    def test_save_phase_start(self, ckpt: CheckpointManager):
        ckpt.save_phase_start(phase=3, phase_name="CONCEPT_DEV")

        state = ckpt.load()
        assert state["current_phase"] == 3
        assert state["status"] == "in_progress"

    def test_sequential_phases(self, ckpt: CheckpointManager):
        ckpt.save_phase_completion(1, "SETUP", outputs={"paper_type": "original"})
        ckpt.save_phase_completion(2, "LITERATURE_SEARCH", outputs={"refs": 10})
        ckpt.save_phase_completion(3, "CONCEPT_DEV", outputs={"novelty": 82})

        state = ckpt.load()
        assert state["last_completed_phase"] == 3
        assert len(state["phase_outputs"]) == 3
        assert len(state["history"]) == 3

    def test_exists_after_save(self, ckpt: CheckpointManager):
        ckpt.save_phase_completion(0, "PRE_CHECK")
        assert ckpt.exists() is True

    # --- section progress ---

    def test_section_progress(self, ckpt: CheckpointManager):
        ckpt.save_section_progress("Introduction", word_count=500)
        ckpt.save_section_progress("Methods", word_count=800)

        state = ckpt.load()
        assert state["section_progress"]["Introduction"]["word_count"] == 500
        assert state["section_progress"]["Methods"]["word_count"] == 800

    # --- flagged issues ---

    def test_add_flagged_issue(self, ckpt: CheckpointManager):
        ckpt.add_flagged_issue("Low citation density in Introduction", severity="major")

        state = ckpt.load()
        assert len(state["flagged_issues"]) == 1
        assert state["flagged_issues"][0]["severity"] == "major"

    def test_multiple_flagged_issues(self, ckpt: CheckpointManager):
        ckpt.add_flagged_issue("Issue 1")
        ckpt.add_flagged_issue("Issue 2", severity="major")

        state = ckpt.load()
        assert len(state["flagged_issues"]) == 2

    # --- recovery summary ---

    def test_recovery_summary_no_checkpoint(self, ckpt: CheckpointManager):
        summary = ckpt.get_recovery_summary()
        assert "No checkpoint found" in summary

    def test_recovery_summary_with_checkpoint(self, ckpt: CheckpointManager):
        ckpt.save_phase_completion(2, "LITERATURE_SEARCH", outputs={"refs": 10})
        ckpt.add_flagged_issue("Test issue")

        summary = ckpt.get_recovery_summary()
        assert "Phase 2" in summary
        assert "LITERATURE_SEARCH" in summary
        assert "1" in summary  # 1 flagged issue

    # --- clear ---

    def test_clear(self, ckpt: CheckpointManager):
        ckpt.save_phase_completion(1, "SETUP")
        assert ckpt.exists() is True

        ckpt.clear()
        assert ckpt.exists() is False
        assert ckpt.load() is None

    # --- audit directory auto-creation ---

    def test_auto_creates_audit_dir(self, tmp_path: Path):
        audit = tmp_path / "new" / ".audit"
        mgr = CheckpointManager(audit)
        mgr.save_phase_completion(0, "PRE_CHECK")
        assert audit.is_dir()

    # --- history tracking ---

    def test_history_records_actions(self, ckpt: CheckpointManager):
        ckpt.save_phase_start(1, "SETUP")
        ckpt.save_phase_completion(1, "SETUP")
        ckpt.save_phase_start(2, "LIT_SEARCH")

        state = ckpt.load()
        assert len(state["history"]) == 3
        assert state["history"][0]["action"] == "phase_started"
        assert state["history"][1]["action"] == "phase_completed"
        assert state["history"][2]["action"] == "phase_started"

    # --- checkpoint_path property ---

    def test_checkpoint_path(self, ckpt: CheckpointManager, audit_dir: Path):
        assert ckpt.checkpoint_path == audit_dir / "checkpoint.json"
