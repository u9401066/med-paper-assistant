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
from datetime import datetime, timezone
from pathlib import Path

# Canonical server definitions — single source of truth
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
        "command": "uvx",
        "args": ["pubmed-search-mcp"],
        "env": {"ENTREZ_EMAIL": "medpaper@example.com"},
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
        "args": ["zotero-keeper"],
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
        "command": "npx",
        "args": ["-y", "@drawio/mcp"],
    },
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


def migrate(mcp_json_path: Path, *, dry_run: bool = False) -> int:
    """Migrate mcp.json in-place, returning 0 (migrated), 1 (up-to-date), or 2 (error)."""
    if not mcp_json_path.is_file():
        print(f"  ❌ File not found: {mcp_json_path}", file=sys.stderr)
        return 2

    try:
        data, parse_mode = load_mcp_json(mcp_json_path)
    except ValueError as exc:
        print(f"  ❌ Cannot parse {mcp_json_path}: {exc}", file=sys.stderr)
        return 2

    missing = find_missing_servers(data)
    if parse_mode == "jsonc":
        print("  🧹 JSONC comments detected — file will be normalized to strict JSON")

    if not missing and parse_mode is None:
        print("  ✅ mcp.json is already up-to-date (all 6 servers present)")
        return 1

    if missing:
        print(f"  🔍 Missing servers detected: {', '.join(missing)}")
    else:
        print("  🔍 No servers missing — normalizing existing file")

    if dry_run:
        print("  🏷️  Dry-run: would add the missing servers and create a backup.")
        return 0

    # Back up before modifying
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = mcp_json_path.with_name(f"{mcp_json_path.name}.bak.{ts}")
    shutil.copy2(mcp_json_path, backup_path)
    print(f"  📦 Backup created: {backup_path.name}")

    # Merge missing servers (preserve user overrides for existing servers)
    if "servers" not in data:
        data["servers"] = {}
    for name in missing:
        data["servers"][name] = REQUIRED_SERVERS[name]

    # Ensure top-level "inputs" key exists
    data.setdefault("inputs", [])

    try:
        mcp_json_path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"  ❌ Failed to write {mcp_json_path}: {exc}", file=sys.stderr)
        return 2

    if missing:
        added = ", ".join(missing)
        print(f"  ✅ Migrated mcp.json — added: {added}")
    else:
        print("  ✅ Migrated mcp.json — normalized to strict JSON")
    return 0


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    mcp_path = Path(args[0]) if args else Path(".vscode/mcp.json")

    rc = migrate(mcp_path, dry_run=dry_run)
    sys.exit(rc)


if __name__ == "__main__":
    main()
