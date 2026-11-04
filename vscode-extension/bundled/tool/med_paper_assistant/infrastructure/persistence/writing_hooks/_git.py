"""Writing Hooks — Git status hook mixin (G9)."""

from __future__ import annotations

import os
import re
import subprocess  # nosec B404 — only runs fixed git commands
from pathlib import Path
from typing import Any

import structlog

from ._models import HookIssue, HookResult

logger = structlog.get_logger()


def _run_git(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run a fixed git command with UTF-8 decoding (independent of the OS locale)."""
    return subprocess.run(  # nosec B603 B607
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        timeout=3,
        env=env,
    )


def _git_toplevel(project_dir: Path, env: dict[str, str]) -> Path | None:
    try:
        root_result = _run_git(["rev-parse", "--show-toplevel"], project_dir, env)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if root_result.returncode != 0 or not root_result.stdout.strip():
        return None
    return Path(root_result.stdout.strip()).resolve()


def _git_failure_issue(message: str) -> HookIssue:
    return HookIssue(
        hook_id="G9",
        severity="WARNING",
        section="git",
        message=f"Git command failed: {message}",
    )


def _dirty_files_issue(dirty_files: list[str]) -> HookIssue:
    return HookIssue(
        hook_id="G9",
        severity="WARNING",
        section="git",
        message=f"{len(dirty_files)} uncommitted file(s) detected",
        location="\n".join(dirty_files[:10]),
        suggestion="Optional provenance step: commit local changes if this paper project uses Git",
    )


def _drift_issue(branch_ab: tuple[int, int] | None) -> HookIssue:
    drift = ""
    if branch_ab:
        ahead, behind = branch_ab
        drift = f" (ahead={ahead}, behind={behind})"
    return HookIssue(
        hook_id="G9",
        severity="WARNING",
        section="git",
        message=f"Git remote drift detected{drift}",
        suggestion="Optional provenance step: push if this project is configured with a remote",
    )


def _collect_status(stdout: str, issues: list[HookIssue], stats: dict[str, Any]) -> None:
    """Fold ``git status --porcelain=v2 --branch`` output into ``issues`` and ``stats``."""
    status_lines = stdout.strip().split("\n")
    dirty_files = [line for line in status_lines if line.strip() and not line.startswith("#")]
    stats["dirty_files"] = len(dirty_files)

    if dirty_files:
        issues.append(_dirty_files_issue(dirty_files))

    # Check remote drift from porcelain v2 ahead/behind counters.
    has_upstream = "branch.upstream" in stdout
    branch_ab_match = re.search(r"^# branch\.ab \+(\d+) -(\d+)$", stdout, re.M)
    branch_ab = (
        (int(branch_ab_match.group(1)), int(branch_ab_match.group(2))) if branch_ab_match else None
    )
    is_pushed = has_upstream and branch_ab == (0, 0)
    stats["has_upstream"] = has_upstream
    stats["branch_ahead_behind"] = branch_ab
    stats["is_pushed"] = is_pushed

    if has_upstream and not is_pushed:
        issues.append(_drift_issue(branch_ab))
    elif not has_upstream:
        stats["remote_sync"] = "not configured"


class GitHooksMixin:
    """G-series hooks: git repository status checks."""

    _project_dir: Path

    def check_git_status(self) -> HookResult:
        """
        G9: Check optional git provenance status.

        Paper-first policy: Git helps provenance, but a paper-only workflow may
        have no remote or no repository at all. This hook must never block
        scientific writing gates solely because code was not pushed.
        """
        issues: list[HookIssue] = []
        stats: dict[str, Any] = {}

        env = os.environ.copy()
        env["GIT_OPTIONAL_LOCKS"] = "0"
        workspace_root = _git_toplevel(self._project_dir, env)
        if workspace_root is None:
            issues.append(
                HookIssue(
                    hook_id="G9",
                    severity="WARNING",
                    section="git",
                    message="No .git directory found",
                    suggestion="Optional: initialize git if you want code/provenance tracking",
                )
            )
            return HookResult(hook_id="G9", passed=True, issues=issues, stats={"git": "not found"})

        try:
            result = _run_git(
                ["status", "--branch", "--porcelain=v2", "--untracked-files=normal"],
                workspace_root,
                env,
            )
            if result.returncode != 0:
                message = result.stderr.strip() or "unknown git status failure"
                issues.append(_git_failure_issue(message))
                return HookResult(hook_id="G9", passed=True, issues=issues, stats=stats)

            _collect_status(result.stdout, issues, stats)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            issues.append(_git_failure_issue(str(e)))

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="G9", passed=passed, issues=issues, stats=stats)
