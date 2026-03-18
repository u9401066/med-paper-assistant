"""Tests for scripts/migrate_mcp_json.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make scripts/ importable
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from migrate_mcp_json import (  # noqa: E402
    REQUIRED_SERVERS,
    find_missing_servers,
    load_mcp_json,
    migrate,
)


@pytest.fixture()
def tmp_mcp(tmp_path: Path):
    """Return a factory that writes mcp.json with given servers and returns the path."""

    def _make(servers: dict | None = None) -> Path:
        data = {"inputs": [], "servers": servers or {}}
        p = tmp_path / "mcp.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    return _make


class TestFindMissingServers:
    def test_empty_servers_returns_all(self):
        missing = find_missing_servers({"servers": {}})
        assert set(missing) == set(REQUIRED_SERVERS.keys())

    def test_all_present_returns_empty(self):
        servers = {name: {"type": "stdio"} for name in REQUIRED_SERVERS}
        missing = find_missing_servers({"servers": servers})
        assert missing == []

    def test_partial_returns_missing(self):
        servers = {"mdpaper": {}, "cgu": {}}
        missing = find_missing_servers({"servers": servers})
        assert "pubmed-search" in missing
        assert "zotero-keeper" in missing
        assert "mdpaper" not in missing

    def test_no_servers_key(self):
        missing = find_missing_servers({})
        assert set(missing) == set(REQUIRED_SERVERS.keys())


class TestLoadMcpJson:
    def test_loads_plain_json(self, tmp_path: Path):
        p = tmp_path / "mcp.json"
        p.write_text('{"inputs": [], "servers": {"mdpaper": {}}}', encoding="utf-8")

        data, mode = load_mcp_json(p)

        assert mode is None
        assert "mdpaper" in data["servers"]

    def test_loads_jsonc_with_line_comments(self, tmp_path: Path):
        p = tmp_path / "mcp.json"
        p.write_text(
            '{\n  "inputs": [],\n  "servers": {\n    // comment\n    "mdpaper": {}\n  }\n}\n',
            encoding="utf-8",
        )

        data, mode = load_mcp_json(p)

        assert mode == "jsonc"
        assert "mdpaper" in data["servers"]


class TestMigrate:
    def test_adds_missing_servers(self, tmp_mcp):
        p = tmp_mcp({"mdpaper": {"type": "stdio", "command": "my-custom-uv"}})
        rc = migrate(p)
        assert rc == 0

        data = json.loads(p.read_text(encoding="utf-8"))
        # All 6 servers should now be present
        assert set(data["servers"].keys()) == set(REQUIRED_SERVERS.keys())
        # User's custom mdpaper config should be preserved
        assert data["servers"]["mdpaper"]["command"] == "my-custom-uv"

    def test_creates_backup(self, tmp_mcp):
        p = tmp_mcp({"mdpaper": {}})
        rc = migrate(p)
        assert rc == 0
        backups = list(p.parent.glob("mcp.json.bak.*"))
        assert len(backups) == 1

    def test_already_up_to_date(self, tmp_mcp):
        servers = {name: {"type": "stdio"} for name in REQUIRED_SERVERS}
        p = tmp_mcp(servers)
        rc = migrate(p)
        assert rc == 1  # up-to-date
        # No backup created
        backups = list(p.parent.glob("mcp.json.bak.*"))
        assert len(backups) == 0

    def test_dry_run_does_not_modify(self, tmp_mcp):
        p = tmp_mcp({"mdpaper": {}})
        original_text = p.read_text()
        rc = migrate(p, dry_run=True)
        assert rc == 0
        assert p.read_text() == original_text
        backups = list(p.parent.glob("mcp.json.bak.*"))
        assert len(backups) == 0

    def test_file_not_found(self, tmp_path):
        rc = migrate(tmp_path / "nonexistent.json")
        assert rc == 2

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "mcp.json"
        p.write_text("not json {{{")
        rc = migrate(p)
        assert rc == 2

    def test_preserves_extra_servers(self, tmp_mcp):
        """User-added servers outside the canonical set should be kept."""
        servers = {name: {"type": "stdio"} for name in REQUIRED_SERVERS}
        servers["my-custom-mcp"] = {"type": "stdio", "command": "my-tool"}
        p = tmp_mcp(servers)
        rc = migrate(p)
        assert rc == 1  # already up-to-date
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "my-custom-mcp" in data["servers"]

    def test_normalizes_jsonc_even_when_no_servers_missing(self, tmp_path: Path):
        servers = ",\n".join(f'    "{name}": {{"type": "stdio"}}' for name in REQUIRED_SERVERS)
        p = tmp_path / "mcp.json"
        p.write_text(
            f'{{\n  "inputs": [],\n  "servers": {{\n    // normalize me\n{servers}\n  }}\n}}\n',
            encoding="utf-8",
        )

        rc = migrate(p)

        assert rc == 0
        data = json.loads(p.read_text(encoding="utf-8"))
        assert set(data["servers"].keys()) >= set(REQUIRED_SERVERS.keys())
