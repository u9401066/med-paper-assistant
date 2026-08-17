from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_NAMES = (
    "asset-aware",
    "pubmed-search",
    "cgu",
    "drawio",
    "zotero-keeper",
)
PROTOCOL_VERSION = "2026-07-28"

SMOKE_CODE = r"""
import asyncio
import importlib.metadata as metadata
import json
import os
from pathlib import Path

from mcp import Client
from mcp.server import MCPServer

config = json.loads(os.environ["MEDPAPER_EXTERNAL_MCP_SMOKE_CONFIG"])
workspace = Path(os.environ["MEDPAPER_EXTERNAL_MCP_SMOKE_DIR"])


def build_server(name):
    if name == "asset-aware":
        from src.presentation.server import mcp

        return mcp
    if name == "pubmed-search":
        from pubmed_search.presentation.mcp_server.server import create_server

        return create_server(
            email="release-smoke@example.org",
            data_dir=str(workspace / "pubmed-data"),
            workspace_dir=str(workspace),
            mode="local",
        )
    if name == "cgu":
        from cgu.server import mcp

        return mcp
    if name == "drawio":
        from drawio_mcp_server.server import mcp

        return mcp
    if name == "zotero-keeper":
        from zotero_mcp.infrastructure.mcp.server import create_server

        return create_server().mcp
    raise AssertionError(f"Unknown managed MCP integration: {name}")


async def smoke():
    server = build_server(config["name"])
    async with Client(server, mode="2026-07-28") as client:
        tools = await client.list_tools()
        prompts = await client.list_prompts()
        resources = await client.list_resources()
        tool_names = [tool.name for tool in tools.tools]
        representative = config["smoke_call"]
        assert representative["tool"] in tool_names
        call_result = await client.call_tool(
            representative["tool"],
            representative["arguments"],
        )

        return {
            "package_version": metadata.version(config["package"]),
            "mcp_version": metadata.version("mcp"),
            "server_type": type(server).__name__,
            "is_sdk2_server": isinstance(server, MCPServer),
            "protocol_version": client.session.protocol_version,
            "tool_count": len(tools.tools),
            "prompt_count": len(prompts.prompts),
            "resource_count": len(resources.resources),
            "unique_tool_names": len(tool_names) == len(set(tool_names)),
            "representative_tool": representative["tool"],
            "call_is_error": bool(getattr(call_result, "is_error", False)),
            "call_content_count": len(getattr(call_result, "content", []) or []),
            "call_has_structured_content": getattr(
                call_result, "structured_content", None
            )
            is not None,
        }


print(json.dumps(asyncio.run(smoke()), default=str))
"""


def _load_lock() -> dict:
    return json.loads((ROOT / "mcp-integration-lock.json").read_text(encoding="utf-8"))


def _run_isolated_package_smoke(
    name: str,
    integration: dict,
    workspace: Path,
) -> dict:
    workspace.mkdir(parents=True, exist_ok=True)
    package_requirement = f"{integration['package']} @ {integration['package_source']}"
    config = {
        "name": name,
        "package": integration["package"],
        "smoke_call": integration["smoke_call"],
    }
    env = os.environ.copy()
    env.update(
        {
            "ASSET_AWARE_DATA_DIR": str(workspace / "asset-aware-data"),
            "MEDPAPER_EXTERNAL_MCP_SMOKE_CONFIG": json.dumps(config),
            "MEDPAPER_EXTERNAL_MCP_SMOKE_DIR": str(workspace),
        }
    )
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
            SMOKE_CODE,
        ],
        cwd=workspace,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"{name} exact-archive smoke failed\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(360)
@pytest.mark.parametrize("name", INTEGRATION_NAMES)
def test_exact_archive_initializes_sdk2_surface_and_safe_call(
    name: str,
    tmp_path: Path,
) -> None:
    """Exercise the immutable package source used by setup, release, and VSIX."""
    integration = _load_lock()["integrations"][name]
    result = _run_isolated_package_smoke(name, integration, tmp_path / name)

    assert result["package_version"] == integration["version"]
    assert int(result["mcp_version"].split(".", maxsplit=1)[0]) == 2
    assert result["is_sdk2_server"] is True
    assert result["protocol_version"] == PROTOCOL_VERSION
    assert result["tool_count"] == integration["surface"]["tools"]
    assert result["prompt_count"] == integration["surface"]["prompts"]
    assert result["resource_count"] == integration["surface"]["resources"]
    assert result["unique_tool_names"] is True
    assert result["representative_tool"] == integration["smoke_call"]["tool"]
    assert result["call_is_error"] is False
    assert result["call_content_count"] > 0 or result["call_has_structured_content"]
