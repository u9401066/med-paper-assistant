from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _run_isolated_package_smoke(package_requirement: str, smoke_code: str) -> dict:
    completed = subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            "--isolated",
            "--python",
            "3.12",
            "--with",
            package_requirement,
            "python",
            "-c",
            smoke_code,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.mark.integration
@pytest.mark.slow
def test_exact_zotero_archive_installs_and_exposes_sdk2_surface() -> None:
    """Network smoke for the exact source used by setup and the VSIX."""
    lock = json.loads((ROOT / "mcp-integration-lock.json").read_text(encoding="utf-8"))
    zotero = lock["integrations"]["zotero-keeper"]
    package_requirement = f"zotero-keeper @ {zotero['package_source']}"
    smoke_code = """
import asyncio
import importlib.metadata as metadata
import json
from mcp.server import MCPServer
from zotero_mcp.infrastructure.mcp.server import create_server

server = create_server().mcp
tools = asyncio.run(server.list_tools())
print(json.dumps({
    "keeper_version": metadata.version("zotero-keeper"),
    "mcp_version": metadata.version("mcp"),
    "server_type": type(server).__name__,
    "is_sdk2_server": isinstance(server, MCPServer),
    "tool_count": len(tools),
}))
"""

    result = _run_isolated_package_smoke(package_requirement, smoke_code)

    assert result == {
        "keeper_version": "2.1.0",
        "mcp_version": "2.0.0",
        "server_type": "MCPServer",
        "is_sdk2_server": True,
        "tool_count": 32,
    }


@pytest.mark.integration
@pytest.mark.slow
def test_exact_drawio_archive_installs_and_exposes_sdk2_surface() -> None:
    """The replacement for the removed npm SDK1 fallback is installable."""
    lock = json.loads((ROOT / "mcp-integration-lock.json").read_text(encoding="utf-8"))
    drawio = lock["integrations"]["drawio"]
    package_requirement = f"drawio-mcp-server @ {drawio['package_source']}"
    smoke_code = """
import asyncio
import importlib.metadata as metadata
import json
from mcp.server import MCPServer
from drawio_mcp_server.server import mcp

tools = asyncio.run(mcp.list_tools())
print(json.dumps({
    "drawio_version": metadata.version("drawio-mcp-server"),
    "mcp_version": metadata.version("mcp"),
    "server_type": type(mcp).__name__,
    "is_sdk2_server": isinstance(mcp, MCPServer),
    "tool_count": len(tools),
}))
"""

    result = _run_isolated_package_smoke(package_requirement, smoke_code)

    assert result == {
        "drawio_version": "2.0.0",
        "mcp_version": "2.0.0",
        "server_type": "MCPServer",
        "is_sdk2_server": True,
        "tool_count": 23,
    }
