"""Behaviour tests for the in-process Python Copilot lifecycle hooks.

The hooks live in ``scripts/hooks/copilot/mdpaper_hooks`` and replace the former
bash scripts. These tests feed representative stdin payloads to every hook with
``tmp_path`` workspaces (no bash, no jq) and assert the decisions and messages
that the ``*.sh`` implementations produced.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK_DIR = ROOT / "scripts" / "hooks" / "copilot"
PACKAGE_DIR = HOOK_DIR / "mdpaper_hooks"
LIFECYCLE_HOOKS = (
    "session-init",
    "prompt-analyzer",
    "pre-tool-guard",
    "post-tool-check",
    "pre-compact-save",
    "subagent-init",
    "session-stop",
)
HOOK_NAMES = (*LIFECYCLE_HOOKS, "mode-guard")
STATE_DIR = Path(".github") / "hooks" / "_state"


@pytest.fixture
def hooks(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(HOOK_DIR))
    return importlib.import_module("mdpaper_hooks")


@pytest.fixture
def dispatch() -> ModuleType:
    spec = importlib.util.spec_from_file_location("hook_dispatch", HOOK_DIR / "hook_dispatch.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_workspace(root: Path, mode: str | None = "development", state: dict | None = None) -> Path:
    if mode is not None:
        write_json(root / ".copilot-mode.json", {"mode": mode})
    if state is not None:
        write_json(root / ".mdpaper-state.json", state)
    return root


def make_project(root: Path, slug: str, workflow: str | None, *, current: bool = True) -> None:
    if workflow is not None:
        write_json(root / "projects" / slug / "project.json", {"workflow_mode": workflow})
    else:
        (root / "projects" / slug).mkdir(parents=True, exist_ok=True)
    if current:
        (root / ".current_project").write_text(slug + "\n", encoding="utf-8")


def run(hooks: ModuleType, name: str, payload: Any, root: Path) -> dict | None:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return hooks.run_hook(name, raw, root)


def context_of(result: dict | None) -> str:
    assert result is not None
    return result["hookSpecificOutput"]["additionalContext"]


def decision_of(result: dict | None) -> str:
    assert result is not None
    return result["hookSpecificOutput"]["permissionDecision"]


def audit_events(root: Path) -> list[dict]:
    path = root / STATE_DIR / "session_audit.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


# ── pre-tool-guard ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("mode", ["normal", "research"])
@pytest.mark.parametrize(
    "path",
    [
        "src/med_paper_assistant/x.py",
        "tests/test_a.py",
        ".github/hooks/a.json",
        ".claude/skills/x/SKILL.md",
        "integrations/foo/bar.py",
        "AGENTS.md",
        "CONSTITUTION.md",
        "ARCHITECTURE.md",
        "pyproject.toml",
        "src\\med_paper_assistant\\x.py",
    ],
)
def test_protected_file_edit_is_denied_in_normal_and_research(
    hooks: ModuleType, tmp_path: Path, mode: str, path: str
) -> None:
    make_workspace(tmp_path, mode)
    payload = {"tool_name": "editFiles", "tool_input": {"filePath": path}}
    result = run(hooks, "pre-tool-guard", payload, tmp_path)
    assert decision_of(result) == "deny"
    assert result is not None and "continue" not in result
    reason = result["hookSpecificOutput"]["permissionDecisionReason"]
    assert reason == (
        f"PROTECTED PATH in {mode} mode: '{path}' is read-only. Switch to development mode first."
    )


@pytest.mark.parametrize("tool", ["create_file", "replace_string_in_file", "multi_replace_x"])
def test_protected_edit_tools_use_path_and_file_keys(
    hooks: ModuleType, tmp_path: Path, tool: str
) -> None:
    make_workspace(tmp_path, "normal")
    for key in ("path", "file"):
        payload = {"tool_name": tool, "tool_input": {key: "src/x.py"}}
        assert decision_of(run(hooks, "pre-tool-guard", payload, tmp_path)) == "deny"


def test_protected_file_edit_is_allowed_in_development(hooks: ModuleType, tmp_path: Path) -> None:
    make_workspace(tmp_path, "development")
    payload = {"tool_name": "editFiles", "tool_input": {"filePath": "src/x.py"}}
    assert run(hooks, "pre-tool-guard", payload, tmp_path) is None


def test_project_files_are_not_protected_in_normal_mode(hooks: ModuleType, tmp_path: Path) -> None:
    make_workspace(tmp_path, "normal")
    payload = {"tool_name": "create_file", "tool_input": {"filePath": "projects/p/concept.md"}}
    assert run(hooks, "pre-tool-guard", payload, tmp_path) is None


def test_copilot_cli_payload_aliases_are_understood(hooks: ModuleType, tmp_path: Path) -> None:
    make_workspace(tmp_path, "normal")
    payload = {"toolName": "editFiles", "toolArgs": json.dumps({"filePath": "src/x.py"})}
    assert decision_of(run(hooks, "pre-tool-guard", payload, tmp_path)) == "deny"


def test_workspace_mode_file_overrides_session_context(hooks: ModuleType, tmp_path: Path) -> None:
    write_json(tmp_path / STATE_DIR / "session_context.json", {"mode": "normal"})
    payload = {"tool_name": "editFiles", "tool_input": {"filePath": "src/x.py"}}
    assert decision_of(run(hooks, "pre-tool-guard", payload, tmp_path)) == "deny"
    make_workspace(tmp_path, "development")
    assert run(hooks, "pre-tool-guard", payload, tmp_path) is None


def test_missing_mode_defaults_to_normal(hooks: ModuleType, tmp_path: Path) -> None:
    payload = {"tool_name": "editFiles", "tool_input": {"filePath": "AGENTS.md"}}
    assert decision_of(run(hooks, "pre-tool-guard", payload, tmp_path)) == "deny"


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf /",
        "psql -c 'DROP TABLE users'",
        "mysql -e 'DROP DATABASE x'",
        "git commit --no-verify -m x",
        "git push --force origin main",
        "git --force push",
    ],
)
def test_destructive_terminal_command_is_intercepted(
    hooks: ModuleType, tmp_path: Path, command: str
) -> None:
    make_workspace(tmp_path, "development")
    payload = {"tool_name": "run_in_terminal", "tool_input": {"command": command}}
    result = run(hooks, "pre-tool-guard", payload, tmp_path)
    assert decision_of(result) == "deny"
    assert result is not None
    assert result["hookSpecificOutput"]["permissionDecisionReason"] == (
        f"DESTRUCTIVE COMMAND BLOCKED: '{command}'. This operation is potentially dangerous "
        "and requires explicit user approval."
    )


@pytest.mark.parametrize("command", ["rm -rf ./build", "drop table x", "git status", "ls"])
def test_harmless_or_case_different_commands_are_not_blocked(
    hooks: ModuleType, tmp_path: Path, command: str
) -> None:
    make_workspace(tmp_path, "development")
    payload = {"tool_name": "run_in_terminal", "tool_input": {"command": command}}
    assert run(hooks, "pre-tool-guard", payload, tmp_path) is None


def test_non_terminal_tool_command_field_is_ignored(hooks: ModuleType, tmp_path: Path) -> None:
    payload = {"tool_name": "read_file", "tool_input": {"command": "rm -rf /"}}
    assert run(hooks, "pre-tool-guard", payload, tmp_path) is None


@pytest.mark.parametrize(
    "command", ["git push origin main", "git reset --hard HEAD~1", "git tag v1.2.3"]
)
def test_git_operations_ask_for_confirmation(
    hooks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    guard = importlib.import_module("mdpaper_hooks.pre_tool_guard")
    monkeypatch.setattr(guard, "recent_cross_platform_changes", lambda _root: [])
    payload = {"tool_name": "run_in_terminal", "tool_input": {"command": command}}
    result = run(hooks, "pre-tool-guard", payload, tmp_path)
    assert decision_of(result) == "ask"
    assert result is not None
    assert result["hookSpecificOutput"]["permissionDecisionReason"] == (
        f"GIT OPERATION requires confirmation: '{command}'"
    )
    assert "additionalContext" not in result["hookSpecificOutput"]


def test_git_push_after_cross_platform_changes_lists_files(
    hooks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    guard = importlib.import_module("mdpaper_hooks.pre_tool_guard")
    changed = [".github/workflows/ci.yml", "scripts/setup.ps1"]
    monkeypatch.setattr(guard, "recent_cross_platform_changes", lambda _root: changed)
    payload = {"tool_name": "run_in_terminal", "tool_input": {"command": "git push"}}
    result = run(hooks, "pre-tool-guard", payload, tmp_path)
    assert decision_of(result) == "ask"
    assert result is not None
    specific = result["hookSpecificOutput"]
    assert specific["permissionDecisionReason"].startswith("RELEASE/PUSH CHECK:")
    assert specific["additionalContext"] == (
        "Changed files requiring smoke evidence:\n.github/workflows/ci.yml\nscripts/setup.ps1"
    )


def test_cross_platform_changes_are_the_sorted_filtered_union(
    hooks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    guard = importlib.import_module("mdpaper_hooks.pre_tool_guard")
    answers = {
        ("diff", "--name-only", "--cached"): ["scripts/setup.sh", "README.md"],
        ("diff", "--name-only"): ["vscode-extension/package.json", "scripts/setup.sh"],
        ("diff", "--name-only", "HEAD~1..HEAD"): ["docs/a.md"],
    }
    monkeypatch.setattr(guard, "_git_names", lambda _root, args, _timeout: answers[args])
    assert guard.recent_cross_platform_changes(tmp_path) == [
        "scripts/setup.sh",
        "vscode-extension/package.json",
    ]


def test_missing_git_is_treated_as_no_changes(
    hooks: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    guard = importlib.import_module("mdpaper_hooks.pre_tool_guard")

    def no_git(*_args: Any, **_kwargs: Any) -> None:
        raise FileNotFoundError("git")

    monkeypatch.setattr(guard.subprocess, "run", no_git)
    assert guard.recent_cross_platform_changes(tmp_path) == []


def test_legacy_save_reference_asks_but_save_reference_mcp_does_not(
    hooks: ModuleType, tmp_path: Path
) -> None:
    result = run(hooks, "pre-tool-guard", {"tool_name": "mcp_mdpaper_save_reference"}, tmp_path)
    assert decision_of(result) == "ask"
    assert result is not None
    assert result["hookSpecificOutput"]["permissionDecisionReason"].startswith(
        "CONSTITUTION RULE: Use save_reference_mcp(pmid) instead of save_reference()."
    )
    assert "preventing metadata corruption" in result["hookSpecificOutput"]["additionalContext"]
    assert (
        run(hooks, "pre-tool-guard", {"tool_name": "mcp_mdpaper_save_reference_mcp"}, tmp_path)
        is None
    )


def test_allowed_tool_is_audited_without_output(hooks: ModuleType, tmp_path: Path) -> None:
    make_workspace(tmp_path, "development")
    assert run(hooks, "pre-tool-guard", {"tool_name": "read_file"}, tmp_path) is None
    events = audit_events(tmp_path)
    assert [(e["event"], e["tool"]) for e in events] == [("pre_tool_use", "read_file")]
    assert run(hooks, "pre-tool-guard", {}, tmp_path) is None
    assert len(audit_events(tmp_path)) == 1


# ── post-tool-check ────────────────────────────────────────────────────────


def test_draft_tool_requires_writing_hooks(hooks: ModuleType, tmp_path: Path) -> None:
    result = run(hooks, "post-tool-check", {"tool_name": "mcp_mdpaper_patch_draft"}, tmp_path)
    assert result is not None
    assert result["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert context_of(result) == (
        "[WRITING HOOKS REQUIRED] Draft modified via mcp_mdpaper_patch_draft. You MUST run "
        "run_writing_hooks(hooks='post-write') to check A1-A6 + A3b before proceeding. "
        "This is Code-Enforced and cannot be skipped."
    )


def test_library_wiki_project_softens_draft_reminders(hooks: ModuleType, tmp_path: Path) -> None:
    make_project(tmp_path, "lib", "library-wiki")
    result = run(hooks, "post-tool-check", {"tool_name": "mcp_mdpaper_write_draft"}, tmp_path)
    assert context_of(result).startswith("[LIBRARY-WIKI NOTE] Draft tool used")
    payload = {"tool_name": "create_file", "tool_input": {"filePath": "projects/lib/drafts/a.md"}}
    assert context_of(run(hooks, "post-tool-check", payload, tmp_path)).startswith(
        "[LIBRARY-WIKI NOTE] Draft-area note 'projects/lib/drafts/a.md'"
    )
    payload = {"tool_name": "create_file", "tool_input": {"filePath": "projects/lib/concept.md"}}
    assert context_of(run(hooks, "post-tool-check", payload, tmp_path)).startswith(
        "[LIBRARY WORKSPACE UPDATED]"
    )
    assert context_of(
        run(hooks, "post-tool-check", {"tool_name": "mcp_mdpaper_save_reference_mcp"}, tmp_path)
    ).startswith("[REFERENCE SAVED] Reference saved into a library-wiki project.")
    assert context_of(
        run(hooks, "post-tool-check", {"tool_name": "mcp_mdpaper_validate_concept"}, tmp_path)
    ).startswith("[MANUSCRIPT CHECK IN LIBRARY MODE]")


@pytest.mark.parametrize(
    "path,prefix",
    [
        ("projects/p/drafts/intro.md", "[WRITING HOOKS REQUIRED] Draft file 'projects/p/drafts/"),
        ("projects/p/concept.md", "[CONCEPT CHANGED] concept.md was modified."),
        ("projects/p/.project.yaml", "[PROJECT CONFIG CHANGED]"),
        (".copilot-mode.json", "[STATE FILE CHANGED]"),
        (".mdpaper-state.json", "[STATE FILE CHANGED]"),
        (".github/workflows/ci.yml", "[CROSS-PLATFORM SMOKE ADVISED] You changed installation"),
        ("scripts/setup.ps1", "[CROSS-PLATFORM SMOKE ADVISED]"),
        ("vscode-extension/src/a.ts", "[CROSS-PLATFORM SMOKE ADVISED]"),
    ],
)
def test_direct_file_edits_get_targeted_reminders(
    hooks: ModuleType, tmp_path: Path, path: str, prefix: str
) -> None:
    payload = {"tool_name": "editFiles", "tool_input": {"filePath": path}}
    assert context_of(run(hooks, "post-tool-check", payload, tmp_path)).startswith(prefix)


def test_windows_style_edit_paths_match_patterns(hooks: ModuleType, tmp_path: Path) -> None:
    path = ".github\\workflows\\ci.yml"
    payload = {"tool_name": "replace_string_in_file", "tool_input": {"path": path}}
    context = context_of(run(hooks, "post-tool-check", payload, tmp_path))
    assert f"at '{path}'" in context


def test_unmatched_edit_has_no_reminder_but_is_audited(hooks: ModuleType, tmp_path: Path) -> None:
    payload = {"tool_name": "editFiles", "tool_input": {"filePath": "notes/todo.txt"}}
    assert run(hooks, "post-tool-check", payload, tmp_path) is None
    assert audit_events(tmp_path)[0]["event"] == "post_tool_use"


PATCH_SRC = (
    "*** Begin Patch\n"
    "*** Update File: scripts/setup.sh\n@@\n-a\n+b\n"
    "*** Add File: docs/new.md\n+x\n"
    "*** End Patch"
)
PATCH_DOCS = "*** Begin Patch\n*** Update File: docs/a.md\n@@\n-a\n+b\n*** End Patch"


def test_apply_patch_paths_are_parsed(hooks: ModuleType) -> None:
    post = importlib.import_module("mdpaper_hooks.post_tool_check")
    patch = PATCH_SRC + "\n*** Delete File: old/file name.txt"
    assert post.patch_paths({"input": patch}) == [
        "scripts/setup.sh",
        "docs/new.md",
        "old/file",
    ]
    assert post.patch_paths({}) == []


def test_apply_patch_cross_platform_files_trigger_smoke_advice(
    hooks: ModuleType, tmp_path: Path
) -> None:
    payload = {"tool_name": "apply_patch", "tool_input": {"input": PATCH_SRC}}
    assert context_of(run(hooks, "post-tool-check", payload, tmp_path)) == (
        "[CROSS-PLATFORM SMOKE ADVISED] You modified installation, workflow, extension, or "
        "path-resolution files via apply_patch. Before wrapping up, run focused smoke tests or "
        "confirm the GitHub Actions cross-platform smoke matrix covers this change."
    )
    payload = {"tool_name": "apply_patch", "tool_input": {"input": PATCH_DOCS}}
    assert run(hooks, "post-tool-check", payload, tmp_path) is None


def test_citation_commit_and_validation_reminders(hooks: ModuleType, tmp_path: Path) -> None:
    cases = [
        ({"tool_name": "mcp_mdpaper_insert_citation"}, "[CITATION ADDED]"),
        ({"tool_name": "mcp_mdpaper_save_reference_mcp"}, "[REFERENCE SAVED] Reference saved."),
        (
            {"tool_name": "run_in_terminal", "tool_input": {"command": "git  commit -m x"}},
            "[POST-COMMIT] Git commit detected.",
        ),
        ({"tool_name": "mcp_mdpaper_validate_concept"}, "[CONCEPT VALIDATED]"),
    ]
    for payload, prefix in cases:
        assert context_of(run(hooks, "post-tool-check", payload, tmp_path)).startswith(prefix)
    terminal = {"tool_name": "run_in_terminal", "tool_input": {"command": "git status"}}
    assert run(hooks, "post-tool-check", terminal, tmp_path) is None


# ── prompt-analyzer ────────────────────────────────────────────────────────

DEV_SWITCH = "MODE SWITCH DETECTED: User wants development mode. Check .copilot-mode.json."
NORMAL_SWITCH = "MODE SWITCH DETECTED: User wants normal/research mode. Check .copilot-mode.json."


@pytest.mark.parametrize(
    "prompt,expected",
    [
        ("請切換到開發模式", DEV_SWITCH),
        ("switch to Dev Mode please", DEV_SWITCH),
        ("use normal mode now", NORMAL_SWITCH),
        ("進入研究模式", NORMAL_SWITCH),
        ("我做完了，幫我 commit", "COMMIT INTENT: Load git-precommit SKILL.md."),
        ("整理我的文獻庫", "LIBRARY-WIKI INTENT: Prefer workflow_mode=library-wiki."),
        ("show the reading queue", "LIBRARY-WIKI INTENT:"),
        ("幫我寫 Introduction", "WRITING INTENT: Remember to validate_concept() before drafting"),
        ("全自動寫論文", "AUTOPILOT INTENT: Load auto-paper SKILL.md. Follow 11-phase pipeline."),
        ("我要離開了，存檔", "CHECKPOINT INTENT: Load memory-checkpoint SKILL.md."),
    ],
)
def test_prompt_intents_are_detected(
    hooks: ModuleType, tmp_path: Path, prompt: str, expected: str
) -> None:
    result = run(hooks, "prompt-analyzer", {"prompt": prompt}, tmp_path)
    assert result is not None
    assert result["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert expected in context_of(result)


def test_prompt_without_intent_or_workflow_has_no_output(hooks: ModuleType, tmp_path: Path) -> None:
    assert run(hooks, "prompt-analyzer", {"prompt": "hello there"}, tmp_path) is None
    assert run(hooks, "prompt-analyzer", {}, tmp_path) is None
    assert run(hooks, "prompt-analyzer", "not json", tmp_path) is None


def test_prompt_user_message_alias_and_ordering(hooks: ModuleType, tmp_path: Path) -> None:
    make_project(tmp_path, "paper", "manuscript")
    result = run(hooks, "prompt-analyzer", {"userMessage": "commit and write the draft"}, tmp_path)
    lines = context_of(result).splitlines()
    assert lines[0] == "ACTIVE WORKFLOW MODE: manuscript"
    assert lines[1].startswith("COMMIT INTENT:")
    assert lines[2].startswith("WRITING INTENT:")


def test_library_wiki_project_changes_writing_and_autopilot_guidance(
    hooks: ModuleType, tmp_path: Path
) -> None:
    make_project(tmp_path, "lib", "library-wiki")
    writing = context_of(run(hooks, "prompt-analyzer", {"prompt": "write section"}, tmp_path))
    assert "WRITING INTENT IN LIBRARY-WIKI PROJECT: Confirm whether to switch" in writing
    auto = context_of(run(hooks, "prompt-analyzer", {"prompt": "autopilot"}, tmp_path))
    assert "AUTOPILOT NOTE: The 11-phase auto-paper pipeline is manuscript-only." in auto


def test_library_intent_prompt_downgrades_autopilot_in_manuscript_project(
    hooks: ModuleType, tmp_path: Path
) -> None:
    make_project(tmp_path, "paper", "manuscript")
    result = run(hooks, "prompt-analyzer", {"prompt": "autopilot 整理文獻庫"}, tmp_path)
    context = context_of(result)
    assert "LIBRARY-WIKI INTENT:" in context
    assert "AUTOPILOT NOTE:" in context
    assert "AUTOPILOT INTENT:" not in context


# ── session-init ───────────────────────────────────────────────────────────

PENDING_COLUMN_ZERO = """items:
- id: PE-0001
  status: pending
