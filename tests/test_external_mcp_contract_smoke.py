from __future__ import annotations

from pathlib import Path

from med_paper_assistant.shared.jsonc import load_jsonc

ROOT = Path(__file__).resolve().parents[1]


def test_external_mcp_servers_are_declared_in_workspace_config() -> None:
    data = load_jsonc(ROOT / ".vscode" / "mcp.json")
    servers = data.get("servers") or data.get("mcpServers", {})

    for name in ["asset-aware", "pubmed-search", "drawio", "zotero-keeper"]:
        assert name in servers

    assert "asset-aware-mcp" in " ".join(servers["asset-aware"].get("args", []))
    assert "pubmed-search-mcp" in " ".join(servers["pubmed-search"].get("args", []))
    assert "drawio-mcp-server" in " ".join(servers["drawio"].get("args", []))
    zotero_args = servers["zotero-keeper"].get("args", [])
    assert zotero_args[-1] == "zotero-keeper"
    assert "--from" in zotero_args
    assert "1faf5733dc7bbc05d0fac8ffe16c51f4585b5ce5" in " ".join(zotero_args)


def test_asset_aware_receipt_contract_shape() -> None:
    """Document the external asset-aware output mdpaper consumes."""
    receipt = {
        "asset_aware_doc_id": "doc_asset_001",
        "sections": ["Methods", "Results"],
        "artifact_paths": ["artifacts/asset-aware/sections.md"],
    }

    assert isinstance(receipt["asset_aware_doc_id"], str)
    assert isinstance(receipt["sections"], list)
    assert isinstance(receipt["artifact_paths"], list)
