"""Regression tests for documentation count authority."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import sync_repo_counts  # noqa: E402


def test_external_counts_come_from_tool_surface_authority() -> None:
    authority = json.loads((ROOT / "tool-surface-authority.json").read_text(encoding="utf-8"))

    assert sync_repo_counts.EXTERNAL_MCP == authority["externalMcp"]
    counts = sync_repo_counts.gather_counts()
    assert counts.asset_aware_tools == 30
    assert counts.pubmed_tools == 45
    assert counts.cgu_tools == 24
    assert counts.drawio_tools == 23
    assert counts.zotero_tools == 32
    assert counts.mcp_servers == 3
    assert counts.managed_mcp_servers == 6
    assert counts.managed_total_tools == 272


def test_repo_count_check_is_clean() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "sync_repo_counts.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise AssertionError(result.stdout + "\n" + result.stderr)
