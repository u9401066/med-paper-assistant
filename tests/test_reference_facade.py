from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from mcp.server import MCPServer

from med_paper_assistant.interfaces.mcp.tools.reference import register_reference_tools
from med_paper_assistant.interfaces.mcp.tools.reference.facade import (
    register_reference_facade_tools,
)


def _capture_reference_registration(surface: str) -> tuple[set[str], dict[str, Callable[..., Any]]]:
    mock_mcp = MagicMock()
    captured: set[str] = set()

    def fake_tool(*args: Any, **kwargs: Any):
        del args, kwargs

        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            captured.add(handler.__name__)
            return handler

        return decorator

    mock_mcp.tool = fake_tool
    handlers = register_reference_tools(
        mock_mcp,
        ref_manager=MagicMock(),
        drafter=MagicMock(),
        project_manager=MagicMock(),
        tool_surface=surface,
    )
    return captured, handlers


def test_compact_reference_surface_keeps_only_safe_direct_verb_and_facade() -> None:
    captured, handlers = _capture_reference_registration("compact")

    assert captured == {"save_reference_mcp", "reference_action"}
    assert {
        "save_reference",
        "save_reference_mcp",
        "list_saved_references",
        "search_local_references",
        "get_reference_details",
        "read_reference_fulltext",
        "save_reference_pdf",
        "format_references",
        "rebuild_foam_aliases",
        "delete_reference",
        "get_reference_for_analysis",
        "save_reference_analysis",
        "reference_action",
    } == set(handlers)


def test_full_reference_surface_preserves_direct_verbs_without_facade() -> None:
    captured, handlers = _capture_reference_registration("full")
    expected_direct = {
        "save_reference",
        "save_reference_mcp",
        "import_local_papers",
        "ingest_web_source",
        "ingest_markdown_source",
        "resolve_reference_identity",
        "build_knowledge_map",
        "build_synthesis_page",
        "materialize_agent_wiki",
        "list_saved_references",
        "search_local_references",
        "get_reference_details",
        "read_reference_fulltext",
        "save_reference_pdf",
        "format_references",
        "rebuild_foam_aliases",
        "delete_reference",
        "get_reference_for_analysis",
        "save_reference_analysis",
    }

    assert captured == expected_direct
    assert set(handlers) == expected_direct
    assert "reference_action" not in captured


