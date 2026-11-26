"""Fail-open Antigravity lifecycle hook dispatcher (stdlib only).

Bridges Antigravity camelCase protojson hook payloads (``.agents/hooks.json``)
onto the existing ``copilot_hook_guard`` and ``mdpaper_hooks`` Python modules.

Supported events (passed as ``argv[1]``):
    session-start   -> SessionStart (injectSteps)
    pre-invocation  -> PreInvocation (injectSteps on first invocation of a turn)
    pre-tool-use    -> PreToolUse (decision: allow | deny | ask, reason)
    post-tool-use   -> PostToolUse (audit trail; returns {})
    stop            -> Stop (finalize audit trail; returns {})

The dispatcher always exits 0 and fails open so a hook error never locks the
agent out of its tools. Any exception is logged to
``.github/hooks/_state/hook_errors.jsonl``.
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
COPILOT_HOOK_DIR = Path(__file__).resolve().parent / "copilot"
REPO_ROOT = SCRIPTS_DIR.parent
ERROR_LOG = Path(".github") / "hooks" / "_state" / "hook_errors.jsonl"
ERROR_LOG_MAX_BYTES = 256 * 1024

_TERMINAL_TOOLS = {"run_command", "run_in_terminal", "powershell", "bash", "shell", "terminal"}
_EDIT_TOOLS = {"edit_file", "write_file", "replace_file_content", "multi_replace_file_content"}


def _log_error(event: str, exc: BaseException) -> None:
    try:
        path = REPO_ROOT / ERROR_LOG
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > ERROR_LOG_MAX_BYTES:
            path.unlink()
        record = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hook": f"antigravity:{event}",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": "".join(traceback.format_exception(exc))[-2000:],
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - logging must never fail the hook
        pass


def _parse_json(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8-sig", errors="replace").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _resolve_workspace(payload: dict[str, Any]) -> Path:
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        candidate = Path(cwd.strip())
        if candidate.is_dir():
            return candidate.resolve()
    workspaces = payload.get("workspacePaths")
    if isinstance(workspaces, list):
        for item in workspaces:
            if isinstance(item, str) and item.strip():
                candidate = Path(item.strip())
                if candidate.is_dir():
                    return candidate.resolve()
    return REPO_ROOT


def _ensure_imports() -> None:
    for directory in (SCRIPTS_DIR, COPILOT_HOOK_DIR):
        text = str(directory)
        if text not in sys.path:
            sys.path.insert(0, text)


def _extract_tool_call(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    tool_call = payload.get("toolCall")
    if isinstance(tool_call, dict):
        name = tool_call.get("name")
        args = tool_call.get("args")
        return (
            name if isinstance(name, str) else "",
            args if isinstance(args, dict) else {},
        )
    return "", {}


def _to_copilot_tool_payload(name: str, args: dict[str, Any], workspace: Path) -> dict[str, Any]:
    lowered = name.casefold()
    mapped_name = name
    mapped_input = dict(args)

    if lowered in _TERMINAL_TOOLS:
        mapped_name = "run_in_terminal"
        command = args.get("CommandLine") or args.get("command") or ""
        mapped_input["command"] = command
    elif lowered in _EDIT_TOOLS:
        mapped_name = "editFiles"
        file_path = args.get("Path") or args.get("TargetFile") or args.get("path") or ""
        mapped_input["filePath"] = file_path
    elif lowered == "save_reference" or lowered.endswith("_save_reference"):
        mapped_name = "mcp_mdpaper_save_reference"

    return {
        "hookEventName": "PreToolUse",
        "cwd": str(workspace),
        "tool_name": mapped_name,
        "tool_input": mapped_input,
    }


def _inject_system_message(text: str) -> dict[str, Any]:
    if not text.strip():
        return {}
    return {"injectSteps": [{"systemMessage": {"systemMessage": text}}]}


def _additional_context(result: Any) -> str:
    if not isinstance(result, dict):
        return ""
    specific = result.get("hookSpecificOutput")
    if isinstance(specific, dict):
        ctx = specific.get("additionalContext")
        if isinstance(ctx, str):
            return ctx
    return ""


def _permission_decision(result: Any) -> tuple[str, str] | None:
    if not isinstance(result, dict):
        return None
    specific = result.get("hookSpecificOutput")
    if not isinstance(specific, dict):
        return None
    decision = specific.get("permissionDecision")
    if decision not in ("allow", "deny", "ask"):
        return None
    reason = specific.get("permissionDecisionReason") or ""
    extra = specific.get("additionalContext") or ""
    full_reason = f"{reason}\n{extra}".strip() if extra and extra not in reason else str(reason)
    return str(decision), full_reason


def _handle_session_start(payload: dict[str, Any], workspace: Path) -> dict[str, Any]:
    _ensure_imports()
    import mdpaper_hooks

    result = mdpaper_hooks.run_hook("session-init", json.dumps(payload), workspace)
    return _inject_system_message(_additional_context(result))


def _handle_pre_invocation(payload: dict[str, Any], workspace: Path) -> dict[str, Any]:
    invocation_num = payload.get("invocationNum", 1)
    if isinstance(invocation_num, int) and invocation_num > 1:
        return {}
    prompt = payload.get("lastUserInput") or ""
    if not isinstance(prompt, str) or not prompt.strip():
        return {}
    _ensure_imports()
    import mdpaper_hooks

    result = mdpaper_hooks.run_hook("prompt-analyzer", json.dumps({"prompt": prompt}), workspace)
    return _inject_system_message(_additional_context(result))


def _handle_pre_tool_use(payload: dict[str, Any], workspace: Path) -> dict[str, Any]:
    name, args = _extract_tool_call(payload)
    if not name:
        return {"decision": "allow"}

    _ensure_imports()
    import copilot_hook_guard
    import mdpaper_hooks

    mode, protected_paths = copilot_hook_guard.load_mode_settings(workspace)
    guard_result = copilot_hook_guard.evaluate_pre_tool_use(
        payload,
        mode=mode,
        protected_paths=protected_paths,
        workspace_root=workspace,
    )
    decision = _permission_decision(guard_result)
    if decision is not None:
        action, reason = decision
        out: dict[str, Any] = {"decision": action}
        if reason:
            out["reason"] = reason
        return out

    bridged = _to_copilot_tool_payload(name, args, workspace)
    lifecycle_result = mdpaper_hooks.run_hook("pre-tool-guard", json.dumps(bridged), workspace)
    decision = _permission_decision(lifecycle_result)
    if decision is not None:
        action, reason = decision
        out = {"decision": action}
        if reason:
            out["reason"] = reason
        return out

    return {"decision": "allow"}


def _handle_post_tool_use(payload: dict[str, Any], workspace: Path) -> dict[str, Any]:
    name, args = _extract_tool_call(payload)
    if name:
        _ensure_imports()
        import mdpaper_hooks

        bridged = _to_copilot_tool_payload(name, args, workspace)
        bridged["hookEventName"] = "PostToolUse"
        mdpaper_hooks.run_hook("post-tool-check", json.dumps(bridged), workspace)
    return {}


def _handle_stop(payload: dict[str, Any], workspace: Path) -> dict[str, Any]:
    _ensure_imports()
    import mdpaper_hooks

    mdpaper_hooks.run_hook("session-stop", json.dumps(payload), workspace)
    return {}


_HANDLERS = {
    "session-start": _handle_session_start,
    "pre-invocation": _handle_pre_invocation,
    "pre-tool-use": _handle_pre_tool_use,
    "post-tool-use": _handle_post_tool_use,
    "stop": _handle_stop,
}


def dispatch(event_name: str, raw_payload: bytes) -> tuple[bytes, int]:
    """Process one Antigravity hook invocation; always returns ``(json_bytes, 0)``."""
    event = event_name.strip().lower().replace("_", "-")
    fallback: dict[str, Any] = {"decision": "allow"} if event == "pre-tool-use" else {}
    handler = _HANDLERS.get(event)
    if handler is None:
        return (json.dumps(fallback, ensure_ascii=False) + "\n").encode("utf-8"), 0

    try:
        payload = _parse_json(raw_payload)
        workspace = _resolve_workspace(payload)
        result = handler(payload, workspace)
        if not isinstance(result, dict):
            result = fallback
        return (json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"), 0
    except Exception as exc:  # noqa: BLE001 - fail open
        _log_error(event, exc)
        return (json.dumps(fallback, ensure_ascii=False) + "\n").encode("utf-8"), 0


def main(argv: list[str]) -> int:
    try:
        stdin = sys.stdin.buffer if sys.stdin is not None else None
        payload = stdin.read() if stdin is not None else b""
        event = argv[1] if len(argv) > 1 else ""
        output, _ = dispatch(event, payload)
        if sys.stdout is not None:
            sys.stdout.buffer.write(output)
            sys.stdout.flush()
    except Exception:  # noqa: BLE001 - broken pipe must not block the agent
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
