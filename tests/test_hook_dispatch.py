"""Regression tests for the window-free Windows hook dispatcher.

Two runners read ``.github/hooks/*.json`` on Windows:

* The Copilot agent host (Copilot CLI semantics) only understands ``bash``,
  ``powershell``, ``command`` and ``exec``. Without an explicit ``powershell``
  key it copies ``command`` into PowerShell, where ``bash`` resolves to WSL's
  ``System32\\bash.exe`` (fails -> preToolUse fail-closed) and a bare ``*.sh``
  path goes through the file association (opens git-bash/VS Code windows).
* The legacy VS Code Local harness uses the ``windows`` override.

Both must route through ``pythonw.exe hook_dispatch.py`` and always exit 0.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK_DIR = ROOT / "scripts" / "hooks" / "copilot"
TRACKED_HOOK_CONFIGS = ("mdpaper-lifecycle.json", "mode-guard.json")


def _load_dispatch():
    spec = importlib.util.spec_from_file_location("hook_dispatch", HOOK_DIR / "hook_dispatch.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hook_entries():
    for name in TRACKED_HOOK_CONFIGS:
        config = json.loads((ROOT / ".github" / "hooks" / name).read_text(encoding="utf-8"))
        assert config.get("version") == 1, f"{name} must declare version 1"
        for event, entries in config["hooks"].items():
            for entry in entries:
                yield name, event, entry


def _dispatch_target(command: str) -> str:
    marker = "hook_dispatch.py "
    assert marker in command
    return command.split(marker, 1)[1].split()[0]


@pytest.mark.parametrize("name,event,entry", list(_hook_entries()))
def test_hook_entries_have_window_free_windows_command(name: str, event: str, entry: dict) -> None:
    windows = entry.get("windows", "")
    assert windows, f"{name}:{event} must define a windows command"
    assert "pythonw.exe" in windows and "hook_dispatch.py" in windows
    assert not windows.strip().endswith(".sh")
    assert "powershell" not in windows.lower()
    target = _dispatch_target(windows)
    if target != "mode-guard":
        assert (HOOK_DIR / f"{target}.sh").is_file()


@pytest.mark.parametrize("name,event,entry", list(_hook_entries()))
def test_hook_entries_have_fail_open_powershell_command(name: str, event: str, entry: dict) -> None:
    powershell = entry.get("powershell", "")
    assert powershell, f"{name}:{event} must define an explicit powershell command"
    assert "pythonw.exe" in powershell and "hook_dispatch.py" in powershell
    assert ".sh" not in powershell
    assert "bash" not in powershell.lower()
    assert powershell.rstrip().endswith("exit 0"), "preToolUse failures are fail-closed"
    assert _dispatch_target(powershell) == _dispatch_target(entry["windows"])
    assert "exec" not in entry, "exec cannot be combined with bash/powershell/command"


def test_posix_commands_invoke_bash_explicitly() -> None:
    for name, event, entry in _hook_entries():
        for key in ("bash", "command"):
            command = entry[key]
            if ".sh" in command:
                assert command.startswith("bash "), (
                    f"{name}:{event} must not rely on file association"
                )


def test_pre_tool_use_timeouts_leave_room_for_dispatch() -> None:
    dispatch = _load_dispatch()
    for name, event, entry in _hook_entries():
        assert entry.get("timeoutSec", 0) >= 5, f"{name}:{event} needs an explicit timeoutSec"
        if event == "PreToolUse":
            assert entry["timeoutSec"] > dispatch.BASH_TIMEOUT_SECONDS + 2


def test_mode_guard_dispatch_returns_json() -> None:
    dispatch = _load_dispatch()
    payload = json.dumps({"tool_name": "run_in_terminal", "tool_input": {"command": "rm -rf /"}})
    output, code = dispatch.dispatch("mode-guard", payload.encode("utf-8"))
    result = json.loads(output)
    assert code == 0
    assert result["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_unknown_or_unsafe_hook_name_fails_open() -> None:
    dispatch = _load_dispatch()
    assert dispatch.dispatch("../../evil", b"{}") == (dispatch.FAIL_OPEN, 0)
    assert dispatch.dispatch("does-not-exist", b"{}") == (dispatch.FAIL_OPEN, 0)


def test_missing_bash_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    dispatch = _load_dispatch()
    monkeypatch.setattr(dispatch, "find_console_bash", lambda: None)
    assert dispatch.dispatch("session-init", b"{}") == (dispatch.FAIL_OPEN, 0)


def test_shell_hook_nonzero_exit_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    dispatch = _load_dispatch()

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=2, stdout=b'{"x": 1}', stderr=b"")

    monkeypatch.setattr(dispatch.subprocess, "run", fake_run)
    assert dispatch.dispatch("session-init", b"{}") == (dispatch.FAIL_OPEN, 0)


def test_main_always_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    dispatch = _load_dispatch()

    def boom(*_args, **_kwargs):
        raise RuntimeError("broken")

    monkeypatch.setattr(dispatch, "dispatch", boom)
    assert dispatch.main(["hook_dispatch.py", "session-init"]) == 0


def test_console_bash_is_never_mintty_or_wsl() -> None:
    bash = _load_dispatch().find_console_bash()
    if bash is not None:
        lowered = str(bash).lower()
        assert not lowered.endswith("git-bash.exe")
        assert "system32" not in lowered


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell hook path")
@pytest.mark.skipif(
    not (ROOT / ".venv" / "Scripts" / "pythonw.exe").is_file(), reason="needs repo .venv"
)
def test_mode_guard_powershell_command_round_trip() -> None:
    entry = next(e for n, _, e in _hook_entries() if n == "mode-guard.json")
    payload = json.dumps({"tool_name": "run_in_terminal", "tool_input": {"command": "rm -rf /"}})
    completed = subprocess.run(  # noqa: S603 - fixed powershell + repo config
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", entry["powershell"]],
        input=payload.encode("utf-8"),
        capture_output=True,
        cwd=ROOT,
        timeout=60,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    assert completed.returncode == 0
    result = json.loads(completed.stdout)
    assert result["hookSpecificOutput"]["permissionDecision"] == "ask"
