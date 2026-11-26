"""Regression tests for the generated Agent Plugins package."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "med-paper-assistant"
BUILDER = ROOT / "scripts" / "build_agent_plugin.py"
ANTIGRAVITY_RULE_BYTE_LIMIT = 24_000
ANTIGRAVITY_ALLOWED_MCP_KEYS = {
    "command",
    "args",
    "env",
    "cwd",
    "url",
    "headers",
    "disabled",
    "variables",
}


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


def test_antigravity_mcp_config_and_workspace_discovery_manifests() -> None:
    ag_mcp = _load(PLUGIN_DIR / "mcp_config.json")
    assert "$schema" not in ag_mcp
    servers = ag_mcp["mcpServers"]
    assert set(servers) == {
        "mdpaper",
        "pubmed-search",
        "asset-aware",
        "cgu",
        "drawio",
        "zotero-keeper",
    }
    for name, server in servers.items():
        assert set(server).issubset(ANTIGRAVITY_ALLOWED_MCP_KEYS), name
        assert "type" not in server, name
        assert server["command"] == "uvx", name
    assert servers["mdpaper"]["env"]["MEDPAPER_TOOL_SURFACE"] == "compact"
    assert servers["cgu"]["env"]["CGU_PROVIDER"] == "passthrough"

    plugins_json = _load(ROOT / ".agents" / "plugins.json")
    assert plugins_json == {"entries": [{"path": "plugins"}]}

    skills_json = _load(ROOT / ".agents" / "skills.json")
    assert len(skills_json["entries"]) == 1
    entry = skills_json["entries"][0]
    assert entry["path"] == ".claude/skills"
    bundled_skills = {p.parent.name for p in (PLUGIN_DIR / "skills").glob("*/SKILL.md")}
    assert set(entry["exclude"]) == bundled_skills


def test_antigravity_rules_and_subagents_are_valid() -> None:
    rules_path = PLUGIN_DIR / "rules" / "AGENTS.md"
    rules_bytes = rules_path.read_bytes()
    assert 100 < len(rules_bytes) <= ANTIGRAVITY_RULE_BYTE_LIMIT
    rules_text = rules_bytes.decode("utf-8")
    assert not rules_text.startswith("---")
    assert "workspace_state_action" in rules_text
    assert "save_reference_mcp" in rules_text

    agents = sorted((PLUGIN_DIR / "agents").glob("*.md"))
    assert len(agents) == 9
    for agent_path in agents:
        text = agent_path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), agent_path
        header = yaml.safe_load(text.split("---", 2)[1])
        assert header["name"] == agent_path.stem
        assert header["description"]
        assert header["subagent"] is True
        assert header["mainAgent"] is False
        assert "model" not in header
        assert isinstance(header["tools"], list) and header["tools"]
        assert all(not tool.endswith("/*") for tool in header["tools"])


def test_root_agents_md_stays_within_antigravity_rule_cap() -> None:
    size = (ROOT / "AGENTS.md").stat().st_size
    assert size <= ANTIGRAVITY_RULE_BYTE_LIMIT, (
        f"AGENTS.md is {size} bytes (> {ANTIGRAVITY_RULE_BYTE_LIMIT}); "
        "Antigravity truncates rules over 24,000 bytes"
    )
