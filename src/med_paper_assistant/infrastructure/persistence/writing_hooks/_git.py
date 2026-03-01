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
        G9: Check for uncommitted changes in git.

        Code-Enforced hook that detects dirty working tree.
        Agent MUST auto-commit + push if this hook fails.
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
                    suggestion="Initialize git repository",
                )
            )
            return HookResult(hook_id="G9", passed=True, issues=issues, stats={"git": "not found"})

        import subprocess  # nosec B404 — only runs git commands

        try:
            result = subprocess.run(  # nosec B603 B607
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=str(workspace_root),
                timeout=10,
            )
            dirty_files = [line for line in result.stdout.strip().split("\n") if line.strip()]
            stats["dirty_files"] = len(dirty_files)

            if dirty_files:
                issues.append(
                    HookIssue(
                        hook_id="G9",
                        severity="CRITICAL",
                        section="git",
                        message=f"{len(dirty_files)} uncommitted file(s) detected",
                        location="\n".join(dirty_files[:10]),
                        suggestion="Auto-commit and push: git add -A && git commit && git push",
                    )
                )

            # Check unpushed commits
            result2 = subprocess.run(  # nosec B603 B607
                ["git", "status", "--branch", "--porcelain=v2"],
                capture_output=True,
                text=True,
                cwd=str(workspace_root),
                timeout=10,
            )
            has_upstream = "branch.upstream" in result2.stdout
            is_pushed = "branch.ab +0" in result2.stdout
            stats["has_upstream"] = has_upstream
            stats["is_pushed"] = is_pushed

            if has_upstream and not is_pushed:
                issues.append(
                    HookIssue(
                        hook_id="G9",
                        severity="CRITICAL",
                        section="git",
                        message="Unpushed commits detected",
                        suggestion="Push to remote: git push",
                    )
                )

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
