#!/usr/bin/env python3
"""Migrate .vscode/mcp.json to the latest server definitions.

Called by setup.sh / setup.ps1 when an existing mcp.json is detected.
Returns exit code 0 if migration happened, 1 if already up-to-date, 2 on error.

Usage:
    python scripts/migrate_mcp_json.py [--dry-run] [path/to/mcp.json]
"""

from __future__ import annotations

import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

# The lock is the cross-runtime authority for external MCP versions/commits.
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
INTEGRATION_LOCK_PATH = REPOSITORY_ROOT / "mcp-integration-lock.json"


def load_integration_lock(lock_path: Path = INTEGRATION_LOCK_PATH) -> dict:
    """Load and minimally validate the canonical MCP integration lock."""
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot load MCP integration lock {lock_path}: {exc}") from exc

    policy = lock.get("policy", {})
    integrations = lock.get("integrations", {})
    if policy.get("python_mcp_sdk_major") != 2:
        raise RuntimeError("MCP integration lock must require Python MCP SDK major 2")
    if policy.get("allow_mcp_v1_fallback") is not False:
        raise RuntimeError("MCP integration lock must fail closed on MCP SDK v1 fallbacks")
    if "zotero-keeper" not in integrations:
        raise RuntimeError("MCP integration lock is missing zotero-keeper")
    return lock


INTEGRATION_LOCK = load_integration_lock()
ZOTERO_KEEPER_LOCK = INTEGRATION_LOCK["integrations"]["zotero-keeper"]

# Canonical server definitions. External versions/commits come from the lock above.
REQUIRED_SERVERS: dict[str, dict] = {
    "mdpaper": {
        "type": "stdio",
        "command": "uv",
        "args": [
            "run",
            "--directory",
            "${workspaceFolder}",
            "python",
            "-m",
            "med_paper_assistant.interfaces.mcp",
        ],
        "env": {
            "PYTHONPATH": "${workspaceFolder}/src",
            "MEDPAPER_TOOL_SURFACE": "compact",
        },
    },
    "pubmed-search": {
        "type": "stdio",
        "command": "uv",
        "args": [
            "run",
            "--directory",
            "${workspaceFolder}/integrations/pubmed-search-mcp",
            "pubmed-search-mcp",
        ],
        "env": {"NCBI_EMAIL": "medpaper@example.com"},
    },
    "cgu": {
        "type": "stdio",
        "command": "uv",
        "args": [
            "run",
            "--directory",
            "${workspaceFolder}/integrations/cgu",
            "python",
            "-m",
            "cgu.server",
        ],
        "env": {"CGU_THINKING_ENGINE": "simple"},
    },
    "zotero-keeper": {
        "type": "stdio",
        "command": "uvx",
        "args": [
            "--python",
            "3.12",
            "--from",
            ZOTERO_KEEPER_LOCK["package_source"],
            ZOTERO_KEEPER_LOCK["entrypoint"],
        ],
    },
    "asset-aware": {
        "type": "stdio",
        "command": "uv",
        "args": [
            "run",
            "--directory",
            "${workspaceFolder}/integrations/asset-aware-mcp",
            "asset-aware-mcp",
        ],
    },
    "drawio": {
        "type": "stdio",
        "command": "uv",
        "args": [
            "run",
            "--directory",
            "${workspaceFolder}/integrations/next-ai-draw-io/mcp-server",
            "drawio-mcp-server",
        ],
    },
}

# Only these exact historical launchers are treated as repository-managed drift.
# Any other existing definition is a user override and remains untouched.
LEGACY_MANAGED_LAUNCHERS: dict[str, set[tuple[str, tuple[str, ...]]]] = {
    "pubmed-search": {("uvx", ("pubmed-search-mcp",))},
    "zotero-keeper": {("uvx", ("zotero-keeper",))},
    "drawio": {("npx", ("-y", "@drawio/mcp"))},
}


def _strip_jsonc_comments(raw: str) -> str:
    """Remove ``//`` comments while preserving content inside JSON strings."""
    lines: list[str] = []
    for line in raw.splitlines():
        in_string = False
        escaped = False
        chars: list[str] = []
        idx = 0
        while idx < len(line):
            ch = line[idx]
            if escaped:
                chars.append(ch)
                escaped = False
                idx += 1
                continue
            if ch == "\\":
                chars.append(ch)
                escaped = True
                idx += 1
                continue
            if ch == '"':
                in_string = not in_string
                chars.append(ch)
                idx += 1
                continue
            if not in_string and ch == "/" and idx + 1 < len(line) and line[idx + 1] == "/":
                break
            chars.append(ch)
            idx += 1
        lines.append("".join(chars))
    return "\n".join(lines)


def load_mcp_json(mcp_json_path: Path) -> tuple[dict, str | None]:
    """Load ``mcp.json`` allowing JSONC comments.

    Returns parsed data and an optional parse mode label:
    - ``None`` when strict JSON parsing succeeds
    - ``jsonc`` when comment stripping was required
    Raises ValueError when parsing fails even after comment stripping.
    """
    try:
        raw = mcp_json_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(str(exc)) from exc

    try:
        return json.loads(raw), None
    except json.JSONDecodeError:
        stripped = _strip_jsonc_comments(raw)
        try:
            return json.loads(stripped), "jsonc"
        except json.JSONDecodeError as exc:
            raise ValueError(str(exc)) from exc


