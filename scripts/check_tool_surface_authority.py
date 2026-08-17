#!/usr/bin/env python3
"""Validate the tool-surface authority used by docs, validate scripts, and release gates."""

from __future__ import annotations

import ast
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = REPO_ROOT / "tool-surface-authority.json"
PACKAGE_JSON_PATH = REPO_ROOT / "vscode-extension" / "package.json"
BUNDLE_MANIFEST_PATH = REPO_ROOT / "vscode-extension" / "bundle-manifest.json"
INTEGRATION_LOCK_PATH = REPO_ROOT / "mcp-integration-lock.json"
ASSET_TOOL_SURFACE_PATH = (
    REPO_ROOT / "integrations" / "asset-aware-mcp" / "src" / "presentation" / "tool_surface.py"
)
DRAWIO_TOOLS_PATH = (
    REPO_ROOT
    / "integrations"
    / "next-ai-draw-io"
    / "mcp-server"
    / "src"
    / "drawio_mcp_server"
    / "tools"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repository_files(pathspec: str, fallback_glob: str) -> list[Path]:
    """Return version-controlled repository files, with an archive-safe fallback.

    Local generated or experimental files must not change release authority counts.
    ``git ls-files --cached`` also sees paths staged for the next commit, while the
    glob fallback keeps source archives (which have no ``.git`` directory) usable.
    """
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--", pathspec],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return [REPO_ROOT / line for line in result.stdout.splitlines() if line]
    return [path for path in REPO_ROOT.glob(fallback_glob) if path.is_file()]


async def _get_runtime_surface_counts() -> dict[str, dict[str, int]]:
    from med_paper_assistant.interfaces.mcp.server import create_server

    original = os.environ.get("MEDPAPER_TOOL_SURFACE")
    counts: dict[str, dict[str, int]] = {}

    try:
        for surface in ("full", "compact"):
            os.environ["MEDPAPER_TOOL_SURFACE"] = surface
            mcp = create_server()
            counts[surface] = {
                "tools": len(await mcp.list_tools()),
                "prompts": len(await mcp.list_prompts()),
                "resources": len(await mcp.list_resources()),
            }
    finally:
        if original is None:
            os.environ.pop("MEDPAPER_TOOL_SURFACE", None)
        else:
            os.environ["MEDPAPER_TOOL_SURFACE"] = original

    return counts


async def _get_external_mcp_counts() -> dict[str, int]:
    """List locally importable MCP surfaces through the SDK 2 client API."""
    import cgu.server as cgu_server
    from mcp import Client
    from pubmed_search.presentation.mcp_server import create_server as create_pubmed_server

    counts: dict[str, int] = {}
    with tempfile.TemporaryDirectory(prefix="medpaper-pubmed-authority-") as data_dir:
        pubmed = create_pubmed_server(
            email="release-authority@example.org",
            data_dir=data_dir,
            workspace_dir=data_dir,
            mode="local",
        )
        async with Client(pubmed, mode="2026-07-28") as client:
            counts["pubmed-search"] = len((await client.list_tools()).tools)
    async with Client(cgu_server.mcp, mode="2026-07-28") as client:
        counts["cgu"] = len((await client.list_tools()).tools)
    return counts


def _literal_string_set(path: Path, variable: str) -> set[str]:
    """Read a module-level literal set without importing a submodule package."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == variable for target in node.targets
        ):
            continue
        if not isinstance(node.value, ast.Set):
            break
        values = {
            item.value
            for item in node.value.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        }
        if len(values) != len(node.value.elts):
            break
        return values
    raise RuntimeError(f"{path}: {variable} must be a literal string set")


def _count_asset_aware_balanced_tools() -> int:
    compact = _literal_string_set(ASSET_TOOL_SURFACE_PATH, "COMPACT_TOOLS")
    shortcuts = _literal_string_set(ASSET_TOOL_SURFACE_PATH, "BALANCED_SHORTCUT_TOOLS")
    if compact & shortcuts:
        raise RuntimeError("Asset-Aware balanced tool sets must not overlap")
    return len(compact | shortcuts)


def _count_drawio_tools() -> int:
    count = 0
    for path in sorted(DRAWIO_TOOLS_PATH.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                if isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "tool":
                    count += 1
    return count


def get_locked_external_mcp_counts() -> dict[str, int]:
    """Load offline release-surface counts tied to immutable package revisions."""
    integrations = _load_json(INTEGRATION_LOCK_PATH)["integrations"]
    return {name: int(config["surface"]["tools"]) for name, config in integrations.items()}


def get_runtime_surface_counts() -> dict[str, dict[str, int]]:
    """Inspect both surfaces through the public MCP SDK 2 server API."""
    return asyncio.run(_get_runtime_surface_counts())


def get_external_mcp_counts() -> dict[str, int]:
    """Inspect four checked-out surfaces locally; Zotero is archive-smoke-only."""
    counts = asyncio.run(_get_external_mcp_counts())
    counts["asset-aware"] = _count_asset_aware_balanced_tools()
    counts["drawio"] = _count_drawio_tools()
    return counts


def get_repository_counts() -> dict[str, int]:
    skills = len(
        _repository_files(
            ".claude/skills/*/SKILL.md",
            ".claude/skills/*/SKILL.md",
        )
    )
    prompt_workflows = len(
        _repository_files(
            ".github/prompts/*.prompt.md",
            ".github/prompts/*.prompt.md",
        )
    )

    return {
        "skills": skills,
        "promptWorkflows": prompt_workflows,
    }


def get_bundle_counts() -> dict[str, int]:
    manifest = _load_json(BUNDLE_MANIFEST_PATH)
    package_json = _load_json(PACKAGE_JSON_PATH)

    return {
        "skills": len(manifest["skills"]),
        "promptWorkflows": len(manifest["prompts"]),
        "agents": len(manifest["agents"]),
        "templates": len(manifest["templates"]),
        "supportFiles": len(manifest["supportFiles"]),
        "chatCommands": len(manifest["chatCommands"]),
        "paletteCommands": len(manifest["paletteCommands"]),
        "packageChatCommands": len(package_json["contributes"]["chatParticipants"][0]["commands"]),
        "packagePaletteCommands": len(package_json["contributes"]["commands"]),
    }


def validate_authority() -> tuple[list[str], list[str]]:
    authority = _load_json(AUTHORITY_PATH)
    runtime = get_runtime_surface_counts()
    external_runtime = get_external_mcp_counts()
    external_locked = get_locked_external_mcp_counts()
    repo_counts = get_repository_counts()
    bundle_counts = get_bundle_counts()

    passes: list[str] = []
    errors: list[str] = []

    expected_mcp = authority["mcpServer"]
    runtime_checks = [
        ("MCP full tools", runtime["full"]["tools"], expected_mcp["fullTools"]),
        ("MCP compact tools", runtime["compact"]["tools"], expected_mcp["compactTools"]),
        ("MCP full prompts", runtime["full"]["prompts"], expected_mcp["prompts"]),
        ("MCP compact prompts", runtime["compact"]["prompts"], expected_mcp["prompts"]),
        ("MCP full resources", runtime["full"]["resources"], expected_mcp["resources"]),
        ("MCP compact resources", runtime["compact"]["resources"], expected_mcp["resources"]),
    ]
    for label, actual, expected in runtime_checks:
        if actual == expected:
            passes.append(f"{label}: {actual}")
        else:
            errors.append(f"{label}: expected {expected}, got {actual}")

    expected_external = authority["externalMcp"]
    if set(expected_external) != set(external_locked):
        errors.append(
            "External MCP authority names do not match mcp-integration-lock.json: "
            f"authority={sorted(expected_external)}, lock={sorted(external_locked)}"
        )
    for name, expected in expected_external.items():
        label = f"External MCP {name} tools"
        locked = external_locked.get(name)
        if locked != expected:
            errors.append(f"{label}: lock expects {locked}, authority expects {expected}")
            continue
        actual = external_runtime.get(name)
        if actual is None:
            passes.append(f"{label}: {locked} (immutable lock + release archive smoke)")
        elif actual == expected:
            passes.append(f"{label}: {actual} (local checkout)")
        else:
            errors.append(f"{label}: expected {expected}, got {actual}")

    expected_repo = authority["repository"]
    repo_checks = [
        ("Repository skills", repo_counts["skills"], expected_repo["skills"]),
        (
            "Repository prompt workflows",
            repo_counts["promptWorkflows"],
            expected_repo["promptWorkflows"],
        ),
    ]
    for label, actual, expected in repo_checks:
        if actual == expected:
            passes.append(f"{label}: {actual}")
        else:
            errors.append(f"{label}: expected {expected}, got {actual}")

    expected_bundle = authority["bundle"]
    bundle_checks = [
        ("Bundled skills", bundle_counts["skills"], expected_bundle["skills"]),
        (
            "Bundled prompt workflows",
            bundle_counts["promptWorkflows"],
            expected_bundle["promptWorkflows"],
        ),
        ("Bundled agents", bundle_counts["agents"], expected_bundle["agents"]),
        ("Bundled templates", bundle_counts["templates"], expected_bundle["templates"]),
        ("Bundled support files", bundle_counts["supportFiles"], expected_bundle["supportFiles"]),
        (
            "Bundle manifest chat commands",
            bundle_counts["chatCommands"],
            expected_bundle["chatCommands"],
        ),
        (
            "Bundle manifest palette commands",
            bundle_counts["paletteCommands"],
            expected_bundle["paletteCommands"],
        ),
        (
            "package.json chat commands",
            bundle_counts["packageChatCommands"],
            expected_bundle["chatCommands"],
        ),
        (
            "package.json palette commands",
            bundle_counts["packagePaletteCommands"],
            expected_bundle["paletteCommands"],
        ),
    ]
    for label, actual, expected in bundle_checks:
        if actual == expected:
            passes.append(f"{label}: {actual}")
        else:
            errors.append(f"{label}: expected {expected}, got {actual}")

    for relative_path, snippets in authority["docs"].items():
        content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        missing = [snippet for snippet in snippets if snippet not in content]
        if missing:
            errors.append(f"{relative_path}: missing authority snippet(s): {', '.join(missing)}")
        else:
            passes.append(f"Doc authority synced: {relative_path}")

    for relative_path, snippets in authority.get("forbiddenDocs", {}).items():
        content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        present = [snippet for snippet in snippets if snippet in content]
        if present:
            errors.append(f"{relative_path}: forbidden legacy snippet(s): {', '.join(present)}")
        else:
            passes.append(f"Doc legacy guard clean: {relative_path}")

    return passes, errors


def main() -> int:
    passes, errors = validate_authority()

    for item in passes:
        print(f"✅ {item}")

    for item in errors:
        print(f"❌ {item}")

    if errors:
        return 1

    print("✅ Tool-surface authority is in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
