import asyncio
from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.interfaces.mcp.tools.draft import register_draft_tools
from med_paper_assistant.interfaces.mcp.tools.draft.facade import register_draft_facade_tools


def test_draft_facade_routes_write_action() -> None:
    captured: dict[str, str] = {}

    def write_draft(**kwargs):
        captured.update(kwargs)
        return "write-ok"

    funcs = register_draft_facade_tools(
        FastMCP("draft-facade-test"),
        writing_tools={"write_draft": write_draft},
        template_tools={},
        editing_tools={},
        citation_tools={},
    )

    result = asyncio.run(
        funcs["draft_action"](
            action="write_draft",
            filename="intro.md",
            content="content",
            project="demo",
        )
    )

    assert result == "write-ok"
    assert captured == {
        "filename": "intro.md",
        "content": "content",
        "project": "demo",
    }


def test_draft_facade_write_derives_filename_from_section() -> None:
    captured: dict[str, str] = {}

    def write_draft(**kwargs):
        captured.update(kwargs)
        return "write-ok"

    funcs = register_draft_facade_tools(
        FastMCP("draft-facade-section-test"),
        writing_tools={"write_draft": write_draft},
        template_tools={},
        editing_tools={},
        citation_tools={},
    )

    result = asyncio.run(
        funcs["draft_action"](
            action="write",
            section="Methods",
            content="Methods text",
            project="demo",
        )
    )

    assert result == "write-ok"
    assert captured == {
        "filename": "methods.md",
        "content": "Methods text",
        "project": "demo",
    }


def test_draft_facade_write_uses_notes_when_content_empty() -> None:
    captured: dict[str, str] = {}

    def write_draft(**kwargs):
        captured.update(kwargs)
        return "write-ok"

    funcs = register_draft_facade_tools(
        FastMCP("draft-facade-notes-test"),
        writing_tools={"write_draft": write_draft},
        template_tools={},
        editing_tools={},
        citation_tools={},
    )

    result = asyncio.run(
        funcs["draft_action"](
            action="write",
            section="Results",
            notes="Results text",
            project="demo",
        )
    )

    assert result == "write-ok"
    assert captured == {
        "filename": "results.md",
        "content": "Results text",
        "project": "demo",
    }


def test_draft_facade_write_rejects_missing_filename_and_section() -> None:
    called = False

    def write_draft(**kwargs):
        nonlocal called
        called = True
        return "write-ok"

    funcs = register_draft_facade_tools(
        FastMCP("draft-facade-missing-filename-test"),
        writing_tools={"write_draft": write_draft},
        template_tools={},
        editing_tools={},
        citation_tools={},
    )

    result = asyncio.run(funcs["draft_action"](action="write", content="content"))

    assert "filename" in result
    assert called is False


def test_draft_facade_write_rejects_empty_content() -> None:
    called = False

    def write_draft(**kwargs):
        nonlocal called
        called = True
        return "write-ok"

    funcs = register_draft_facade_tools(
        FastMCP("draft-facade-empty-content-test"),
        writing_tools={"write_draft": write_draft},
        template_tools={},
        editing_tools={},
        citation_tools={},
    )

    result = asyncio.run(funcs["draft_action"](action="write", section="Methods"))

    assert "content" in result
    assert called is False


def test_draft_facade_count_words_derives_filename_from_section() -> None:
    captured: dict[str, str] = {}

    def count_words(**kwargs):
        captured.update(kwargs)
        return "count-ok"

    funcs = register_draft_facade_tools(
        FastMCP("draft-facade-count-section-test"),
        writing_tools={},
        template_tools={"count_words": count_words},
        editing_tools={},
        citation_tools={},
    )

    result = asyncio.run(
        funcs["draft_action"](action="count_words", section="Methods", project="demo")
    )

    assert result == "count-ok"
    assert captured == {
        "filename": "methods.md",
        "project": "demo",
    }


def test_draft_facade_routes_patch_alias_to_editing_tools() -> None:
    captured: dict[str, str] = {}

    def patch_draft(**kwargs):
        captured.update(kwargs)
        return "patch-ok"

    funcs = register_draft_facade_tools(
        FastMCP("draft-facade-edit-test"),
        writing_tools={},
        template_tools={},
        editing_tools={"patch_draft": patch_draft},
        citation_tools={},
    )

    result = asyncio.run(
        funcs["draft_action"](
            action="edit",
            filename="intro.md",
            old_text="before",
            content="after",
            project="demo",
        )
    )

    assert result == "patch-ok"
    assert captured == {
        "filename": "intro.md",
        "old_text": "before",
        "new_text": "after",
        "project": "demo",
    }


def test_draft_facade_reports_missing_handler() -> None:
    funcs = register_draft_facade_tools(
        FastMCP("draft-facade-missing-test"),
        writing_tools={},
        template_tools={},
        editing_tools={},
        citation_tools={},
    )

    result = asyncio.run(
        funcs["draft_action"](action="write", filename="intro.md", content="content")
    )

    assert "Draft facade misconfigured" in result


def test_register_draft_tools_is_compact_safe() -> None:
    captured: list[str] = []
    mock_mcp = MagicMock()

    def fake_tool(*args, **kwargs):
        def decorator(handler):
            captured.append(handler.__name__)
            return handler

        return decorator

    mock_mcp.tool = fake_tool

    drafter = MagicMock()
    drafter.ref_manager = MagicMock()

    tool_map = register_draft_tools(mock_mcp, drafter, tool_surface="compact")

    assert captured == ["draft_action"]
    assert "draft_action" in tool_map
    assert "write_draft" in tool_map
    assert "patch_draft" in tool_map
    assert "count_words" in tool_map
