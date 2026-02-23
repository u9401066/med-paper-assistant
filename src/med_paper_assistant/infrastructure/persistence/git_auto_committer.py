"""
Git Auto-Committer — Automatic git commits at safe points.

Provides a safety net for long agent sessions: automatically commits
draft changes, reference saves, and pipeline phase completions.

Architecture:
  Infrastructure layer service. Called after significant write operations.
  Uses subprocess to call git — no Python git library dependency.

Safety:
  - Only commits within the project directory
  - Only adds specific files (not blanket `git add .`)
  - Non-blocking: failures are logged but never raise
  - Messages are structured for easy `git log --grep`
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

CommitType = Literal[
    "draft",        # Draft write/patch/sync
    "reference",    # Reference saved
    "checkpoint",   # Pipeline phase completed
    "snapshot",     # Manual checkpoint / session save
]

# Structured commit message prefixes for git log --grep
_COMMIT_PREFIXES: dict[CommitType, str] = {
    "draft": "📝 auto-draft",
    "reference": "📚 auto-ref",
    "checkpoint": "🔖 auto-checkpoint",
    "snapshot": "💾 auto-snapshot",
}


class GitAutoCommitter:
    """
    Auto-commit changes at safe points in the workflow.

    Usage:
        committer = GitAutoCommitter(repo_dir="projects/my-paper")

        # After a draft change:
        committer.commit_draft("introduction.md", "patch_draft: added methods paragraph")

        # After saving a reference:
        committer.commit_reference("tang2023_38049909")

        # After completing a pipeline phase:
        committer.commit_checkpoint(phase=2, phase_name="LITERATURE_SEARCH")
    """

    def __init__(self, repo_dir: str | Path) -> None:
        self._repo_dir = Path(repo_dir)
        self._enabled = self._check_git_repo()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _check_git_repo(self) -> bool:
        """Check if the directory is inside a git repository."""
        try:
            result = self._run_git(["rev-parse", "--is-inside-work-tree"])
            return result.returncode == 0
        except FileNotFoundError:
            logger.info("Git not found on PATH — auto-commit disabled")
            return False

    def commit_draft(self, filename: str, reason: str = "") -> bool:
        """
        Auto-commit after a draft change.

        Args:
            filename: Draft filename (e.g., "introduction.md")
            reason: What triggered the change (e.g., "patch_draft", "sync_references")
        """
        msg = f"{_COMMIT_PREFIXES['draft']}: {filename}"
        if reason:
            msg += f" ({reason})"
        return self._auto_commit(
            paths=[f"drafts/{filename}", "drafts/.snapshots/"],
            message=msg,
        )

    def commit_reference(self, citation_key: str) -> bool:
        """Auto-commit after saving a reference."""
        # Extract PMID for the path
        pmid = citation_key.split("_")[-1] if "_" in citation_key else citation_key
        return self._auto_commit(
            paths=[f"references/{pmid}/", f"references/{citation_key}.md"],
            message=f"{_COMMIT_PREFIXES['reference']}: {citation_key}",
        )

    def commit_checkpoint(self, phase: int, phase_name: str) -> bool:
        """Auto-commit after a pipeline phase completion."""
        return self._auto_commit(
            paths=[".audit/checkpoint.json", ".audit/"],
            message=f"{_COMMIT_PREFIXES['checkpoint']}: Phase {phase} ({phase_name})",
        )

    def commit_snapshot(self, reason: str = "session save") -> bool:
        """
        Auto-commit a general snapshot (e.g., end of conversation).

        Adds all tracked changes under the project directory.
        """
        return self._auto_commit(
            paths=["drafts/", "references/", ".audit/", ".memory/"],
            message=f"{_COMMIT_PREFIXES['snapshot']}: {reason}",
        )

    def _auto_commit(self, paths: list[str], message: str) -> bool:
        """
        Stage files and commit if there are changes.

        Returns True if a commit was made, False otherwise.
        """
        if not self._enabled:
            return False

        try:
            # Stage specific paths (ignore errors for non-existent paths)
            for p in paths:
                full_path = self._repo_dir / p
                if full_path.exists():
                    self._run_git(["add", str(full_path)])

            # Check if there's anything to commit
            status = self._run_git(["diff", "--cached", "--name-only"])
            if not status.stdout.strip():
                logger.debug("No staged changes — skipping auto-commit")
                return False

            # Commit
            result = self._run_git(["commit", "-m", message, "--no-verify"])
            if result.returncode == 0:
                logger.info("Auto-committed: %s", message)
                return True
            else:
                logger.warning("Auto-commit failed: %s", result.stderr)
                return False

        except Exception as e:
            logger.warning("Auto-commit error (non-fatal): %s", e)
            return False

    def _run_git(self, args: list[str]) -> subprocess.CompletedProcess:
        """Run a git command in the repo directory."""
        return subprocess.run(
            ["git"] + args,
            cwd=str(self._repo_dir),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
