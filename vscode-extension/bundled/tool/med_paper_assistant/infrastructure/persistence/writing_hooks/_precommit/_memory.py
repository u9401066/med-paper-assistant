"""Writing Hooks — P6 memory-sync gate."""

from __future__ import annotations

import time
from pathlib import Path

import structlog

from .._models import HookIssue, HookResult

logger = structlog.get_logger()

_STALENESS_THRESHOLD = 7200  # 2 hours in seconds


def _find_workspace_root(project_dir: Path) -> Path:
    workspace_root = project_dir
    for _ in range(5):
        if (workspace_root / ".git").is_dir():
            break
        parent = workspace_root.parent
        if parent == workspace_root:
            break
        workspace_root = parent
    return workspace_root


def _memory_files(project_dir: Path) -> list[Path]:
    memory_dir = project_dir / ".memory"
    memory_bank_dir = _find_workspace_root(project_dir) / "memory-bank"

    files_to_check: list[Path] = []
    if memory_dir.is_dir():
        files_to_check.append(memory_dir / "activeContext.md")
    if memory_bank_dir.is_dir():
        files_to_check.append(memory_bank_dir / "activeContext.md")
        files_to_check.append(memory_bank_dir / "progress.md")
    return files_to_check


def _classify_memory_files(files: list[Path]) -> tuple[int, list[str], list[str]]:
    """Return (files checked, stale descriptions, fresh names)."""
    checked = 0
    stale_files: list[str] = []
    fresh_files: list[str] = []
    now = time.time()

    for fpath in files:
        if not fpath.is_file():
            continue
        checked += 1
        try:
            age = now - fpath.stat().st_mtime
            if age > _STALENESS_THRESHOLD:
                stale_files.append(f"{fpath.name} (age: {age / 3600:.1f}h)")
            else:
                fresh_files.append(fpath.name)
        except OSError:
            stale_files.append(f"{fpath.name} (unreadable)")
    return checked, stale_files, fresh_files


def _stale_memory_issue(stale_files: list[str]) -> HookIssue:
    return HookIssue(
        hook_id="P6",
        severity="WARNING",
        section="memory",
        message=f"Memory files appear stale: {', '.join(stale_files)}",
        suggestion=(
            "Run sync_workspace_state() or update memory-bank/ "
            "before committing to preserve session context"
        ),
    )


class MemorySyncHooksMixin:
    """P6: memory files must have been refreshed before committing."""

    _project_dir: Path

    def check_memory_sync(self) -> HookResult:
        """Hook P6: Verify memory files were updated before commit.

        Code-Enforced pre-commit check. Verifies that project .memory/
        or workspace memory-bank/ files have been modified recently
        (within the last 2 hours), indicating the Agent synced context.

        Previously Agent-Driven (relied on Agent reading git-precommit SKILL.md).
        Now Code-Enforced for weak model resilience.
        """
        issues: list[HookIssue] = []

        memory_files_checked, stale_files, fresh_files = _classify_memory_files(
            _memory_files(self._project_dir)
        )

        if memory_files_checked == 0:
            return HookResult(
                hook_id="P6",
                passed=True,
                stats={"note": "No memory files found to check"},
            )

        if stale_files and not fresh_files:
            issues.append(_stale_memory_issue(stale_files))

        passed = len(issues) == 0
        stats = {
            "files_checked": memory_files_checked,
            "fresh_files": fresh_files,
            "stale_files": stale_files,
        }

        logger.info(
            "Hook P6 complete", passed=passed, fresh=len(fresh_files), stale=len(stale_files)
        )
        return HookResult(hook_id="P6", passed=passed, issues=issues, stats=stats)
