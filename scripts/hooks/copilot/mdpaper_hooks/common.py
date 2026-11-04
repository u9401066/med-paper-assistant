"""Shared helpers for the MedPaper Copilot lifecycle hooks (stdlib only).

Hooks receive the host's JSON on stdin and answer with a JSON document on
stdout. Every helper here is best-effort: a malformed payload, a missing state
file or an unwritable audit log must never raise, because a hook failure can
make the agent host deny tool calls.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

Payload = dict[str, Any]
HookResult = dict[str, Any] | None

STATE_SUBDIR = Path(".github") / "hooks" / "_state"
AUDIT_FILE = "session_audit.jsonl"
CONTEXT_FILE = "session_context.json"

# Installation, workflow, extension and path-resolution files that need smoke evidence.
CROSS_PLATFORM_RE = re.compile(
    r"(^|/)(\.github/workflows/|vscode-extension/|scripts/setup(\.ps1|\.sh)?$"
    r"|scripts/setup-integrations(\.ps1|\.sh)$|scripts/start-drawio(\.ps1|\.sh)$"
    r"|src/med_paper_assistant/infrastructure/config\.py$"
    r"|src/med_paper_assistant/infrastructure/services/template_reader\.py$"
    r"|tests/test_config_paths\.py$)"
)


@dataclass(frozen=True)
class HookContext:
    """Where a hook reads workspace state and writes its ephemeral state."""

    workspace_root: Path

    @property
    def state_dir(self) -> Path:
        return self.workspace_root / STATE_SUBDIR


def parse_payload(raw: str) -> Payload:
    """Parse the hook stdin JSON; anything that is not a JSON object becomes ``{}``."""
    try:
        data = json.loads(raw.lstrip("\ufeff")) if raw.strip() else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def alt(value: Any) -> str:
    """Mirror ``jq -r '.x // empty'``: null/false -> '', strings as-is, others as JSON."""
    if value is None or value is False:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def first_alt(*values: Any) -> str:
    """Mirror ``jq -r '.a // .b // empty'``: the first value that is not null/false."""
    for value in values:
        if value is not None and value is not False:
            return alt(value)
    return ""


def get_tool_name(payload: Payload) -> str:
    """Tool name across VS Code (``tool_name``) and Copilot CLI (``toolName``) payloads."""
    return alt(payload.get("tool_name") or payload.get("toolName"))


def get_tool_input(payload: Payload) -> Payload:
    """Tool arguments; Copilot CLI may send ``toolArgs`` as a JSON string."""
    value = payload.get("tool_input")
    if value is None:
        value = payload.get("toolArgs")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {"command": value}
    return value if isinstance(value, dict) else {}


def get_prompt(payload: Payload) -> str:
    return alt(payload.get("prompt") or payload.get("userMessage"))


def normalize_slashes(path_text: str) -> str:
    """Use ``/`` so the POSIX-style path patterns also match Windows paths."""
    return path_text.replace("\\", "/")


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_output(event: str, additional_context: str) -> Payload:
    """Hook output that only injects ``additionalContext``."""
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": additional_context}}


def build_decision(event: str, decision: str, reason: str, context: str | None = None) -> Payload:
    """PreToolUse permission output (allow/deny/ask) with an optional context hint."""
    specific: Payload = {
        "hookEventName": event,
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }
    if context:
        specific["additionalContext"] = context
    return {"hookSpecificOutput": specific}


def write_json(path: Path, data: Payload) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError:
        pass


def append_jsonl(path: Path, record: Payload) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def append_audit(ctx: HookContext, event: str, **fields: Any) -> None:
    record: Payload = {"timestamp": utc_timestamp(), "event": event, **fields}
    append_jsonl(ctx.state_dir / AUDIT_FILE, record)


def count_audit_lines(ctx: HookContext) -> int:
    """Number of audit records so far (``wc -l`` semantics: counts newlines)."""
    try:
        return (ctx.state_dir / AUDIT_FILE).read_bytes().count(b"\n")
    except OSError:
        return 0


def remove_session_context(ctx: HookContext) -> None:
    try:
        (ctx.state_dir / CONTEXT_FILE).unlink(missing_ok=True)
    except OSError:
        pass
