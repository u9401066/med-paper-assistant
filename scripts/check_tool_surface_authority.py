#!/usr/bin/env python3
"""Validate the tool-surface authority used by docs, validate scripts, and release gates."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = REPO_ROOT / "tool-surface-authority.json"
PACKAGE_JSON_PATH = REPO_ROOT / "vscode-extension" / "package.json"
BUNDLE_MANIFEST_PATH = REPO_ROOT / "vscode-extension" / "bundle-manifest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_runtime_surface_counts() -> dict[str, dict[str, int]]:
    from med_paper_assistant.interfaces.mcp.server import create_server

    original = os.environ.get("MEDPAPER_TOOL_SURFACE")
    counts: dict[str, dict[str, int]] = {}

    try:
        for surface in ("full", "compact"):
            os.environ["MEDPAPER_TOOL_SURFACE"] = surface
            mcp = create_server()
            counts[surface] = {
                "tools": len(mcp._tool_manager._tools),
                "prompts": len(mcp._prompt_manager._prompts),
                "resources": len(mcp._resource_manager._resources),
            }
    finally:
        if original is None:
            os.environ.pop("MEDPAPER_TOOL_SURFACE", None)
        else:
            os.environ["MEDPAPER_TOOL_SURFACE"] = original

    return counts


def get_repository_counts() -> dict[str, int]:
    skills_dir = REPO_ROOT / ".claude" / "skills"
    prompts_dir = REPO_ROOT / ".github" / "prompts"

    skills = sum(1 for child in skills_dir.iterdir() if child.is_dir() and (child / "SKILL.md").exists())
    prompt_workflows = sum(1 for child in prompts_dir.glob("*.prompt.md") if child.is_file())

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

    expected_repo = authority["repository"]
    repo_checks = [
        ("Repository skills", repo_counts["skills"], expected_repo["skills"]),
        ("Repository prompt workflows", repo_counts["promptWorkflows"], expected_repo["promptWorkflows"]),
    ]
    for label, actual, expected in repo_checks:
        if actual == expected:
            passes.append(f"{label}: {actual}")
        else:
            errors.append(f"{label}: expected {expected}, got {actual}")

    expected_bundle = authority["bundle"]
    bundle_checks = [
        ("Bundled skills", bundle_counts["skills"], expected_bundle["skills"]),
        ("Bundled prompt workflows", bundle_counts["promptWorkflows"], expected_bundle["promptWorkflows"]),
        ("Bundled agents", bundle_counts["agents"], expected_bundle["agents"]),
        ("Bundled templates", bundle_counts["templates"], expected_bundle["templates"]),
        ("Bundled support files", bundle_counts["supportFiles"], expected_bundle["supportFiles"]),
        ("Bundle manifest chat commands", bundle_counts["chatCommands"], expected_bundle["chatCommands"]),
        ("Bundle manifest palette commands", bundle_counts["paletteCommands"], expected_bundle["paletteCommands"]),
        ("package.json chat commands", bundle_counts["packageChatCommands"], expected_bundle["chatCommands"]),
        ("package.json palette commands", bundle_counts["packagePaletteCommands"], expected_bundle["paletteCommands"]),
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