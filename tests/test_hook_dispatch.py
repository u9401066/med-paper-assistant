"""Regression tests for the window-free Windows hook dispatcher.

On Windows ``.sh`` is commonly associated with ``git-bash.exe`` (a GUI mintty
window). Hook configs that run ``*.sh`` without a ``windows`` override open a
new window on every hook event and steal focus from VS Code.
"""

from __future__ import annotations

import importlib.util
import json
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
        for event, entries in config["hooks"].items():
            for entry in entries:
                yield name, event, entry


@pytest.mark.parametrize("name,event,entry", list(_hook_entries()))
def test_hook_entries_have_window_free_windows_command(name: str, event: str, entry: dict) -> None:
    windows = entry.get("windows", "")
    assert windows, f"{name}:{event} must define a windows command"
    assert "pythonw.exe" in windows and "hook_dispatch.py" in windows
    assert not windows.strip().endswith(".sh")
    assert "powershell" not in windows.lower()
    target = windows.split()[-1]
    if target != "mode-guard":
        assert (HOOK_DIR / f"{target}.sh").is_file()


def test_posix_commands_invoke_bash_explicitly() -> None:
    for name, event, entry in _hook_entries():
        command = entry["command"]
        if ".sh" in command:
            assert command.startswith("bash "), f"{name}:{event} must not rely on file association"


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


def test_console_bash_is_never_mintty_or_wsl() -> None:
    bash = _load_dispatch().find_console_bash()
    if bash is not None:
        lowered = str(bash).lower()
        assert not lowered.endswith("git-bash.exe")
        assert "system32" not in lowered
