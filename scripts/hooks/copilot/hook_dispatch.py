"""Window-free, fail-open Windows dispatcher for Copilot/VS Code chat hooks.

Run with ``pythonw.exe`` (GUI subsystem) so no console window is ever created.
Never launch ``*.sh`` hook scripts through the Windows file association: ``.sh``
is usually bound to ``git-bash.exe`` (mintty), a GUI program that opens a new
window and steals focus on every hook event.

Usage: ``pythonw.exe scripts/hooks/copilot/hook_dispatch.py <hook-name>``
where ``<hook-name>`` is ``mode-guard`` or a ``scripts/hooks/copilot/*.sh`` stem.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
REPO_ROOT = HOOK_DIR.parents[2]
FAIL_OPEN = b'{"continue": true}\n'
BASH_TIMEOUT_SECONDS = 4.0
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def find_console_bash() -> Path | None:
    """Return Git for Windows' console ``bash.exe`` (never WSL or git-bash.exe)."""
    candidates: list[Path] = []
    git = shutil.which("git")
    if git:
        git_root = Path(git).resolve().parent.parent
        candidates += [git_root / "bin" / "bash.exe", git_root / "usr" / "bin" / "bash.exe"]
    for env_name in ("ProgramFiles", "ProgramW6432", "LOCALAPPDATA"):
        base = os.environ.get(env_name)
        if base:
            candidates.append(Path(base) / "Git" / "bin" / "bash.exe")
            candidates.append(Path(base) / "Programs" / "Git" / "bin" / "bash.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def run_mode_guard(payload: bytes) -> tuple[bytes, int]:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import copilot_hook_guard

    result = copilot_hook_guard.run_hook(payload.decode("utf-8", errors="replace"))
    return (json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"), 0


def run_shell_hook(name: str, payload: bytes) -> tuple[bytes, int]:
    script = HOOK_DIR / f"{name}.sh"
    bash = find_console_bash()
    if not script.is_file() or bash is None:
        return FAIL_OPEN, 0
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and repo-local script
        [str(bash), script.relative_to(REPO_ROOT).as_posix()],
        input=payload,
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=BASH_TIMEOUT_SECONDS,
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    if completed.returncode in (0, 2) and completed.stdout.strip():
        return completed.stdout, completed.returncode
    return FAIL_OPEN, 0


def dispatch(name: str, payload: bytes) -> tuple[bytes, int]:
    try:
        if name == "mode-guard":
            return run_mode_guard(payload)
        if not name.replace("-", "").isalnum():
            return FAIL_OPEN, 0
        return run_shell_hook(name, payload)
    except Exception:  # noqa: BLE001 - hooks must never block the agent
        return FAIL_OPEN, 0


def main(argv: list[str]) -> int:
    stdin = sys.stdin.buffer if sys.stdin is not None else None
    payload = stdin.read() if stdin is not None else b""
    output, code = dispatch(argv[1] if len(argv) > 1 else "", payload)
    if sys.stdout is not None:
        sys.stdout.buffer.write(output)
        sys.stdout.flush()
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