def find_missing_servers(existing: dict) -> list[str]:
    """Return names of servers in REQUIRED_SERVERS but absent from *existing*."""
    servers = existing.get("servers", {})
    return [name for name in REQUIRED_SERVERS if name not in servers]


def find_outdated_managed_servers(existing: dict) -> list[str]:
    """Return legacy repository launchers that are safe to replace.

    Custom commands and paths are deliberately excluded so migration never
    rewrites a user-managed MCP server definition merely because it differs
    from the repository default.
    """
    servers = existing.get("servers", {})
    outdated: list[str] = []
    for name, launchers in LEGACY_MANAGED_LAUNCHERS.items():
        current = servers.get(name)
        if not isinstance(current, dict):
            continue
        signature = (str(current.get("command", "")), tuple(current.get("args", [])))
        if signature in launchers:
            outdated.append(name)
    return outdated


def _updated_managed_definition(name: str, current: dict) -> dict:
    """Replace a managed launcher while preserving user-provided environment."""
    updated = deepcopy(REQUIRED_SERVERS[name])
    current_env = current.get("env")
    if isinstance(current_env, dict):
        preserved_env = dict(current_env)
        if name == "pubmed-search" and "NCBI_EMAIL" not in preserved_env:
            legacy_email = preserved_env.pop("ENTREZ_EMAIL", None)
            if legacy_email:
                preserved_env["NCBI_EMAIL"] = legacy_email
        updated["env"] = {**updated.get("env", {}), **preserved_env}
    return updated


def migrate(
    mcp_json_path: Path,
    *,
    dry_run: bool = False,
    create_if_missing: bool = False,
) -> int:
    """Migrate mcp.json in-place, returning 0 (migrated), 1 (up-to-date), or 2 (error)."""
    existed = mcp_json_path.is_file()
    if not existed and not create_if_missing:
        print(f"  ❌ File not found: {mcp_json_path}", file=sys.stderr)
        return 2

    if existed:
        try:
            data, parse_mode = load_mcp_json(mcp_json_path)
        except ValueError as exc:
            print(f"  ❌ Cannot parse {mcp_json_path}: {exc}", file=sys.stderr)
            return 2
    else:
        data, parse_mode = {"inputs": [], "servers": {}}, None

    missing = find_missing_servers(data)
    outdated = find_outdated_managed_servers(data)
    if parse_mode == "jsonc":
        print("  🧹 JSONC comments detected — file will be normalized to strict JSON")

    if not missing and not outdated and parse_mode is None:
        print("  ✅ mcp.json is already up-to-date (all 6 SDK2 servers present)")
        return 1

    if missing:
        print(f"  🔍 Missing servers detected: {', '.join(missing)}")
    if outdated:
        print(f"  🔒 Legacy managed launchers detected: {', '.join(outdated)}")
    if not missing and not outdated:
        print("  🔍 No servers missing — normalizing existing file")

    if dry_run:
        print("  🏷️  Dry-run: would apply the SDK2 server contract.")
        return 0

    # Back up before modifying an existing file. A newly created file needs no backup.
    if existed:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = mcp_json_path.with_name(f"{mcp_json_path.name}.bak.{ts}")
        shutil.copy2(mcp_json_path, backup_path)
        print(f"  📦 Backup created: {backup_path.name}")

    # Merge missing servers (preserve user overrides for existing servers)
    if "servers" not in data:
        data["servers"] = {}
    for name in missing:
        data["servers"][name] = deepcopy(REQUIRED_SERVERS[name])
    for name in outdated:
        data["servers"][name] = _updated_managed_definition(name, data["servers"][name])

    # Ensure top-level "inputs" key exists
    data.setdefault("inputs", [])

    try:
        mcp_json_path.parent.mkdir(parents=True, exist_ok=True)
        mcp_json_path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"  ❌ Failed to write {mcp_json_path}: {exc}", file=sys.stderr)
        return 2

    changes: list[str] = []
    if missing:
        changes.append(f"added: {', '.join(missing)}")
    if outdated:
        changes.append(f"upgraded to pinned SDK2: {', '.join(outdated)}")
    if changes:
        print(f"  ✅ Migrated mcp.json — {'; '.join(changes)}")
    elif not existed:
        print("  ✅ Created mcp.json with the pinned SDK2 server contract")
    else:
        print("  ✅ Migrated mcp.json — normalized to strict JSON")
    return 0


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    create_if_missing = "--create" in sys.argv
    args = [a for a in sys.argv[1:] if a not in {"--dry-run", "--create"}]
    mcp_path = Path(args[0]) if args else Path(".vscode/mcp.json")

    rc = migrate(mcp_path, dry_run=dry_run, create_if_missing=create_if_missing)
    sys.exit(rc)


if __name__ == "__main__":
    main()
