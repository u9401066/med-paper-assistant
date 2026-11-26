"""Unit and contract tests for Antigravity lifecycle hooks (.agents/hooks.json)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS_JSON = ROOT / ".agents" / "hooks.json"
DISPATCHER_PATH = ROOT / "scripts" / "hooks" / "antigravity_dispatch.py"


def _load_dispatcher():
    spec = importlib.util.spec_from_file_location("antigravity_dispatch", DISPATCHER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_mode(root: Path, mode: str) -> None:
    config = {
        "mode": mode,
        "modes": {
            "development": {"protected_paths": []},
            "normal": {"protected_paths": ["src/", "AGENTS.md", ".github/"]},
            "research": {"protected_paths": ["src/", "AGENTS.md", ".github/"]},
        },
    }
    (root / ".copilot-mode.json").write_text(json.dumps(config), encoding="utf-8")


def test_hooks_json_matches_antigravity_schema() -> None:
    config = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    assert "medpaper-lifecycle" in config
    spec = config["medpaper-lifecycle"]
    assert set(spec) == {"SessionStart", "PreInvocation", "PreToolUse", "PostToolUse", "Stop"}

    for flat_event in ("SessionStart", "PreInvocation", "Stop"):
        assert isinstance(spec[flat_event], list) and spec[flat_event]
        for handler in spec[flat_event]:
            assert handler["type"] == "command"
            assert "antigravity_dispatch.py" in handler["command"]
            assert "uv run" not in handler["command"]

    for grouped_event in ("PreToolUse", "PostToolUse"):
        groups = spec[grouped_event]
        assert isinstance(groups, list) and groups
        for group in groups:
            assert group["matcher"]
            assert isinstance(group["hooks"], list) and group["hooks"]
            for handler in group["hooks"]:
                assert handler["type"] == "command"
                assert "antigravity_dispatch.py" in handler["command"]
                assert "uv run" not in handler["command"]


def test_pre_tool_use_denies_protected_path_in_normal_mode(tmp_path: Path) -> None:
    _write_mode(tmp_path, "normal")
    dispatch = _load_dispatcher()
    payload = {
        "hookEventName": "PreToolUse",
        "cwd": str(tmp_path),
        "toolCall": {
            "id": "t1",
            "name": "write_file",
            "args": {"Path": str(tmp_path / "src" / "main.py")},
        },
    }
    raw, code = dispatch.dispatch("pre-tool-use", json.dumps(payload).encode("utf-8"))
    result = json.loads(raw)
    assert code == 0
    assert result["decision"] == "deny"
    assert "protected" in result["reason"].lower()


def test_pre_tool_use_asks_on_destructive_run_command(tmp_path: Path) -> None:
    _write_mode(tmp_path, "development")
    dispatch = _load_dispatcher()
    payload = {
        "hookEventName": "PreToolUse",
        "cwd": str(tmp_path),
        "toolCall": {
            "id": "t2",
            "name": "run_command",
            "args": {"CommandLine": "git reset --hard HEAD~1"},
        },
    }
    raw, code = dispatch.dispatch("pre-tool-use", json.dumps(payload).encode("utf-8"))
    result = json.loads(raw)
    assert code == 0
    assert result["decision"] == "ask"


def test_pre_tool_use_asks_on_fallback_save_reference(tmp_path: Path) -> None:
    _write_mode(tmp_path, "development")
    dispatch = _load_dispatcher()
    payload = {
        "hookEventName": "PreToolUse",
        "cwd": str(tmp_path),
        "toolCall": {"id": "t3", "name": "mdpaper_save_reference", "args": {}},
    }
    raw, code = dispatch.dispatch("pre-tool-use", json.dumps(payload).encode("utf-8"))
    result = json.loads(raw)
    assert code == 0
    assert result["decision"] == "ask"
    assert "save_reference_mcp" in result["reason"]


def test_pre_tool_use_allows_safe_calls_and_fails_open(tmp_path: Path) -> None:
    _write_mode(tmp_path, "development")
    dispatch = _load_dispatcher()
    safe_payload = {
        "hookEventName": "PreToolUse",
        "cwd": str(tmp_path),
        "toolCall": {
            "id": "t4",
            "name": "edit_file",
            "args": {"Path": str(tmp_path / "README.md")},
        },
    }
    raw, code = dispatch.dispatch("pre-tool-use", json.dumps(safe_payload).encode("utf-8"))
    assert code == 0
    assert json.loads(raw) == {"decision": "allow"}

    bad_raw, bad_code = dispatch.dispatch("pre-tool-use", b"{not valid json")
    assert bad_code == 0
    assert json.loads(bad_raw) == {"decision": "allow"}


def test_session_start_and_pre_invocation_inject_system_message(tmp_path: Path) -> None:
    _write_mode(tmp_path, "research")
    dispatch = _load_dispatcher()

    start_raw, code = dispatch.dispatch(
        "session-start",
        json.dumps({"cwd": str(tmp_path), "hookEventName": "SessionStart"}).encode("utf-8"),
    )
    assert code == 0
    start_out = json.loads(start_raw)
    assert "injectSteps" in start_out
    msg = start_out["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "MODE: research" in msg

    first_turn_raw, _ = dispatch.dispatch(
        "pre-invocation",
        json.dumps(
            {"cwd": str(tmp_path), "invocationNum": 1, "lastUserInput": "請幫我寫草稿 Introduction"}
        ).encode("utf-8"),
    )
    first_turn = json.loads(first_turn_raw)
    assert "WRITING INTENT" in first_turn["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert (
        'validation_action(action="concept")'
        in first_turn["injectSteps"][0]["systemMessage"]["systemMessage"]
    )

    second_step_raw, _ = dispatch.dispatch(
        "pre-invocation",
        json.dumps(
            {"cwd": str(tmp_path), "invocationNum": 2, "lastUserInput": "請幫我寫草稿 Introduction"}
        ).encode("utf-8"),
    )
    assert json.loads(second_step_raw) == {}


def test_pre_invocation_suppresses_paper_noise_in_development_mode(tmp_path: Path) -> None:
    _write_mode(tmp_path, "development")
    dispatch = _load_dispatcher()

    meta_raw, code = dispatch.dispatch(
        "pre-invocation",
        json.dumps(
            {
                "cwd": str(tmp_path),
                "invocationNum": 1,
                "lastUserInput": "你覺得這個全自動寫論文的repo和plugin還缺什麼？",
            }
        ).encode("utf-8"),
    )
    assert code == 0
    assert json.loads(meta_raw) == {}


def test_pre_tool_use_asks_on_compact_reference_save_agent(tmp_path: Path) -> None:
    _write_mode(tmp_path, "development")
    dispatch = _load_dispatcher()
    payload = {
        "hookEventName": "PreToolUse",
        "cwd": str(tmp_path),
        "toolCall": {
            "id": "t6",
            "name": "med-paper-assistant_mdpaper_reference_action",
            "args": {"action": "save_agent"},
        },
    }
    raw, code = dispatch.dispatch("pre-tool-use", json.dumps(payload).encode("utf-8"))
    result = json.loads(raw)
    assert code == 0
    assert result["decision"] == "ask"
    assert "save_reference_mcp" in result["reason"]


def test_post_tool_use_and_stop_return_empty_json(tmp_path: Path) -> None:
    _write_mode(tmp_path, "development")
    dispatch = _load_dispatcher()

    post_raw, post_code = dispatch.dispatch(
        "post-tool-use",
        json.dumps(
            {
                "cwd": str(tmp_path),
                "toolCall": {"id": "t5", "name": "write_file", "args": {"Path": "drafts/a.md"}},
            }
        ).encode("utf-8"),
    )
    assert post_code == 0
    assert json.loads(post_raw) == {}

    stop_raw, stop_code = dispatch.dispatch(
        "stop",
        json.dumps({"cwd": str(tmp_path), "terminationReason": "NO_TOOL_CALL"}).encode("utf-8"),
    )
    assert stop_code == 0
    assert json.loads(stop_raw) == {}


def test_dispatcher_cli_round_trip_from_agents_dir() -> None:
    payload = json.dumps(
        {
            "cwd": str(ROOT),
            "hookEventName": "PreToolUse",
            "toolCall": {
                "id": "cli-1",
                "name": "run_command",
                "args": {"CommandLine": "rm -rf /"},
            },
        }
    ).encode("utf-8")
    completed = subprocess.run(  # noqa: S603 - fixed python executable and repo script
        [sys.executable, "../scripts/hooks/antigravity_dispatch.py", "pre-tool-use"],
        input=payload,
        cwd=ROOT / ".agents",
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["decision"] == "ask"
