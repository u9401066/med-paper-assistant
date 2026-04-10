from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable

DESTRUCTIVE_TERMINAL_PATTERNS = {
    "git reset --hard": "Destructive git reset requires explicit human approval.",
    "git checkout --": "Discarding local changes requires explicit human approval.",
    "remove-item -recurse -force": "Recursive forced deletion requires explicit human approval.",
    "rm -rf": "Recursive forced deletion requires explicit human approval.",
    "del /f /s /q": "Forced recursive deletion requires explicit human approval.",
}

PATCH_FILE_PATTERN = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (?P<path>.+?)\s*$")
WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")
MUTATING_TOOL_KEYWORDS = (
    "apply",
    "copy",
    "create",
    "delete",
    "edit",
    "move",
    "rename",
    "update",
)
PATH_FIELD_NAMES = {
    "path",
    "destinationpath",
    "dirpath",
    "filepath",
    "frompath",
    "newpath",
    "oldpath",
    "sourcepath",
    "targetpath",
    "topath",
}


def _rebase_foreign_absolute_path(parts: tuple[str, ...], workspace_root: Path) -> Path | None:
    normalized_parts: list[str] = []
    for part in parts:
        cleaned = part.rstrip("\\/")
        if not cleaned or cleaned in {"/", "\\"}:
            continue
        if re.fullmatch(r"[A-Za-z]:", cleaned):
            continue
        normalized_parts.append(cleaned)

    try:
        repo_index = normalized_parts.index(workspace_root.name)
    except ValueError:
        return None

    return workspace_root.joinpath(*normalized_parts[repo_index + 1 :]).resolve()


def load_mode_settings(workspace_root: Path) -> tuple[str, list[str]]:
    config_path = workspace_root / ".copilot-mode.json"
    if not config_path.exists():
        return "development", []

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "development", []

    if not isinstance(config, dict):
        return "development", []

    mode = config.get("mode", "development")
    if not isinstance(mode, str) or not mode:
        mode = "development"

    modes = config.get("modes", {})
    if not isinstance(modes, dict):
        return mode, []

    mode_settings = modes.get(mode, {})
    if not isinstance(mode_settings, dict):
        return mode, []

    protected = mode_settings.get("protected_paths", [])
    if not isinstance(protected, list):
        return mode, []

    return mode, [path for path in protected if isinstance(path, str)]


def normalize_path(path_text: str, workspace_root: Path) -> Path:
    raw_path = path_text.strip()

    if WINDOWS_ABSOLUTE_PATH_PATTERN.match(raw_path):
        rebased = _rebase_foreign_absolute_path(PureWindowsPath(raw_path).parts, workspace_root)
        if rebased is not None:
            return rebased
    elif raw_path.startswith("/"):
        rebased = _rebase_foreign_absolute_path(PurePosixPath(raw_path).parts, workspace_root)
        if rebased is not None:
            return rebased

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    return candidate.resolve()


def iter_patch_paths(patch_text: str, workspace_root: Path) -> list[Path]:
    paths: list[Path] = []
    for line in patch_text.splitlines():
        match = PATCH_FILE_PATTERN.match(line.strip())
        if not match:
            continue

        raw_path = match.group("path")
        if " -> " in raw_path:
            raw_path = raw_path.split(" -> ", 1)[0]
        paths.append(normalize_path(raw_path, workspace_root))
    return paths


def _coerce_path_texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]

    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]

    return []


def iter_explicit_tool_paths(tool_input: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    stack: list[Any] = [tool_input]

    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                normalized_key = key.replace("_", "").casefold()
                if normalized_key in PATH_FIELD_NAMES:
                    paths.extend(_coerce_path_texts(value))
                    continue

                if isinstance(value, (dict, list)):
                    stack.append(value)
            continue

        if isinstance(current, list):
            stack.extend(item for item in current if isinstance(item, (dict, list)))

    return paths


def get_tool_target_paths(payload: dict[str, Any], workspace_root: Path) -> list[Path]:
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    if tool_name == "apply_patch":
        patch_text = tool_input.get("input", "")
        return iter_patch_paths(patch_text, workspace_root)

    if tool_name == "memory":
        return []

    normalized_tool_name = tool_name.casefold()
    if not any(keyword in normalized_tool_name for keyword in MUTATING_TOOL_KEYWORDS):
        return []

    return [
        normalize_path(path_text, workspace_root)
        for path_text in iter_explicit_tool_paths(tool_input)
    ]


def is_protected_path(target_path: Path, workspace_root: Path, protected_paths: Iterable[str]) -> bool:
    try:
        relative = target_path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return False

    for protected in protected_paths:
        normalized = protected.replace("\\", "/").strip()
        if not normalized:
            continue

        if normalized.endswith("/"):
            if relative == normalized.rstrip("/") or relative.startswith(normalized):
                return True
            continue

        if relative == normalized:
            return True

    return False


def detect_dangerous_terminal_command(command: str) -> str | None:
    normalized = command.casefold()
    for pattern, reason in DESTRUCTIVE_TERMINAL_PATTERNS.items():
        if pattern in normalized:
            return reason
    return None


def build_pretool_response(
    decision: str,
    reason: str,
    *,
    additional_context: str | None = None,
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        },
    }
    if additional_context:
        output["hookSpecificOutput"]["additionalContext"] = additional_context
    return output


def evaluate_pre_tool_use(
    payload: dict[str, Any],
    *,
    mode: str,
    protected_paths: list[str],
    workspace_root: Path,
) -> dict[str, Any]:
    tool_name = payload.get("tool_name", "")

    if tool_name == "run_in_terminal":
        tool_input = payload.get("tool_input") or {}
        command = tool_input.get("command", "")
        reason = detect_dangerous_terminal_command(command)
        if reason:
            return build_pretool_response(
                "ask",
                reason,
                additional_context="Review the command carefully before approving terminal execution.",
            )

    if mode == "development":
        return {"continue": True}

    for target in get_tool_target_paths(payload, workspace_root):
        if is_protected_path(target, workspace_root, protected_paths):
            relative = target.resolve().relative_to(workspace_root.resolve()).as_posix()
            reason = (
                f"Current mode '{mode}' treats '{relative}' as protected. "
                "Switch to development mode before editing this path."
            )
            return build_pretool_response(
                "deny",
                reason,
                additional_context="Protected paths come from .copilot-mode.json runtime policy.",
            )

    return {"continue": True}


def main() -> int:
    payload = json.load(sys.stdin)
    workspace_root = Path(payload.get("cwd") or ".").resolve()
    mode, protected_paths = load_mode_settings(workspace_root)

    if payload.get("hookEventName") != "PreToolUse":
        print(json.dumps({"continue": True}))
        return 0

    result = evaluate_pre_tool_use(
        payload,
        mode=mode,
        protected_paths=protected_paths,
        workspace_root=workspace_root,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
