from __future__ import annotations

import asyncio
import inspect
from unittest.mock import MagicMock

import pytest
from docx import Document

from med_paper_assistant.infrastructure.services.template_reader import TemplateReader
from med_paper_assistant.interfaces.mcp.tools.export import word as word_tools
from med_paper_assistant.shared.path_guard import PathGuardError


def _capture_word_tools(tmp_path, monkeypatch, word_writer=None):
    mock_mcp = MagicMock()
    captured = {}

    def fake_tool(*args, **kwargs):
        def decorator(fn):
            if inspect.iscoroutinefunction(fn):

                def sync_wrapper(*wrapper_args, **wrapper_kwargs):
                    return asyncio.run(fn(*wrapper_args, **wrapper_kwargs))

                sync_wrapper.__name__ = fn.__name__
                captured[fn.__name__] = sync_wrapper
            else:
                captured[fn.__name__] = fn
            return fn

        return decorator

    mock_mcp.tool = fake_tool
    monkeypatch.setattr(
        word_tools,
        "resolve_project_context",
        lambda project=None, required_mode="manuscript": (
            {"slug": "demo", "name": "Demo", "paths": {"root": str(tmp_path)}},
            None,
        ),
    )
    funcs = word_tools.register_word_export_tools(
        mock_mcp,
        formatter=MagicMock(),
        template_reader=TemplateReader(str(tmp_path / "templates")),
        word_writer=word_writer or MagicMock(),
    )
    captured.update(funcs)
    return captured


@pytest.mark.parametrize(
    "template_name",
    ["../secret.docx", r"C:\tmp\secret.docx", r"\\server\share\secret.docx", "CON.docx"],
)
def test_word_read_template_rejects_unsafe_template_names(tmp_path, monkeypatch, template_name):
    funcs = _capture_word_tools(tmp_path, monkeypatch)

    result = funcs["read_template"](template_name)

    assert result.startswith("Error: Invalid template name:")


@pytest.mark.parametrize("template_name", ["../secret.docx", "/tmp/secret.docx", "bad\nname.docx"])
def test_start_document_session_rejects_unsafe_template_names(
    tmp_path,
    monkeypatch,
    template_name,
):
    word_writer = MagicMock()
    funcs = _capture_word_tools(tmp_path, monkeypatch, word_writer=word_writer)

    result = funcs["start_document_session"](template_name=template_name, session_id="unsafe")

    assert result.startswith("Error: Invalid template name:")
    word_writer.create_document_from_template.assert_not_called()


def test_save_document_resolves_output_under_project_exports(tmp_path, monkeypatch):
    word_writer = MagicMock()
    word_writer.save_document.side_effect = lambda doc, path: path
    funcs = _capture_word_tools(tmp_path, monkeypatch, word_writer=word_writer)
    word_tools.get_active_documents().clear()
    word_tools.get_active_documents()["safe"] = {
        "doc": Document(),
        "template": "(blank)",
        "modifications": [],
        "project": "demo",
    }

    result = funcs["save_document"](session_id="safe", output_filename="submission")

    expected = tmp_path.resolve() / "exports" / "submission.docx"
    assert "Document saved successfully" in result
    word_writer.save_document.assert_called_once()
    assert word_writer.save_document.call_args.args[1] == str(expected)


@pytest.mark.parametrize("output_filename", ["../escape.docx", r"C:\tmp\escape.docx", "CON.docx"])
def test_save_document_rejects_unsafe_output_filename(tmp_path, monkeypatch, output_filename):
    word_writer = MagicMock()
    funcs = _capture_word_tools(tmp_path, monkeypatch, word_writer=word_writer)
    word_tools.get_active_documents().clear()
    word_tools.get_active_documents()["unsafe"] = {
        "doc": Document(),
        "template": "(blank)",
        "modifications": [],
        "project": "demo",
    }

    result = funcs["save_document"](session_id="unsafe", output_filename=output_filename)

    assert result.startswith("Error: Invalid output filename:")
    word_writer.save_document.assert_not_called()


def test_template_reader_rejects_unsafe_template_name(tmp_path):
    reader = TemplateReader(str(tmp_path))

    with pytest.raises(PathGuardError):
        reader.read_template("../secret.docx")