- id: PE-0002
  status: applied
- id: PE-0003
  status: dismissed
- id: PE-0004
  title: no status means pending
"""
PENDING_INDENTED = """items:
  - id: PE-1
    status: "pending"
    detail:
      - id: nested
  - id: PE-2
    status: applied
"""


@pytest.mark.parametrize(
    "content,expected", [(PENDING_COLUMN_ZERO, 2), (PENDING_INDENTED, 1), ("items: []\n", 0)]
)
def test_pending_evolutions_are_counted_by_status(
    hooks: ModuleType, tmp_path: Path, content: str, expected: int
) -> None:
    workspace = importlib.import_module("mdpaper_hooks.workspace")
    assert workspace.count_pending_evolutions(tmp_path) == 0
    (tmp_path / ".audit").mkdir()
    (tmp_path / ".audit" / "pending-evolutions.yaml").write_text(content, encoding="utf-8")
    assert workspace.count_pending_evolutions(tmp_path) == expected


def test_session_init_loads_recovery_pending_and_project_context(
    hooks: ModuleType, tmp_path: Path
) -> None:
    state = {
        "doing": "Writing intro",
        "next_action": "Run hooks",
        "active_project": "proj-a",
        "writing_session": {"section": "Introduction"},
    }
    make_workspace(tmp_path, "normal", state)
    make_project(tmp_path, "proj-a", "library-wiki", current=False)
    (tmp_path / "projects" / "temp-scratch").mkdir()
    (tmp_path / ".audit").mkdir()
    (tmp_path / ".audit" / "pending-evolutions.yaml").write_text(
        PENDING_COLUMN_ZERO, encoding="utf-8"
    )

    result = run(hooks, "session-init", {}, tmp_path)

    assert result is not None
    assert result["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert context_of(result).splitlines() == [
        "MODE: normal",
        "Research skills only. Protected paths: .claude/ .github/ src/ tests/ "
        "AGENTS.md CONSTITUTION.md pyproject.toml",
        "RECOVERY: Was doing 'Writing intro'",
        "NEXT ACTION: Run hooks",
        "ACTIVE PROJECT: proj-a",
        "WRITING SESSION: section=Introduction (call get_workspace_state() for details)",
        "PENDING EVOLUTIONS: 2 items (call get_workspace_state() for details)",
        "PROJECTS: 1 active",
        "WORKFLOW MODE: library-wiki",
    ]
    session = json.loads((tmp_path / STATE_DIR / "session_context.json").read_text("utf-8"))
    assert session["mode"] == "normal"
    assert session["active_project"] == "proj-a"
    assert session["workflow_mode"] == "library-wiki"
    assert session["started_at"].endswith("Z")
    assert [(e["event"], e["mode"]) for e in audit_events(tmp_path)] == [
        ("session_start", "normal")
    ]


def test_session_init_development_mode_and_current_project_fallback(
    hooks: ModuleType, tmp_path: Path
) -> None:
    make_workspace(tmp_path, "development", {"doing": None, "next_action": "null"})
    make_project(tmp_path, "paper", "manuscript")
    assert context_of(run(hooks, "session-init", {}, tmp_path)).splitlines() == [
        "MODE: development",
        "All skills enabled. Static analysis ON.",
        "PROJECTS: 1 active",
        "WORKFLOW MODE: manuscript",
    ]
    assert (
        json.loads((tmp_path / STATE_DIR / "session_context.json").read_text("utf-8"))[
            "active_project"
        ]
        == "paper"
    )


def test_session_init_invalid_project_json_defaults_to_manuscript(
    hooks: ModuleType, tmp_path: Path
) -> None:
    make_workspace(tmp_path, None, {"active_project": "broken"})
    (tmp_path / "projects" / "broken").mkdir(parents=True)
    (tmp_path / "projects" / "broken" / "project.json").write_text("{oops", encoding="utf-8")
    assert "WORKFLOW MODE: manuscript" in context_of(run(hooks, "session-init", {}, tmp_path))


def test_session_init_with_nothing_to_report_is_silent_and_clears_context(
    hooks: ModuleType, tmp_path: Path
) -> None:
    write_json(tmp_path / STATE_DIR / "session_context.json", {"mode": "normal"})
    assert run(hooks, "session-init", {}, tmp_path) is None
    assert not (tmp_path / STATE_DIR / "session_context.json").exists()


def test_session_init_ignores_unsafe_project_names(hooks: ModuleType, tmp_path: Path) -> None:
    make_workspace(tmp_path, "development", {"active_project": "../escape"})
    write_json(tmp_path / "escape" / "project.json", {"workflow_mode": "library-wiki"})
    assert "WORKFLOW MODE" not in context_of(run(hooks, "session-init", {}, tmp_path))


# ── pre-compact-save / subagent-init / session-stop ────────────────────────


def seed_audit(root: Path, lines: int) -> None:
    path = root / STATE_DIR / "session_audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"event": "x"}\n' * lines, encoding="utf-8")


def test_pre_compact_checkpoint_lists_state_and_tool_count(
    hooks: ModuleType, tmp_path: Path
) -> None:
    make_workspace(
        tmp_path,
        "research",
        {
            "doing": "Methods",
            "next_action": "Results",
            "active_project": "p1",
            "writing_session": {"section": "Methods"},
        },
    )
    seed_audit(tmp_path, 3)
    result = run(hooks, "pre-compact-save", {}, tmp_path)
    assert result is not None
    assert result["hookSpecificOutput"]["hookEventName"] == "PreCompact"
    assert context_of(result) == (
        "[PRE-COMPACT CHECKPOINT] Context is being compacted. Critical state to preserve:\n"
        "- Mode: research\n- Doing: Methods\n- Next: Results\n- Project: p1\n- Writing: Methods\n"
        "- Tool calls this session: 3\n\n"
        "ACTION REQUIRED: Before proceeding, call sync_workspace_state() and "
        "checkpoint_writing_context() if actively writing. Also call get_workspace_state() "
        "after compaction to recover full context."
    )


def test_pre_compact_without_state_defaults_to_normal(hooks: ModuleType, tmp_path: Path) -> None:
    lines = context_of(run(hooks, "pre-compact-save", {}, tmp_path)).splitlines()
    assert lines[1:3] == ["- Mode: normal", "- Tool calls this session: 0"]


@pytest.mark.parametrize(
    "agent,fragment",
    [
        ("literature-searcher", "Use save_reference_mcp(pmid) for saving."),
        ("paper-reviewer", "Read-only mode: Do NOT modify any draft files."),
        ("statistics-reviewer", "Read-only mode: Do NOT modify any draft files."),
        ("reference-analyzer", "Focus on extracting structured data from full text."),
        ("concept-challenger", "Be critical and constructive."),
    ],
)
def test_subagent_guidance_is_role_specific(
    hooks: ModuleType, tmp_path: Path, agent: str, fragment: str
) -> None:
    make_workspace(tmp_path, "development")
    result = run(hooks, "subagent-init", {"agentName": agent}, tmp_path)
    assert result is not None
    assert result["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
    lines = context_of(result).splitlines()
    assert lines[0] == f"[SUBAGENT CONTEXT] Agent: {agent} | Mode: development"
    assert fragment in lines[1]


def test_subagent_context_includes_project_workflow_and_restrictions(
    hooks: ModuleType, tmp_path: Path
) -> None:
    make_workspace(
        tmp_path, "normal", {"active_project": "lib", "writing_session": {"section": "X"}}
    )
    make_project(tmp_path, "lib", "library-wiki", current=False)
    context = context_of(run(hooks, "subagent-init", {"agent_type": "custom"}, tmp_path))
    assert context.splitlines() == [
        "[SUBAGENT CONTEXT] Agent: custom | Mode: normal | Project: lib | "
        "Workflow: library-wiki | Writing: X",
        "WORKFLOW NOTE: active project is library-wiki. Prioritize ingestion, organization, "
        "synthesis, and evidence traversal unless the user explicitly requests a manuscript "
        "transition.",
        "MODE RESTRICTION: normal mode — .claude/, .github/, src/, tests/ are read-only.",
    ]


def test_subagent_without_name_is_unknown(hooks: ModuleType, tmp_path: Path) -> None:
    make_workspace(tmp_path, "development")
    assert context_of(run(hooks, "subagent-init", {}, tmp_path)) == (
        "[SUBAGENT CONTEXT] Agent: unknown | Mode: development"
    )


def test_session_stop_counts_before_appending_and_cleans_up(
    hooks: ModuleType, tmp_path: Path
) -> None:
    seed_audit(tmp_path, 2)
    write_json(tmp_path / STATE_DIR / "session_context.json", {"mode": "normal"})
    result = run(hooks, "session-stop", {}, tmp_path)
    assert result is not None
    assert result["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert context_of(result).splitlines() == [
        "[SESSION ENDING] Before this session closes, ensure:",
        "1. sync_workspace_state(doing, next_action) — save current progress",
        "2. Update memory-bank/ (progress.md, activeContext.md) if significant work was done",
        "3. Update projects/{slug}/.memory/ (activeContext.md, progress.md) if working on a paper",
        "4. Total tool calls this session: 2",
    ]
    last = audit_events(tmp_path)[-1]
    assert (last["event"], last["tool_count"]) == ("session_end", 2)
    assert not (tmp_path / STATE_DIR / "session_context.json").exists()


# ── dispatcher: never raises, always exits 0 ───────────────────────────────

GARBAGE_PAYLOADS = [b"", b"not json", b"[1, 2]", b'\xef\xbb\xbf{"tool_name": "x"}', b"\xff\xfe\x00"]


@pytest.mark.parametrize("payload", GARBAGE_PAYLOADS)
@pytest.mark.parametrize("name", [*HOOK_NAMES, "session_init", "SESSION-STOP", "Pre_Tool_Guard"])
def test_dispatch_returns_json_and_exit_zero_for_any_payload(
    dispatch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
    payload: bytes,
) -> None:
    monkeypatch.setattr(dispatch, "REPO_ROOT", tmp_path)
    output, code = dispatch.dispatch(name, payload)
    assert code == 0
    assert output.endswith(b"\n")
    assert isinstance(json.loads(output), dict)


def test_hooks_without_output_answer_with_the_neutral_continue(
    dispatch: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(dispatch, "REPO_ROOT", tmp_path)
    payload = json.dumps({"prompt": "hello"}).encode("utf-8")
    assert dispatch.dispatch("prompt-analyzer", payload) == (dispatch.FAIL_OPEN, 0)
    assert dispatch.dispatch("unknown-hook", payload) == (dispatch.FAIL_OPEN, 0)
    assert dispatch.dispatch("", payload) == (dispatch.FAIL_OPEN, 0)


def test_dispatch_runs_lifecycle_hooks_in_process(
    dispatch: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(dispatch, "REPO_ROOT", tmp_path)
    make_workspace(tmp_path, "normal")
    payload = {"tool_name": "editFiles", "tool_input": {"filePath": "src/x.py"}}
    output, code = dispatch.dispatch("pre-tool-guard", json.dumps(payload).encode("utf-8"))
    assert code == 0
    assert decision_of(json.loads(output)) == "deny"
    make_workspace(tmp_path, "development")
    assert dispatch.dispatch("pre-tool-guard", json.dumps(payload).encode("utf-8")) == (
        dispatch.FAIL_OPEN,
        0,
    )


def test_dispatch_output_keeps_non_ascii_text(
    dispatch: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(dispatch, "REPO_ROOT", tmp_path)
    make_workspace(tmp_path, "development", {"doing": "撰寫引言"})
    output, _ = dispatch.dispatch("session-init", b"{}")
    assert "撰寫引言".encode() in output


@pytest.mark.parametrize("name", HOOK_NAMES)
def test_any_hook_exception_fails_open_and_is_logged(
    hooks: ModuleType,
    dispatch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError(f"{name} exploded")

    monkeypatch.setattr(dispatch, "REPO_ROOT", tmp_path)
    for hook in hooks.HOOKS:
        monkeypatch.setitem(hooks.HOOKS, hook, boom)
    monkeypatch.setattr(dispatch, "run_mode_guard", boom)
    assert dispatch.dispatch(name, b"{}") == (dispatch.FAIL_OPEN, 0)
    log_lines = (tmp_path / dispatch.ERROR_LOG).read_text(encoding="utf-8").splitlines()
    assert f"{name} exploded" in json.loads(log_lines[-1])["error"]


def test_unwritable_error_log_never_raises(
    dispatch: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("file, not a directory", encoding="utf-8")
    monkeypatch.setattr(dispatch, "REPO_ROOT", blocker)
    monkeypatch.setattr(
        dispatch, "run_lifecycle_hook", lambda *_a: (_ for _ in ()).throw(ValueError("x"))
    )
    assert dispatch.dispatch("session-init", b"{}") == (dispatch.FAIL_OPEN, 0)


def test_main_reads_stdin_writes_stdout_and_returns_zero(
    dispatch: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(dispatch, "REPO_ROOT", tmp_path)
    out = io.BytesIO()
    payload = json.dumps({"tool_name": "run_in_terminal", "tool_input": {"command": "rm -rf /"}})
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload.encode("utf-8"))))
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(out, encoding="utf-8"))
    assert dispatch.main(["hook_dispatch.py", "pre-tool-guard"]) == 0
    assert decision_of(json.loads(out.getvalue())) == "deny"


def test_main_survives_missing_std_streams(
    dispatch: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "stdin", None)
    monkeypatch.setattr(sys, "stdout", None)
    assert dispatch.main(["hook_dispatch.py"]) == 0


def test_mode_guard_dispatch_denies_protected_apply_patch(
    dispatch: ModuleType, tmp_path: Path
) -> None:
    write_json(
        tmp_path / ".copilot-mode.json",
        {"mode": "normal", "modes": {"normal": {"protected_paths": ["src/"]}}},
    )
    patch = "*** Begin Patch\n*** Update File: src/app.py\n@@\n-a\n+b\n*** End Patch"
    payload = {"cwd": str(tmp_path), "tool_name": "apply_patch", "tool_input": {"input": patch}}
    output, code = dispatch.dispatch("mode-guard", json.dumps(payload).encode("utf-8"))
    assert code == 0
    assert decision_of(json.loads(output)) == "deny"
    write_json(tmp_path / ".copilot-mode.json", {"mode": "development"})
    output, _ = dispatch.dispatch("mode-guard", json.dumps(payload).encode("utf-8"))
    assert json.loads(output) == {"continue": True}


def test_cli_process_prints_json_without_stderr_and_exits_zero() -> None:
    payload = {"tool_name": "run_in_terminal", "tool_input": {"command": "rm -rf /"}}
    completed = subprocess.run(  # noqa: S603 - repo-local dispatcher with the test interpreter
        [sys.executable, str(HOOK_DIR / "hook_dispatch.py"), "pre-tool-guard"],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stderr == b""
    assert decision_of(json.loads(completed.stdout)) == "deny"


# ── wiring and structure guards ────────────────────────────────────────────


def test_every_configured_dispatch_target_is_a_registered_hook(hooks: ModuleType) -> None:
    for config_name in ("mdpaper-lifecycle.json", "mode-guard.json"):
        config = json.loads((ROOT / ".github" / "hooks" / config_name).read_text("utf-8"))
        for entries in config["hooks"].values():
            for entry in entries:
                target = entry["powershell"].split("hook_dispatch.py ", 1)[1].split()[0]
                assert target == "mode-guard" or target in hooks.HOOKS


def test_registry_matches_shell_shim_names(hooks: ModuleType) -> None:
    assert set(hooks.HOOKS) == set(LIFECYCLE_HOOKS)
    for name in LIFECYCLE_HOOKS:
        assert (HOOK_DIR / f"{name}.sh").is_file()
    assert hooks.normalize_name("Session_Init.sh") == "session-init"


def test_hook_package_is_stdlib_only_and_small() -> None:
    stdlib = set(sys.stdlib_module_names)
    for module in sorted(PACKAGE_DIR.glob("*.py")):
        source = module.read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 400, f"{module.name} exceeds 400 lines"
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(a.name.split(".")[0] in stdlib for a in node.names), module.name
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                assert (node.module or "").split(".")[0] in stdlib, module.name
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                length = (node.end_lineno or node.lineno) - node.lineno + 1
                assert length <= 50, f"{module.name}:{node.name} is {length} lines"
