#!/usr/bin/env python3
"""Cross-platform smoke test for Med Paper Assistant installation.

Verifies that all critical components are importable and MCP servers can
create their server objects.  Exits 0 only if every check passes.

Usage:
    uv run python scripts/smoke_test.py          # from workspace root
    python scripts/smoke_test.py                  # if already in venv
"""

from __future__ import annotations

import importlib
import os
import platform
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "scripts"))

from migrate_mcp_json import find_missing_servers, load_mcp_json  # noqa: E402

_pass = 0
_fail = 0


def ok(msg: str) -> None:
    global _pass
    _pass += 1
    print(f"  ✅ {msg}")


def fail(msg: str) -> None:
    global _fail
    _fail += 1
    print(f"  ❌ {msg}")


def section(title: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


# ── 1. Platform & Environment ──────────────────────────────────────────────


def check_environment() -> None:
    section("1. Environment")
    print(f"  OS:      {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"  Python:  {sys.version}")
    print(f"  CWD:     {Path.cwd()}")

    # uv reachable?
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            ok(f"uv: {result.stdout.strip()}")
        else:
            fail("uv returned non-zero")
    except FileNotFoundError:
        fail("uv not found in PATH")
    except subprocess.TimeoutExpired:
        fail("uv --version timed out")


# ── 2. Core Imports ────────────────────────────────────────────────────────


def check_core_imports() -> None:
    section("2. Core Python Imports")

    modules = [
        "med_paper_assistant",
        "med_paper_assistant.interfaces.mcp",
        "med_paper_assistant.interfaces.mcp.server",
        "med_paper_assistant.interfaces.mcp.tools._shared.progress",
    ]
    for modname in modules:
        try:
            importlib.import_module(modname)
            ok(modname)
        except Exception as exc:
            fail(f"{modname}: {exc}")


# ── 3. MCP Server Creation ────────────────────────────────────────────────


def check_mcp_server() -> None:
    section("3. MedPaper MCP Server")
    try:
        from med_paper_assistant.interfaces.mcp.server import create_server

        server = create_server()
        ok(f"create_server() → {type(server).__name__}")
    except Exception as exc:
        fail(f"create_server() failed: {exc}")


# ── 4. CGU Integration ────────────────────────────────────────────────────


def check_cgu() -> None:
    section("4. CGU Integration")
    cgu_dir = WORKSPACE / "integrations" / "cgu"
    if not cgu_dir.exists():
        ok("CGU submodule not present (optional)")
        return

    try:
        import cgu  # noqa: F401, F811

        ok("import cgu")
    except Exception as exc:
        fail(f"import cgu: {exc}")


# ── 5. mcp.json ───────────────────────────────────────────────────────────


def check_mcp_json() -> None:
    section("5. .vscode/mcp.json")
    mcp_path = WORKSPACE / ".vscode" / "mcp.json"
    if not mcp_path.is_file():
        fail(".vscode/mcp.json does not exist (run setup first)")
        return

    try:
        data, parse_mode = load_mcp_json(mcp_path)
    except Exception as exc:
        fail(f"Cannot parse mcp.json: {exc}")
        return

    if parse_mode == "jsonc":
        ok("mcp.json parsed via JSONC compatibility mode")

    servers = data.get("servers", {})
    expected = {"mdpaper", "pubmed-search", "cgu", "zotero-keeper", "asset-aware", "drawio"}
    present = set(servers.keys()) & expected
    missing = expected - present

    if missing:
        fail(f"Missing servers in mcp.json: {', '.join(sorted(missing))}")
    else:
        ok(f"All {len(expected)} servers defined: {', '.join(sorted(present))}")


# ── 6. Submodules ─────────────────────────────────────────────────────────


def check_submodules() -> None:
    section("6. Git Submodules")
    try:
        result = subprocess.run(
            ["git", "submodule", "status"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(WORKSPACE),
        )
        if result.returncode != 0:
            fail("git submodule status failed")
            return

        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # Prefix: ' ' = init, '-' = uninit, '+' = dirty
            prefix = line[0] if line[0] in " -+" else " "
            parts = line.lstrip(" -+").split()
            name = parts[1] if len(parts) >= 2 else parts[0]
            if prefix == "-":
                fail(f"Uninitialized submodule: {name}")
            elif prefix == "+":
                ok(f"{name} (dirty — local changes)")
            else:
                ok(name)
    except FileNotFoundError:
        fail("git not found in PATH")
    except subprocess.TimeoutExpired:
        fail("git submodule status timed out")


# ── 7. Migration Script ──────────────────────────────────────────────────


def check_migration_script() -> None:
    section("7. Migration Script (dry-run)")
    mcp_path = WORKSPACE / ".vscode" / "mcp.json"
    if not mcp_path.is_file():
        ok("No mcp.json yet — migration not applicable")
        return

    migrate_script = WORKSPACE / "scripts" / "migrate_mcp_json.py"
    if not migrate_script.is_file():
        fail("scripts/migrate_mcp_json.py not found")
        return

    try:
        data, _ = load_mcp_json(mcp_path)
        missing = find_missing_servers(data)
        if missing:
            fail(f"mcp.json needs migration — missing: {', '.join(missing)}")
        else:
            ok("mcp.json has all required servers")
    except Exception as exc:
        fail(f"Migration check error: {exc}")


# ── Summary ───────────────────────────────────────────────────────────────


def main() -> None:
    print("=" * 50)
    print("  Med Paper Assistant – Smoke Test")
    print("=" * 50)

    check_environment()
    check_core_imports()
    check_mcp_server()
    check_cgu()
    check_mcp_json()
    check_submodules()
    check_migration_script()

    print(f"\n{'=' * 50}")
    total = _pass + _fail
    if _fail == 0:
        print(f"  ALL {total} checks passed ✅")
    else:
        print(f"  {_pass}/{total} passed, {_fail} FAILED ❌")
    print(f"{'=' * 50}\n")

    sys.exit(1 if _fail else 0)


if __name__ == "__main__":
    os.chdir(WORKSPACE)
    main()
