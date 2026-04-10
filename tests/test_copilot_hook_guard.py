from __future__ import annotations

import importlib.util
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = WORKSPACE_ROOT / "scripts" / "copilot_hook_guard.py"


def _load_hook_guard_module():
    spec = importlib.util.spec_from_file_location("copilot_hook_guard", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load copilot_hook_guard.py")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HOOK_GUARD = _load_hook_guard_module()
evaluate_pre_tool_use = HOOK_GUARD.evaluate_pre_tool_use
get_tool_target_paths = HOOK_GUARD.get_tool_target_paths
is_protected_path = HOOK_GUARD.is_protected_path
iter_patch_paths = HOOK_GUARD.iter_patch_paths
load_mode_settings = HOOK_GUARD.load_mode_settings
normalize_path = HOOK_GUARD.normalize_path


PROTECTED_PATHS = [
    ".claude/",
    ".github/",
    "src/",
    "tests/",
    "integrations/",
    "AGENTS.md",
    "CONSTITUTION.md",
    "ARCHITECTURE.md",
    "pyproject.toml",
]


def test_iter_patch_paths_extracts_target_files() -> None:
    patch_text = """*** Begin Patch
*** Update File: d:\\workspace260223\\med-paper-assistant\\src\\med_paper_assistant\\interfaces\\mcp\\server.py
*** Add File: d:\\workspace260223\\med-paper-assistant\\tests\\test_mcp_integration.py
*** End Patch"""

    paths = iter_patch_paths(patch_text, WORKSPACE_ROOT)

    assert len(paths) == 2
    assert paths[0].name == "server.py"
    assert paths[1].name == "test_mcp_integration.py"


def test_iter_patch_paths_extracts_posix_target_files() -> None:
    patch_text = f"""*** Begin Patch
*** Update File: {WORKSPACE_ROOT.as_posix()}/src/med_paper_assistant/interfaces/mcp/server.py
*** Add File: {WORKSPACE_ROOT.as_posix()}/tests/test_mcp_integration.py
*** End Patch"""

    paths = iter_patch_paths(patch_text, WORKSPACE_ROOT)

    assert len(paths) == 2
    assert paths[0].name == "server.py"
    assert paths[1].name == "test_mcp_integration.py"


def test_iter_patch_paths_handles_arrow_path_conversion() -> None:
    patch_text = f"""*** Begin Patch
*** Update File: {WORKSPACE_ROOT.as_posix()}/src/med_paper_assistant/interfaces/mcp/server.py -> bundled/tool/server.py
*** End Patch"""

    paths = iter_patch_paths(patch_text, WORKSPACE_ROOT)

    assert len(paths) == 1
    assert paths[0] == (WORKSPACE_ROOT / "src" / "med_paper_assistant" / "interfaces" / "mcp" / "server.py").resolve()


def test_iter_patch_paths_handles_duplicate_workspace_name_prefix(tmp_path: Path) -> None:
    workspace_root = tmp_path / "med-paper-assistant" / "med-paper-assistant"
    patch_text = f"""*** Begin Patch
*** Update File: {workspace_root.as_posix()}/src/med_paper_assistant/interfaces/mcp/server.py -> bundled/tool/server.py
*** End Patch"""

    paths = iter_patch_paths(patch_text, workspace_root)

    assert len(paths) == 1
    assert paths[0] == (
        workspace_root / "src" / "med_paper_assistant" / "interfaces" / "mcp" / "server.py"
    ).resolve()


def test_normal_mode_denies_protected_create_file() -> None:
    payload = {
        "tool_name": "create_file",
        "tool_input": {"filePath": str(WORKSPACE_ROOT / "src" / "new_file.py")},
    }

    result = evaluate_pre_tool_use(
        payload,
        mode="normal",
        protected_paths=PROTECTED_PATHS,
        workspace_root=WORKSPACE_ROOT,
    )

    decision = result["hookSpecificOutput"]["permissionDecision"]
    assert decision == "deny"


def test_normal_mode_denies_protected_create_file_with_duplicate_workspace_name(tmp_path: Path) -> None:
    workspace_root = tmp_path / "med-paper-assistant" / "med-paper-assistant"
    payload = {
        "tool_name": "create_file",
        "tool_input": {"filePath": str(workspace_root / "src" / "new_file.py")},
    }

    result = evaluate_pre_tool_use(
        payload,
        mode="normal",
        protected_paths=PROTECTED_PATHS,
        workspace_root=workspace_root,
    )

    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_research_mode_denies_protected_apply_patch() -> None:
    payload = {
        "tool_name": "apply_patch",
        "tool_input": {
            "input": """*** Begin Patch
*** Update File: d:\\workspace260223\\med-paper-assistant\\.github\\copilot-instructions.md
*** End Patch"""
        },
    }

    result = evaluate_pre_tool_use(
        payload,
        mode="research",
        protected_paths=PROTECTED_PATHS,
        workspace_root=WORKSPACE_ROOT,
    )

    decision = result["hookSpecificOutput"]["permissionDecision"]
    assert decision == "deny"


def test_development_mode_allows_protected_edit() -> None:
    payload = {
        "tool_name": "create_file",
        "tool_input": {"filePath": str(WORKSPACE_ROOT / "src" / "new_file.py")},
    }

    result = evaluate_pre_tool_use(
        payload,
        mode="development",
        protected_paths=PROTECTED_PATHS,
        workspace_root=WORKSPACE_ROOT,
    )

    assert result == {"continue": True}


def test_generic_mutating_tool_denies_protected_rename_path() -> None:
    payload = {
        "tool_name": "rename_file",
        "tool_input": {
            "oldPath": str(WORKSPACE_ROOT / "docs" / "draft.md"),
            "newPath": str(WORKSPACE_ROOT / "src" / "renamed.py"),
        },
    }

    result = evaluate_pre_tool_use(
        payload,
        mode="normal",
        protected_paths=PROTECTED_PATHS,
        workspace_root=WORKSPACE_ROOT,
    )

    decision = result["hookSpecificOutput"]["permissionDecision"]
    assert decision == "deny"


def test_nested_path_fields_in_dicts_and_lists_are_extracted() -> None:
    payload = {
        "tool_name": "rename_file",
        "tool_input": {
            "operations": [
                {"path": str(WORKSPACE_ROOT / "docs" / "draft.md")},
                {"nested": {"newPath": str(WORKSPACE_ROOT / "src" / "renamed.py")}},
            ]
        },
    }

    paths = get_tool_target_paths(payload, WORKSPACE_ROOT)

    assert (WORKSPACE_ROOT / "docs" / "draft.md").resolve() in paths
    assert (WORKSPACE_ROOT / "src" / "renamed.py").resolve() in paths


def test_nested_path_fields_handle_duplicate_workspace_name_prefix(tmp_path: Path) -> None:
    workspace_root = tmp_path / "med-paper-assistant" / "med-paper-assistant"
    payload = {
        "tool_name": "rename_file",
        "tool_input": {
            "operations": [
                {"path": str(workspace_root / "docs" / "draft.md")},
                {"nested": {"newPath": str(workspace_root / "src" / "renamed.py")}},
            ]
        },
    }

    paths = get_tool_target_paths(payload, workspace_root)

    assert (workspace_root / "docs" / "draft.md").resolve() in paths
    assert (workspace_root / "src" / "renamed.py").resolve() in paths


def test_read_only_tools_are_not_blocked_by_protected_paths() -> None:
    payload = {
        "tool_name": "read_file",
        "tool_input": {"filePath": str(WORKSPACE_ROOT / "src" / "new_file.py")},
    }

    result = evaluate_pre_tool_use(
        payload,
        mode="normal",
        protected_paths=PROTECTED_PATHS,
        workspace_root=WORKSPACE_ROOT,
    )

    assert result == {"continue": True}


def test_external_absolute_paths_are_not_rebased_into_workspace() -> None:
    external_path = normalize_path("D:/external/another-repo/src/file.py", WORKSPACE_ROOT)

    assert external_path != (WORKSPACE_ROOT / "src" / "file.py").resolve()
    assert is_protected_path(external_path, WORKSPACE_ROOT, PROTECTED_PATHS) is False


def test_protected_prefix_does_not_match_similar_directory_name() -> None:
    target = (WORKSPACE_ROOT / "src-other" / "file.py").resolve()

    assert is_protected_path(target, WORKSPACE_ROOT, PROTECTED_PATHS) is False


def test_destructive_terminal_command_requires_confirmation() -> None:
    payload = {
        "tool_name": "run_in_terminal",
        "tool_input": {"command": "git reset --hard HEAD"},
    }

    result = evaluate_pre_tool_use(
        payload,
        mode="development",
        protected_paths=PROTECTED_PATHS,
        workspace_root=WORKSPACE_ROOT,
    )

    decision = result["hookSpecificOutput"]["permissionDecision"]
    assert decision == "ask"


def test_load_mode_settings_defaults_when_config_is_invalid_json(tmp_path: Path) -> None:
    (tmp_path / ".copilot-mode.json").write_text("{not-json", encoding="utf-8")

    assert load_mode_settings(tmp_path) == ("development", [])


def test_load_mode_settings_handles_missing_or_invalid_mode_fields(tmp_path: Path) -> None:
    (tmp_path / ".copilot-mode.json").write_text(
        '{"mode": "normal", "modes": {"normal": {"protected_paths": "src/"}}}',
        encoding="utf-8",
    )

    assert load_mode_settings(tmp_path) == ("normal", [])
