"""Phase 11 gate: final delivery with advisory Git provenance checks."""

from __future__ import annotations

import os
import re
import subprocess  # nosec B404 — only runs git commands
from pathlib import Path

from ._base import GateBase
from ._constants import _GIT_GATE_TIMEOUT_SECONDS
from ._types import GateCheck, GateResult


def _run_git(workspace_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(  # nosec B603 B607
        ["git", *args],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(workspace_root),
        timeout=_GIT_GATE_TIMEOUT_SECONDS,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise OSError(detail)
    return result


def _clean_check(status_stdout: str) -> GateCheck:
    status_lines = status_stdout.splitlines()
    dirty_lines = [line for line in status_lines if line and not line.startswith("#")]
    dirty_files = "\n".join(dirty_lines)
    is_clean = len(dirty_lines) == 0
    return GateCheck(
        name="git:clean",
        description="Working tree is clean for optional provenance",
        passed=is_clean,
        details="clean"
        if is_clean
        else f"Uncommitted changes detected; paper export may still proceed:\n{dirty_files[:500]}",
        severity="INFO" if is_clean else "WARNING",
    )


def _commit_check(project_dir: Path, workspace_root: Path) -> GateCheck:
    try:
        project_rel = project_dir.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        project_rel = "projects"

    result = _run_git(
        workspace_root, ["log", "-1", "--name-only", "--format=%H %s", "--", project_rel]
    )
    commit_output = result.stdout.strip()
    commit_lines = commit_output.splitlines()
    changed_files = [line.strip() for line in commit_lines[1:] if line.strip()]
    if project_rel in {"", "."}:
        has_project_files = bool(changed_files)
    else:
        project_prefix = project_rel.rstrip("/") + "/"
        has_project_files = any(
            line == project_rel or line.startswith(project_prefix) for line in changed_files
        )
    return GateCheck(
        name="git:commit_includes_project",
        description="Latest commit includes project files",
        passed=has_project_files,
        details=commit_output[:300] if commit_output else "No commits found",
        severity="WARNING",
    )


class FinalDeliveryPhaseMixin(GateBase):
    """Validation of Phase 11 (final delivery).

    Phase 11 requires valid exports and Phase 10; no separate completion marker exists.
    Git provenance checks (repository, clean tree, latest commit coverage, remote sync)
    are advisory because many users only need a final manuscript export.
    """

    def _validate_phase_11(self) -> GateResult:
        """Phase 11: advisory Git provenance checks."""
        checks = []

        # 1. Check .git exists
        git_dir = self._project_dir.parents[1] / ".git"  # workspace root
        if not git_dir.is_dir():
            # Try project_dir itself
            git_dir = self._project_dir / ".git"
        has_git = git_dir.is_dir()
        checks.append(
            GateCheck(
                name="git:repository",
                description="Git repository available for optional provenance",
                passed=has_git,
                details="found"
                if has_git
                else "No .git directory found; Git provenance is optional for paper-only workflows",
                severity="INFO" if has_git else "WARNING",
            )
        )

        if has_git:
            checks.extend(self._git_provenance_checks(git_dir.parent))

        return GateResult(phase=11, phase_name="Final Delivery", checks=checks, passed=False)

    def _git_provenance_checks(self, workspace_root: Path) -> list[GateCheck]:
        checks: list[GateCheck] = []
        try:
            # 2. Check working tree and push status with one bounded status call.
            status_result = _run_git(
                workspace_root, ["status", "--branch", "--porcelain=v2", "--untracked-files=normal"]
            )
            checks.append(_clean_check(status_result.stdout))

            # 3. Check latest commit contains project files
            checks.append(_commit_check(self._project_dir, workspace_root))

            # 4. Check push status
            checks.append(self._push_check(status_result.stdout))

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            checks.append(
                GateCheck(
                    name="git:error",
                    description="Optional Git provenance command execution",
                    passed=False,
                    details=f"Git command failed; paper delivery may still proceed: {e}",
                    severity="WARNING",
                )
            )
        return checks

    def _push_check(self, branch_info: str) -> GateCheck:
        has_upstream = "branch.upstream" in branch_info
        branch_ab = self._parse_branch_ab(branch_info)
        is_pushed = has_upstream and branch_ab == (0, 0)
        if not has_upstream:
            push_passed = True
            push_details = (
                "No upstream configured; remote publishing is optional for paper delivery"
            )
            push_severity = "INFO"
        elif is_pushed:
            push_passed = True
            push_details = "up to date with remote"
            push_severity = "INFO"
        else:
            push_passed = False
            if branch_ab:
                ahead, behind = branch_ab
                push_details = (
                    f"Remote sync drift: ahead={ahead}, behind={behind}; "
                    "remote sync is optional for paper delivery"
                )
            else:
                push_details = (
                    "Remote sync status unknown; remote sync is optional for paper delivery"
                )
            push_severity = "WARNING"
        return GateCheck(
            name="git:pushed",
            description="Remote sync status, if an upstream is configured",
            passed=push_passed,
            details=push_details,
            severity=push_severity,
        )

    @staticmethod
    def _parse_branch_ab(status_output: str) -> tuple[int, int] | None:
        """Parse `git status --porcelain=v2` ahead/behind counters."""
        match = re.search(r"^# branch\.ab \+(\d+) -(\d+)$", status_output, re.MULTILINE)
        if not match:
            return None
        return int(match.group(1)), int(match.group(2))
