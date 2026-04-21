from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]


def _tool_text(result) -> str:
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if isinstance(text, str):
            return text

    message = getattr(result, "message", None)
    if isinstance(message, str):
        return message

    raise AssertionError("Expected text tool content")


@asynccontextmanager
async def open_mcp_session(base_dir: Path) -> AsyncIterator[ClientSession]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = src_path if not existing else os.pathsep.join([src_path, existing])
    env["MEDPAPER_BASE_DIR"] = str(base_dir)
    env["MEDPAPER_TOOL_SURFACE"] = "full"

    params = StdioServerParameters(
        command=os.environ.get("PYTHON", "python"),
        args=["-m", "med_paper_assistant.interfaces.mcp"],
        cwd=str(base_dir),
        env=env,
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@pytest.mark.asyncio
async def test_local_import_and_analysis_round_trip_updates_note_and_metadata(
    tmp_workspace: Path,
) -> None:
    source_file = tmp_workspace / "paper.pdf"
    source_file.write_bytes(b"synthetic-local-pdf")

    metadata = {
        "title": "Local import via MCP",
        "authors": ["Chen Eric"],
        "year": "2026",
        "data_source": "asset_aware",
        "asset_aware_doc_id": "doc_local_001",
        "fulltext_sections": ["Methods", "Results"],
        "extracted_markdown": "# Methods\n\nParsed section content.",
    }

    async with open_mcp_session(tmp_workspace) as session:
        import_result = await session.call_tool(
            "import_local_papers",
            {"paths": str(source_file), "metadata_json": json.dumps(metadata)},
        )

    import_text = _tool_text(import_result)
    assert "Successfully imported local source" in import_text

    project_root = tmp_workspace / "projects" / "temp-exploration"
    references_dir = project_root / "references"
    ref_dirs = [path for path in references_dir.iterdir() if path.is_dir()]
    assert len(ref_dirs) == 1

    ref_dir = ref_dirs[0]
    ref_id = ref_dir.name
    metadata_path = ref_dir / "metadata.json"
    initial_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    verified_metadata = {
        "pmid": "12345678",
        "title": "Resolved verified reference",
        "authors": ["Chen Eric"],
        "authors_full": [{"last_name": "Chen", "first_name": "Eric", "initials": "E"}],
        "year": "2026",
        "journal": "Journal of Testing",
        "doi": "10.1000/test.2026.1",
        "abstract": "Verified abstract content.",
    }

    async with open_mcp_session(tmp_workspace) as session:
        resolve_result = await session.call_tool(
            "resolve_reference_identity",
            {
                "reference_id": ref_id,
                "verified_metadata_json": json.dumps(verified_metadata),
            },
        )
        resolve_text = _tool_text(resolve_result)
        assert "Resolved" in resolve_text

        canonical_ref_dir = references_dir / "12345678"
        assert canonical_ref_dir.exists()
        assert not (references_dir / ref_id).exists()

        metadata_path = canonical_ref_dir / "metadata.json"
        updated_after_resolution = json.loads(metadata_path.read_text(encoding="utf-8"))
        note_path = canonical_ref_dir / f"{updated_after_resolution['citation_key']}.md"

        analysis_package = await session.call_tool(
            "get_reference_for_analysis", {"pmid": "12345678"}
        )
        save_result = await session.call_tool(
            "save_reference_analysis",
            {
                "pmid": "12345678",
                "summary": "Parsed fulltext confirms the local import pipeline works.",
                "usage_sections": "Introduction,Discussion",
                "relevance_score": 4,
            },
        )

    analysis_text = _tool_text(analysis_package)
    save_text = _tool_text(save_result)

    assert updated_after_resolution["pmid"] == "12345678"
    assert updated_after_resolution["content_hash"]
    assert (canonical_ref_dir / "artifacts" / "asset-aware" / "sections.md").exists()
    assert "Fulltext available**: Yes" in analysis_text
    assert "Parsed section content." in analysis_text
    assert "✅ Analysis saved" in save_text

    updated_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    note_text = note_path.read_text(encoding="utf-8")

    assert updated_metadata["analysis_completed"] is True
    assert updated_metadata["analysis_summary"] == (
        "Parsed fulltext confirms the local import pipeline works."
    )
    assert updated_metadata["usage_sections"] == ["Introduction", "Discussion"]
    assert initial_metadata["citation_key"] in updated_metadata["legacy_aliases"]
    assert ref_id in updated_metadata["legacy_aliases"]
    assert "analysis_completed: true" in note_text
    assert initial_metadata["citation_key"] in note_text
    assert f'  - "{ref_id}"' in note_text
    assert "Parsed fulltext confirms the local import pipeline works." in note_text


@pytest.mark.asyncio
async def test_markdown_intake_and_agent_wiki_materialization_via_mcp(
    tmp_workspace: Path,
) -> None:
    markdown_text = (
        "# ICU Sedation Notes\n\n"
        "Remimazolam may become a useful ICU sedation option.\n\n"
        "## Findings\n\n"
        "Current evidence is still sparse.\n"
    )
    metadata = {
        "title": "ICU Sedation Notes",
        "authors": ["Chen Eric"],
        "year": "2026",
    }

    async with open_mcp_session(tmp_workspace) as session:
        intake_result = await session.call_tool(
            "ingest_markdown_source",
            {"markdown_text": markdown_text, "metadata_json": json.dumps(metadata)},
        )

    intake_text = _tool_text(intake_result)
    assert "Successfully imported markdown source" in intake_text

    project_root = tmp_workspace / "projects" / "temp-exploration"
    references_dir = project_root / "references"
    ref_dirs = [path for path in references_dir.iterdir() if path.is_dir()]
    assert len(ref_dirs) == 1
    ref_id = ref_dirs[0].name

    async with open_mcp_session(tmp_workspace) as session:
        materialize_result = await session.call_tool(
            "materialize_agent_wiki",
            {
                "knowledge_map_title": "ICU Sedation Map",
                "reference_ids": ref_id,
                "focus": "Delirium implications",
            },
        )

    materialize_text = _tool_text(materialize_result)
    index_text = (project_root / "notes" / "index.md").read_text(encoding="utf-8")
    knowledge_map_text = (
        project_root / "notes" / "knowledge-maps" / "icu-sedation-map.md"
    ).read_text(encoding="utf-8")
    synthesis_text = (
        project_root / "notes" / "synthesis-pages" / "icu-sedation-map-synthesis.md"
    ).read_text(encoding="utf-8")

    assert "Agent wiki materialized" in materialize_text
    assert "[[knowledge-map-icu-sedation-map]]" in index_text
    assert "[[synthesis-icu-sedation-map-synthesis]]" in index_text
    assert "## Reference Graph" in knowledge_map_text
    assert "## Evidence Base" in synthesis_text