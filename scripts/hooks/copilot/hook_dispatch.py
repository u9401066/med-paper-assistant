"""Window-free, fail-open dispatcher for Copilot/VS Code chat hooks.

Run with ``pythonw.exe`` (GUI subsystem) so no console window is ever created.
The lifecycle hooks are implemented in-process by the ``mdpaper_hooks`` package
(stdlib only); ``mode-guard`` calls ``scripts/copilot_hook_guard.py`` in-process.
There is no bash dependency and no subprocess for the hook logic. The only
child process is a read-only ``git diff`` in ``pre-tool-guard`` for release/push
checks (see ``mdpaper_hooks/pre_tool_guard.py``).

The ``*.sh`` files next to this file are thin POSIX shims that exec this script,
so Claude Code / Copilot on Linux or macOS share the single implementation.
Never launch those shims through the Windows file association (``.sh`` may be
bound to ``git-bash.exe`` or an editor, which steals focus on every hook event)
and never rely on ``bash`` from ``PATH`` (usually WSL's ``System32\\bash.exe``).
There is deliberately no bash fallback: the shims call back into this
dispatcher, so a fallback would recurse.

The process always exits 0. The Copilot agent host treats a failing
``preToolUse`` command as fail-closed (the tool call is denied), so decisions
must be expressed only through the JSON written to stdout. Any exception is
logged to ``.github/hooks/_state/hook_errors.jsonl`` and answered with the
neutral ``{"continue": true}``; nothing is ever written to stderr.

Usage: ``pythonw.exe scripts/hooks/copilot/hook_dispatch.py <hook-name>``
where ``<hook-name>`` is ``mode-guard`` or a ``scripts/hooks/copilot/*.sh`` stem.
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOOK_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = HOOK_DIR.parents[1]
REPO_ROOT = HOOK_DIR.parents[2]
FAIL_OPEN = b'{"continue": true}\n'
ERROR_LOG = Path(".github") / "hooks" / "_state" / "hook_errors.jsonl"
ERROR_LOG_MAX_BYTES = 256 * 1024
MODE_GUARD = "mode-guard"


def _encode(result: Any) -> bytes:
    if not result:
        return FAIL_OPEN
    return (json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8")


def log_error(name: str, exc: BaseException) -> None:
    """Best-effort error log; never raises."""
    try:
        path = REPO_ROOT / ERROR_LOG
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > ERROR_LOG_MAX_BYTES:
            path.unlink()
        record = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hook": name,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": "".join(traceback.format_exception(exc))[-2000:],
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - logging must not break the hook
        pass


def run_mode_guard(payload: str) -> Any:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import copilot_hook_guard

    return copilot_hook_guard.run_hook(payload)


def run_lifecycle_hook(name: str, payload: str) -> Any:
    if str(HOOK_DIR) not in sys.path:
        sys.path.insert(0, str(HOOK_DIR))
    import mdpaper_hooks

    return mdpaper_hooks.run_hook(name, payload, REPO_ROOT)


def dispatch(name: str, payload: bytes) -> tuple[bytes, int]:
    """Run hook ``name`` on the raw stdin ``payload``; always ``(json bytes, 0)``."""
    try:
        text = payload.decode("utf-8-sig", errors="replace")
        hook = name.strip().lower().replace("_", "-")
        if hook == MODE_GUARD:
            return _encode(run_mode_guard(text)), 0
        return _encode(run_lifecycle_hook(hook, text)), 0
    except Exception as exc:  # noqa: BLE001 - hooks must never block the agent
        log_error(name, exc)
        return FAIL_OPEN, 0


def main(argv: list[str]) -> int:
    try:
        stdin = sys.stdin.buffer if sys.stdin is not None else None
        payload = stdin.read() if stdin is not None else b""
        output, _ = dispatch(argv[1] if len(argv) > 1 else "", payload)
        if sys.stdout is not None:
            sys.stdout.buffer.write(output)
            sys.stdout.flush()
    except Exception:  # noqa: BLE001 - a broken pipe must not deny tool calls
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
