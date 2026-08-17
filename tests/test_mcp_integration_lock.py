from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "mcp-integration-lock.json"
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from migrate_mcp_json import REQUIRED_SERVERS  # noqa: E402


def _lock() -> dict:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def _pyproject(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_lock_matrix_covers_every_managed_external_mcp_at_sdk2() -> None:
    lock = _lock()
    integrations = lock["integrations"]

    assert lock["policy"] == {
        "python_mcp_sdk_major": 2,
        "allow_mcp_v1_fallback": False,
    }
    assert set(integrations) == {
        "asset-aware",
        "pubmed-search",
        "cgu",
        "drawio",
        "zotero-keeper",
    }

    for name, integration in integrations.items():
        assert integration["mcp_sdk_major"] == 2, name
        assert integration["mcp_requirement"].startswith("mcp>=2"), name
        assert integration["commit"].isalnum() and len(integration["commit"]) == 40, name
        assert integration["commit"] in integration["package_source"], name
        assert integration["entrypoint"], name
        assert integration["version"], name


def test_locked_submodule_commits_versions_and_requirements_match_checkout() -> None:
    integrations = _lock()["integrations"]
    pyprojects = {
        "asset-aware": ROOT / "integrations/asset-aware-mcp/pyproject.toml",
        "pubmed-search": ROOT / "integrations/pubmed-search-mcp/pyproject.toml",
        "cgu": ROOT / "integrations/cgu/pyproject.toml",
        "drawio": ROOT / "integrations/next-ai-draw-io/mcp-server/pyproject.toml",
    }

    for name, pyproject_path in pyprojects.items():
        integration = integrations[name]
        checkout = ROOT / integration["path"]
        checked_out_commit = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert checked_out_commit == integration["commit"], name

        project = _pyproject(pyproject_path)["project"]
        assert project["version"] == integration["version"], name
        mcp_dependencies = [
            Requirement(dependency)
            for dependency in project["dependencies"]
            if Requirement(dependency).name == "mcp"
        ]
        assert len(mcp_dependencies) == 1, name
        specifier = mcp_dependencies[0].specifier
        assert Version("2.0.0") in specifier, name
        assert Version("1.99.99") not in specifier, name
        assert Version("3.0.0") not in specifier, name


def test_workspace_and_migration_use_the_same_safe_launch_contract() -> None:
    workspace = json.loads((ROOT / ".vscode/mcp.json").read_text(encoding="utf-8"))

    for name in ["pubmed-search", "cgu", "zotero-keeper", "asset-aware", "drawio"]:
        assert workspace["servers"][name] == REQUIRED_SERVERS[name], name

    zotero_args = workspace["servers"]["zotero-keeper"]["args"]
    zotero = _lock()["integrations"]["zotero-keeper"]
    assert zotero_args == [
        "--python",
        "3.12",
        "--from",
        zotero["package_source"],
        zotero["entrypoint"],
    ]
    assert zotero_args != ["zotero-keeper"]

    drawio = workspace["servers"]["drawio"]
    assert drawio["command"] == "uv"
    assert "drawio-mcp-server" in drawio["args"]
    assert "@drawio/mcp" not in drawio["args"]


def test_setup_and_vsix_sources_do_not_launch_known_mcp1_fallbacks() -> None:
    launcher_paths = [
        ROOT / "scripts/setup.sh",
        ROOT / "scripts/setup.ps1",
        ROOT / "scripts/setup-integrations.sh",
        ROOT / "scripts/setup-integrations.ps1",
        ROOT / "scripts/start-drawio.sh",
        ROOT / "scripts/start-drawio.ps1",
        ROOT / "vscode-extension/src/extension.ts",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in launcher_paths)

    assert "@drawio/mcp" not in combined
    assert "buildMcpCommand(uvPath, 'zotero-keeper')" not in combined
    assert "buildMcpCommand(uvPath, 'pubmed-search-mcp')" not in combined
    assert "MCP_INTEGRATION_PACKAGES['zotero-keeper']" in combined
    assert "buildPinnedUvxCommand" in combined
