from __future__ import annotations

from med_paper_assistant.infrastructure.persistence import _reset_project_manager
from med_paper_assistant.interfaces.mcp.server import create_server


def _registered_tool_names(surface: str, workspace_root: str) -> set[str]:
    import os

    previous_base_dir = os.environ.get("MEDPAPER_BASE_DIR")
    previous_surface = os.environ.get("MEDPAPER_TOOL_SURFACE")

    try:
        os.environ["MEDPAPER_BASE_DIR"] = workspace_root
        os.environ["MEDPAPER_TOOL_SURFACE"] = surface
        _reset_project_manager()

        server = create_server()
        return set(server._tool_manager._tools.keys())
    finally:
        if previous_base_dir is None:
            os.environ.pop("MEDPAPER_BASE_DIR", None)
        else:
            os.environ["MEDPAPER_BASE_DIR"] = previous_base_dir

        if previous_surface is None:
            os.environ.pop("MEDPAPER_TOOL_SURFACE", None)
        else:
            os.environ["MEDPAPER_TOOL_SURFACE"] = previous_surface

        _reset_project_manager()


def test_compact_surface_reduces_main_mdpaper_tool_count(tmp_path) -> None:
    full_tools = _registered_tool_names("full", str(tmp_path))
    compact_tools = _registered_tool_names("compact", str(tmp_path))

    assert len(full_tools) >= 94
    assert len(compact_tools) <= 44
    assert len(full_tools) - len(compact_tools) >= 50

    assert {
        "project_action",
        "workspace_state_action",
        "run_quality_checks",
        "pipeline_action",
        "export_document",
        "inspect_export",
    }.issubset(compact_tools)

    assert "create_project" not in compact_tools
    assert "check_formatting" not in compact_tools
    assert "run_quality_audit" not in compact_tools
    assert "export_docx" not in compact_tools
    assert "list_templates" not in compact_tools
    assert "import_local_papers" in full_tools
    assert "import_local_papers" not in compact_tools
    assert "resolve_reference_identity" in full_tools
    assert "resolve_reference_identity" not in compact_tools
    assert "ingest_web_source" in full_tools
    assert "ingest_web_source" not in compact_tools
    assert "ingest_markdown_source" in full_tools
    assert "ingest_markdown_source" not in compact_tools
    assert "build_knowledge_map" in full_tools
    assert "build_knowledge_map" not in compact_tools
    assert "build_synthesis_page" in full_tools
    assert "build_synthesis_page" not in compact_tools
    assert "materialize_agent_wiki" in full_tools
    assert "materialize_agent_wiki" not in compact_tools
