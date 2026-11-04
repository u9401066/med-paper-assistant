"""Regression tests for the generated Agent Plugins package."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "med-paper-assistant"
BUILDER = ROOT / "scripts" / "build_agent_plugin.py"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_generated_plugin_is_up_to_date() -> None:
    result = subprocess.run(
        [sys.executable, str(BUILDER), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_plugin_manifest_matches_package_version() -> None:
    import tomllib

    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    manifest = _load(PLUGIN_DIR / "plugin.json")
    claude_manifest = _load(PLUGIN_DIR / ".claude-plugin" / "plugin.json")
    assert manifest["name"] == "med-paper-assistant"
    assert manifest["version"] == version
    assert claude_manifest["version"] == version


def test_mcp_servers_pin_published_packages() -> None:
    servers = _load(PLUGIN_DIR / "mcp.json")["mcpServers"]
    assert "mdpaper" in servers
    for name, server in servers.items():
        assert server["type"] == "stdio", name
        assert server["command"] == "uvx", name
        assert "--from" in server["args"], name
    mdpaper_args = servers["mdpaper"]["args"]
    assert any(arg.startswith("med-paper-assistant") and "==" in arg for arg in mdpaper_args)
    assert servers["mdpaper"]["env"]["MEDPAPER_TOOL_SURFACE"] == "compact"


@pytest.mark.parametrize(
    "marketplace",
    [
        ROOT / ".claude-plugin" / "marketplace.json",
        ROOT / ".agents" / "plugins" / "marketplace.json",
    ],
)
def test_marketplaces_point_at_existing_plugin(marketplace: Path) -> None:
    data = _load(marketplace)
    entries = [p for p in data["plugins"] if p["name"] == "med-paper-assistant"]
    assert len(entries) == 1
    source = entries[0]["source"]
    rel = source if isinstance(source, str) else source["path"]
    assert (ROOT / rel / "plugin.json").is_file()


def test_every_bundled_skill_has_frontmatter() -> None:
    skills = sorted((PLUGIN_DIR / "skills").glob("*/SKILL.md"))
    assert skills
    for skill in skills:
        text = skill.read_text(encoding="utf-8")
        assert text.startswith("---"), skill
        header = text.split("---", 2)[1]
        assert f"name: {skill.parent.name}" in header, skill
        assert "description:" in header, skill