@pytest.mark.asyncio
async def test_reference_action_list_returns_machine_readable_schema() -> None:
    handlers = register_reference_facade_tools(
        MCPServer("reference-facade-list-test"),
        reference_tools={},
    )

    result = await handlers["reference_action"](action="list")
    payload = json.loads(result)

    assert payload["schema"] == "mdpaper.facade_actions.v1"
    assert payload["tool"] == "reference_action"
    assert {
        "save_agent",
        "list",
        "list_saved",
        "search",
        "details",
        "fulltext",
        "save_pdf",
        "format",
        "rebuild_aliases",
        "delete",
        "analysis_get",
        "analysis_save",
    } == set(payload["actions"])
    assert payload["actions"]["save_agent"]["handler"] == "save_reference"
    assert payload["actions"]["list_saved"]["handler"] == "list_saved_references"
    assert "save_reference_mcp" in " ".join(payload["notes"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "handler_name", "call_kwargs", "expected_kwargs"),
    [
        (
            "save_agent",
            "save_reference",
            {"article": {"pmid": "123"}, "project": "demo"},
            {"article": {"pmid": "123"}, "project": "demo"},
        ),
        (
            "list_saved",
            "list_saved_references",
            {"project": "demo"},
            {"project": "demo"},
        ),
        (
            "search",
            "search_local_references",
            {"query": "sedation"},
            {"query": "sedation"},
        ),
        (
            "details",
            "get_reference_details",
            {"pmid": "123"},
            {"pmid": "123"},
        ),
        (
            "fulltext",
            "read_reference_fulltext",
            {"pmid": "123", "max_chars": 321},
            {"pmid": "123", "max_chars": 321},
        ),
        (
            "save_pdf",
            "save_reference_pdf",
            {"pmid": "123", "pdf_content": "JVBERg=="},
            {"pmid": "123", "pdf_content": "JVBERg=="},
        ),
        (
            "format",
            "format_references",
            {"pmid": "123", "style": "apa"},
            {"pmids": "123", "style": "apa"},
        ),
        (
            "rebuild_aliases",
            "rebuild_foam_aliases",
            {"project": "demo"},
            {"project": "demo"},
        ),
        (
            "delete",
            "delete_reference",
            {"pmid": "123", "confirm": True, "project": "demo"},
            {"pmid": "123", "confirm": True, "project": "demo"},
        ),
        (
            "analysis_get",
            "get_reference_for_analysis",
            {"pmid": "123", "project": "demo"},
            {"pmid": "123", "project": "demo"},
        ),
        (
            "analysis_save",
            "save_reference_analysis",
            {
                "pmid": "123",
                "summary": "Summary",
                "methodology": "RCT",
                "key_findings": "Benefit",
                "limitations": "Small sample",
                "usage_sections": "Discussion",
                "relevance_score": 4,
                "project": "demo",
            },
            {
                "pmid": "123",
                "summary": "Summary",
                "methodology": "RCT",
                "key_findings": "Benefit",
                "limitations": "Small sample",
                "usage_sections": "Discussion",
                "relevance_score": 4,
                "project": "demo",
            },
        ),
    ],
)
async def test_reference_action_routes_existing_handler(
    action: str,
    handler_name: str,
    call_kwargs: dict[str, Any],
    expected_kwargs: dict[str, Any],
) -> None:
    captured: dict[str, Any] = {}

    def handler(**kwargs: Any) -> str:
        captured.update(kwargs)
        return f"{handler_name}-ok"

    handlers = register_reference_facade_tools(
        MCPServer(f"reference-facade-{action}-test"),
        reference_tools={handler_name: handler},
    )

    result = await handlers["reference_action"](action=action, **call_kwargs)

    assert result == f"{handler_name}-ok"
    assert captured == expected_kwargs


@pytest.mark.asyncio
async def test_reference_action_routes_legacy_alias() -> None:
    captured: dict[str, Any] = {}

    def list_saved_references(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "listed"

    handlers = register_reference_facade_tools(
        MCPServer("reference-facade-alias-test"),
        reference_tools={"list_saved_references": list_saved_references},
    )

    result = await handlers["reference_action"](
        action="list_saved_references",
        project="demo",
    )

    assert result == "listed"
    assert captured == {"project": "demo"}


@pytest.mark.asyncio
async def test_reference_action_rejects_missing_required_payloads_before_dispatch() -> None:
    called = False

    def handler(**kwargs: Any) -> str:
        nonlocal called
        called = True
        return str(kwargs)

    handlers = register_reference_facade_tools(
        MCPServer("reference-facade-validation-test"),
        reference_tools={
            "save_reference": handler,
            "save_reference_analysis": handler,
        },
    )

    missing_article = await handlers["reference_action"](action="save_agent")
    missing_summary = await handlers["reference_action"](
        action="analysis_save",
        pmid="123",
    )

    assert "article" in missing_article
    assert "summary" in missing_summary
    assert called is False


@pytest.mark.asyncio
async def test_reference_action_reports_missing_handler_and_unsupported_action() -> None:
    handlers = register_reference_facade_tools(
        MCPServer("reference-facade-error-test"),
        reference_tools={},
    )

    missing = await handlers["reference_action"](action="details", pmid="123")
    unsupported = await handlers["reference_action"](action="save_mcp", pmid="123")

    assert "missing handler 'get_reference_details'" in missing
    assert "Unsupported action 'save_mcp'" in unsupported
