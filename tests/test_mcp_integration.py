from __future__ import annotations

import json
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import AnyUrl

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CORE_TOOL_NAMES = {
    "create_project",
    "get_workspace_state",
    "list_saved_references",
    "validate_concept",
    "analyze_dataset",
    "check_formatting",
    "start_document_session",
    "run_quality_checks",
    "pipeline_action",
    "project_action",
    "workspace_state_action",
    "export_document",
    "inspect_export",
}


def _resource_text(result) -> str:
    item = result.contents[0]
    text = getattr(item, "text", None)
    if text is None:
        raise AssertionError("Expected text resource content")
    return text


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
async def open_mcp_session(base_dir: Path | None = None) -> AsyncIterator[ClientSession]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = src_path if not existing else os.pathsep.join([src_path, existing])
    if base_dir is not None:
        env["MEDPAPER_BASE_DIR"] = str(base_dir)

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "med_paper_assistant.interfaces.mcp"],
        cwd=str(base_dir or ROOT),
        env=env,
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@pytest.mark.asyncio
async def test_live_server_exposes_tools_prompts_and_resources() -> None:
    async with open_mcp_session() as session:
        tools = await session.list_tools()
        prompts = await session.list_prompts()
        resources = await session.list_resources()

    assert len(tools.tools) >= len(EXPECTED_CORE_TOOL_NAMES)
    assert len(prompts.prompts) == 3
    assert len(resources.resources) == 3

    tool_names = {tool.name for tool in tools.tools}
    prompt_names = {prompt.name for prompt in prompts.prompts}
    resource_uris = {str(resource.uri) for resource in resources.resources}

    assert len(tool_names) == len(tools.tools)
    assert EXPECTED_CORE_TOOL_NAMES.issubset(tool_names)
    assert prompt_names == {
        "project_bootstrap",
        "draft_section_plan",
        "word_export_checklist",
    }
    assert resource_uris == {
        "medpaper://workspace/state",
        "medpaper://workspace/projects",
        "medpaper://templates/catalog",
    }


@pytest.mark.asyncio
async def test_get_workspace_state_returns_structured_content() -> None:
    async with open_mcp_session() as session:
        result = await session.call_tool("get_workspace_state", {})

    payload = result.structuredContent
    assert isinstance(payload, dict)
    assert "recovery_summary" in payload
    assert "workspace_state" in payload
    assert isinstance(payload["workspace_state"], dict)
    assert isinstance(payload["startup_guidance"], str)


@pytest.mark.asyncio
async def test_resources_are_readable_via_official_client() -> None:
    async with open_mcp_session() as session:
        state = await session.read_resource(AnyUrl("medpaper://workspace/state"))
        projects = await session.read_resource(AnyUrl("medpaper://workspace/projects"))
        templates = await session.read_resource(AnyUrl("medpaper://templates/catalog"))

    state_payload = json.loads(_resource_text(state))
    projects_payload = json.loads(_resource_text(projects))
    templates_payload = json.loads(_resource_text(templates))

    assert isinstance(state_payload, dict)
    assert {"projects", "current", "count"}.issubset(projects_payload.keys())
    assert {"count", "templates"}.issubset(templates_payload.keys())


@pytest.mark.asyncio
async def test_empty_workspace_projects_resource_has_stable_schema(tmp_workspace: Path) -> None:
    async with open_mcp_session(tmp_workspace) as session:
        projects = await session.read_resource(AnyUrl("medpaper://workspace/projects"))

    payload = json.loads(_resource_text(projects))
    assert payload == {"projects": [], "current": None, "count": 0}


@pytest.mark.asyncio
async def test_get_workspace_state_has_stable_empty_shapes(tmp_workspace: Path) -> None:
    async with open_mcp_session(tmp_workspace) as session:
        result = await session.call_tool("get_workspace_state", {})

    payload = result.structuredContent
    assert isinstance(payload, dict)
    assert isinstance(payload["recovery_summary"], str)
    assert isinstance(payload["startup_guidance"], str)
    assert isinstance(payload["workspace_state"], dict)
    assert isinstance(payload["workspace_state"]["workspace_state"]["open_drafts"], list)
    assert isinstance(payload["workspace_state"]["recovery_hints"]["important_context"], list)


@pytest.mark.asyncio
async def test_templates_catalog_resource_has_stable_schema_for_sparse_workspace(
    tmp_workspace: Path,
) -> None:
    async with open_mcp_session(tmp_workspace) as session:
        templates = await session.read_resource(AnyUrl("medpaper://templates/catalog"))

    payload = json.loads(_resource_text(templates))
    assert isinstance(payload, dict)
    assert isinstance(payload["count"], int)
    assert isinstance(payload["templates"], list)


@pytest.mark.asyncio
async def test_workspace_smoke_create_project_then_state_and_resources(tmp_workspace: Path) -> None:
    async with open_mcp_session(tmp_workspace) as session:
        create_result = await session.call_tool(
            "create_project",
            {
                "name": "Smoke Workflow Project",
                "description": "Integration smoke for MCP workspace workflow.",
                "paper_type": "other",
            },
        )
        state_result = await session.call_tool("get_workspace_state", {})
        projects_resource = await session.read_resource(AnyUrl("medpaper://workspace/projects"))
        state_resource = await session.read_resource(AnyUrl("medpaper://workspace/state"))

    create_text = _tool_text(create_result)
    state_payload = state_result.structuredContent
    projects_payload = json.loads(_resource_text(projects_resource))
    workspace_state_payload = json.loads(_resource_text(state_resource))

    assert "Project Created Successfully" in create_text
    assert "Smoke Workflow Project" in create_text

    assert isinstance(state_payload, dict)
    assert "Current Project:" in state_payload["recovery_summary"]
    assert "smoke-workflow-project" in state_payload["recovery_summary"]
    assert isinstance(state_payload["workspace_state"], dict)
    assert state_payload["workspace_state"]["version"] == 2

    assert projects_payload["count"] == 1
    assert projects_payload["current"] == "smoke-workflow-project"
    assert projects_payload["projects"][0]["slug"] == "smoke-workflow-project"
    assert projects_payload["projects"][0]["name"] == "Smoke Workflow Project"

    assert workspace_state_payload["version"] == 2
    assert workspace_state_payload["workspace_state"]["open_drafts"] == []
    assert (tmp_workspace / "projects" / "smoke-workflow-project" / "concept.md").exists()


@pytest.mark.asyncio
async def test_prompt_can_be_materialized() -> None:
    async with open_mcp_session() as session:
        result = await session.get_prompt(
            "draft_section_plan",
            {
                "section": "Discussion",
                "objective": "Summarize the clinical implications.",
                "citation_keys": "smith2025_12345678,lee2024_23456789",
            },
        )

    content = result.messages[0].content
    message_text = getattr(content, "text", None)

    assert isinstance(message_text, str)
    assert "Discussion" in message_text
    assert "clinical implications" in message_text
    assert "smith2025_12345678" in message_text
