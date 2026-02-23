"""Tests for GitAutoCommitter — auto-commit at safe points."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from med_paper_assistant.infrastructure.persistence.git_auto_committer import (
    GitAutoCommitter,
    _COMMIT_PREFIXES,
)


def _git_log(cwd: Path) -> str:
    """Read the latest git log message, handling Windows encoding."""
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=str(cwd),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout or ""


@pytest.fixture
def git_repo(tmp_path):
    """Create a real temporary git repository."""
    subprocess.run(
        ["git", "init"],
        cwd=str(tmp_path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(tmp_path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path),
        capture_output=True,
        check=True,
    )
    # Need at least one commit for git diff --cached to work
    readme = tmp_path / "README.md"
    readme.write_text("init", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path),
        capture_output=True,
        check=True,
    )
    return tmp_path


# ──────────────────────────────────────────────────────────────────────────────
# Initialization
# ──────────────────────────────────────────────────────────────────────────────


class TestInit:
    def test_enabled_in_git_repo(self, git_repo):
        committer = GitAutoCommitter(git_repo)
        assert committer.enabled is True

    def test_disabled_outside_git_repo(self, tmp_path):
        committer = GitAutoCommitter(tmp_path)
        assert committer.enabled is False

    def test_disabled_when_git_not_found(self, tmp_path):
        with patch(
            "med_paper_assistant.infrastructure.persistence.git_auto_committer.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            committer = GitAutoCommitter(tmp_path)
            assert committer.enabled is False


# ──────────────────────────────────────────────────────────────────────────────
# commit_draft
# ──────────────────────────────────────────────────────────────────────────────


class TestCommitDraft:
    def test_commits_when_file_changed(self, git_repo):
        committer = GitAutoCommitter(git_repo)
        drafts = git_repo / "drafts"
        drafts.mkdir()
        draft_file = drafts / "intro.md"
        draft_file.write_text("# Introduction\n", encoding="utf-8")

        result = committer.commit_draft("intro.md", "create_draft")
        assert result is True

        # Verify commit exists
        assert "auto-draft" in _git_log(git_repo)

    def test_skips_when_no_changes(self, git_repo):
        committer = GitAutoCommitter(git_repo)
        result = committer.commit_draft("nonexistent.md")
        assert result is False

    def test_includes_reason_in_message(self, git_repo):
        committer = GitAutoCommitter(git_repo)
        drafts = git_repo / "drafts"
        drafts.mkdir()
        (drafts / "test.md").write_text("test", encoding="utf-8")

        committer.commit_draft("test.md", "patch_draft")

        assert "patch_draft" in _git_log(git_repo)


# ──────────────────────────────────────────────────────────────────────────────
# commit_reference
# ──────────────────────────────────────────────────────────────────────────────


class TestCommitReference:
    def test_commits_reference_dir(self, git_repo):
        committer = GitAutoCommitter(git_repo)
        ref_dir = git_repo / "references" / "38049909"
        ref_dir.mkdir(parents=True)
        (ref_dir / "metadata.json").write_text('{"title":"test"}', encoding="utf-8")

        result = committer.commit_reference("tang2023_38049909")
        assert result is True

        log_msg = _git_log(git_repo)
        assert "auto-ref" in log_msg
        assert "tang2023_38049909" in log_msg


# ──────────────────────────────────────────────────────────────────────────────
# commit_checkpoint
# ──────────────────────────────────────────────────────────────────────────────


class TestCommitCheckpoint:
    def test_commits_audit_files(self, git_repo):
        committer = GitAutoCommitter(git_repo)
        audit = git_repo / ".audit"
        audit.mkdir()
        (audit / "checkpoint.json").write_text('{"phase":2}', encoding="utf-8")

        result = committer.commit_checkpoint(2, "LITERATURE_SEARCH")
        assert result is True

        log_msg = _git_log(git_repo)
        assert "auto-checkpoint" in log_msg
        assert "Phase 2" in log_msg


# ──────────────────────────────────────────────────────────────────────────────
# commit_snapshot
# ──────────────────────────────────────────────────────────────────────────────


class TestCommitSnapshot:
    def test_commits_multiple_dirs(self, git_repo):
        committer = GitAutoCommitter(git_repo)
        for d in ["drafts", "references", ".audit", ".memory"]:
            (git_repo / d).mkdir(exist_ok=True)
            (git_repo / d / "test.txt").write_text("data", encoding="utf-8")

        result = committer.commit_snapshot("session end")
        assert result is True

        log_msg = _git_log(git_repo)
        assert "auto-snapshot" in log_msg
        assert "session end" in log_msg


# ──────────────────────────────────────────────────────────────────────────────
# Error handling (non-blocking)
# ──────────────────────────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_returns_false_when_disabled(self, tmp_path):
        committer = GitAutoCommitter(tmp_path)
        assert committer.enabled is False
        assert committer.commit_draft("test.md") is False

    def test_non_blocking_on_subprocess_error(self, git_repo):
        committer = GitAutoCommitter(git_repo)
        with patch.object(
            committer,
            "_run_git",
            side_effect=subprocess.SubprocessError("test error"),
        ):
            # Should not raise
            result = committer.commit_draft("test.md")
            assert result is False
