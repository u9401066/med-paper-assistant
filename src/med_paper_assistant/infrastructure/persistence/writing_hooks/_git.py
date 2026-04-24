"""Writing Hooks — Git status hook mixin (G9)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from ._models import HookIssue, HookResult

logger = structlog.get_logger()


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

        # Find workspace root (walk up from project_dir)
        workspace_root = self._project_dir
        for _ in range(5):
            if (workspace_root / ".git").is_dir():
                break
            parent = workspace_root.parent
            if parent == workspace_root:
                break
            workspace_root = parent

        if not (workspace_root / ".git").is_dir():
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

        import os
        import subprocess  # nosec B404 — only runs git commands

        try:
            env = os.environ.copy()
            env["GIT_OPTIONAL_LOCKS"] = "0"
            result = subprocess.run(  # nosec B603 B607
                ["git", "status", "--branch", "--porcelain=v2", "--untracked-files=normal"],
                capture_output=True,
                text=True,
                cwd=str(workspace_root),
                timeout=3,
                env=env,
            )
            status_lines = result.stdout.strip().split("\n")
            dirty_files = [line for line in status_lines if line.strip() and not line.startswith("#")]
            stats["dirty_files"] = len(dirty_files)

            if dirty_files:
                issues.append(
                    HookIssue(
                        hook_id="G9",
                        severity="WARNING",
                        section="git",
                        message=f"{len(dirty_files)} uncommitted file(s) detected",
                        location="\n".join(dirty_files[:10]),
                        suggestion="Optional provenance step: commit local changes if this paper project uses Git",
                    )
                )

            # Check unpushed commits
            has_upstream = "branch.upstream" in result.stdout
            is_pushed = has_upstream and "branch.ab +0" in result.stdout
            stats["has_upstream"] = has_upstream
            stats["is_pushed"] = is_pushed

            if has_upstream and not is_pushed:
                issues.append(
                    HookIssue(
                        hook_id="G9",
                        severity="WARNING",
                        section="git",
                        message="Unpushed commits detected",
                        suggestion="Optional provenance step: push if this project is configured with a remote",
                    )
                )
            elif not has_upstream:
                stats["remote_sync"] = "not configured"

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            issues.append(
                HookIssue(
                    hook_id="G9",
                    severity="WARNING",
                    section="git",
                    message=f"Git command failed: {e}",
                )
            )

        passed = all(i.severity != "CRITICAL" for i in issues)
        return HookResult(hook_id="G9", passed=passed, issues=issues, stats=stats)
