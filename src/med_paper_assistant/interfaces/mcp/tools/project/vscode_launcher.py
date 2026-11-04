"""Non-blocking VS Code CLI launcher used by workspace tools."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - intentional VS Code CLI integration
from collections.abc import Sequence
from dataclasses import dataclass, field

LAUNCH_WAIT_SECONDS = 5.0


@dataclass
class LaunchResult:
    """Outcome of asking VS Code to open a set of files."""

    cli: str | None
    opened: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)


def find_code_cli() -> str | None:
    """Locate the VS Code CLI (``code`` / ``code.cmd`` on Windows)."""
    for name in ("code", "code.cmd"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _launch_one(cli: str, file_path: str, wait_seconds: float) -> str | None:
    """Start the CLI for one file; return an error message, or None on success."""
    try:
        proc = subprocess.Popen(  # nosec B603 - trusted VS Code CLI, list args, no shell
            [cli, "--goto", file_path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        return str(exc)
    try:
        returncode = proc.wait(timeout=wait_seconds)
    except subprocess.TimeoutExpired:
        # VS Code is still starting up; do not block the server or kill it.
        return None
    if returncode != 0:
        return f"code exited with status {returncode}"
    return None


def open_files_in_vscode(
    file_paths: Sequence[str], wait_seconds: float = LAUNCH_WAIT_SECONDS
) -> LaunchResult:
    """Open files in VS Code, bounded by ``wait_seconds`` per file (blocking call)."""
    cli = find_code_cli()
    result = LaunchResult(cli=cli)
    if cli is None:
        return result
    for file_path in file_paths:
        error = _launch_one(cli, file_path, wait_seconds)
        if error is None:
            result.opened.append(file_path)
        else:
            result.failed[file_path] = error
    return result


def render_launch_report(
    project_name: str,
    existing: Sequence[str],
    not_found: Sequence[str],
    launch: LaunchResult | None,
) -> str:
    """Render the user-facing report for open_project_files."""
    result = f"📂 專案: {project_name}\n\n"
    if launch is not None and launch.cli is None:
        result += (
            "❌ VS Code CLI (`code`) not found on PATH; nothing was opened. "
            "Install the `code` command (VS Code: Shell Command) or open manually:\n"
        )
        result += "".join(f"  - {f}\n" for f in existing)
    elif launch is not None:
        if launch.opened:
            result += "✅ 開啟的文件:\n"
            result += "".join(f"  - {os.path.basename(f)}\n" for f in launch.opened)
        if launch.failed:
            result += "\n❌ 無法開啟的文件:\n"
            result += "".join(
                f"  - {os.path.basename(f)}: {reason}\n" for f, reason in launch.failed.items()
            )
    if not_found:
        result += "\n⚠️ 未找到的文件:\n"
        result += "".join(f"  - {os.path.basename(f)}\n" for f in not_found)
    return result.strip()


__all__ = [
    "LAUNCH_WAIT_SECONDS",
    "LaunchResult",
    "find_code_cli",
    "open_files_in_vscode",
    "render_launch_report",
]
