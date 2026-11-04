"""Regression tests for the P1 interface audit fixes (IFACE-1/2/4/5/6/7/9/10/14/15, DOM-14)."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest
import yaml
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from med_paper_assistant.infrastructure.persistence.project_manager import ProjectManager
from med_paper_assistant.infrastructure.services import pandoc_runner
from med_paper_assistant.infrastructure.services.pandoc_runner import (
    PandocTimeoutError,
    build_pandoc_args,
    pandoc_timeout_seconds,
    run_pandoc,
)
from med_paper_assistant.interfaces.mcp.tool_surface import resolve_tool_surface
from med_paper_assistant.interfaces.mcp.tools._shared.tool_errors import (
    enable_failure_errors,
    raise_for_failure,
)
from med_paper_assistant.interfaces.mcp.tools.export.export_inputs import (
    entry_title,
    require_drafts_dir,
    resolve_export_csl,
    resolve_export_reference_doc,
)
from med_paper_assistant.interfaces.mcp.tools.project import vscode_launcher
from med_paper_assistant.interfaces.mcp.tools.project.facade import (
    project_inline as project_facade,
)
from med_paper_assistant.interfaces.mcp.tools.project.facade import register_project_facade_tools
from med_paper_assistant.interfaces.mcp.tools.project.library_notes import (
    register_library_note_tools,
)
from med_paper_assistant.interfaces.mcp.tools.project.workspace import register_workspace_tools
from med_paper_assistant.shared.path_guard import PathGuardError
from med_paper_assistant.shared.yaml_escape import escape_yaml_value

# --------------------------------------------------------------------------- IFACE-1


@pytest.mark.asyncio
async def test_iface1_failure_string_becomes_tool_error_only_at_server_boundary() -> None:
    mcp = enable_failure_errors(MCPServer("iface1"))

    @mcp.tool()
    def failing(x: int = 1) -> str:
        return "❌ Something went wrong"

    @mcp.tool()
    async def async_failing() -> str:
        return "  ❌ async failure"

    @mcp.tool()
    def succeeding() -> str:
        return "✅ fine"

    # Direct calls keep returning the plain string.
    assert failing() == "❌ Something went wrong"

    with pytest.raises(ToolError, match="Something went wrong"):
        await mcp.call_tool("failing", {})
    with pytest.raises(ToolError, match="async failure"):
        await mcp.call_tool("async_failing", {})

    ok = await mcp.call_tool("succeeding", {})
    assert "fine" in str(ok)


@pytest.mark.asyncio
async def test_iface1_error_reported_with_is_error_flag() -> None:
    mcp = enable_failure_errors(MCPServer("iface1-flag"))

    @mcp.tool()
    def failing() -> str:
        return "❌ nope"

    result = await mcp._handle_call_tool(  # noqa: SLF001 - protocol-level check
        None,  # type: ignore[arg-type]
        type("Params", (), {"name": "failing", "arguments": {}})(),  # type: ignore[arg-type]
    )
    assert result.is_error is True
    assert "nope" in result.content[0].text  # type: ignore[union-attr]


def test_iface1_raise_for_failure_passes_non_failures() -> None:
    assert raise_for_failure("✅ ok") == "✅ ok"
    assert raise_for_failure({"status": "error"}) == {"status": "error"}
    with pytest.raises(ToolError):
        raise_for_failure("❌ bad")


# --------------------------------------------------------------------------- IFACE-2


def test_iface2_missing_code_cli_returns_clear_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vscode_launcher.shutil, "which", lambda name: None)
    launch = vscode_launcher.open_files_in_vscode(["a.md"])
    assert launch.cli is None and not launch.opened
    report = vscode_launcher.render_launch_report("Demo", ["a.md"], [], launch)
    assert "❌ VS Code CLI" in report
    assert "a.md" in report


def test_iface2_launch_does_not_block_on_running_editor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vscode_launcher.shutil, "which", lambda name: "C:\\fake\\code.cmd")
    seen: dict[str, object] = {}

    class FakeProc:
        def wait(self, timeout: float) -> int:
            seen["timeout"] = timeout
            raise subprocess.TimeoutExpired("code", timeout)

    def fake_popen(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["kwargs"] = kwargs
        return FakeProc()

    monkeypatch.setattr(vscode_launcher.subprocess, "Popen", fake_popen)
    launch = vscode_launcher.open_files_in_vscode(["a.md"], wait_seconds=0.5)

    assert launch.opened == ["a.md"] and not launch.failed
    assert seen["timeout"] == 0.5
    assert seen["cmd"] == ["C:\\fake\\code.cmd", "--goto", "a.md"]
    assert "shell" not in seen["kwargs"]  # type: ignore[operator]


def test_iface2_nonzero_exit_and_oserror_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vscode_launcher.shutil, "which", lambda name: "code")

    class Failing:
        def wait(self, timeout: float) -> int:
            return 3

    def fake_popen(cmd, **kwargs):
        if cmd[-1] == "boom.md":
            raise OSError("cannot start")
        return Failing()

    monkeypatch.setattr(vscode_launcher.subprocess, "Popen", fake_popen)
    launch = vscode_launcher.open_files_in_vscode(["x.md", "boom.md"])
    assert "status 3" in launch.failed["x.md"]
    assert "cannot start" in launch.failed["boom.md"]


@pytest.mark.asyncio
async def test_iface2_open_project_files_reports_missing_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_dir = tmp_path / "projects" / "demo"
    project_dir.mkdir(parents=True)
    (project_dir / "concept.md").write_text("# Concept", encoding="utf-8")

    class FakePM:
        projects_dir = tmp_path / "projects"

        @staticmethod
        def get_current_project() -> str:
            return "demo"

        @staticmethod
        def get_project_info(slug: str) -> dict[str, object]:
            return {"success": True, "slug": slug, "name": "Demo", "project_path": str(project_dir)}

    monkeypatch.setattr(vscode_launcher.shutil, "which", lambda name: None)
    tools = register_workspace_tools(MCPServer("iface2"), FakePM())
    result = await tools["open_project_files"]()
    assert "VS Code CLI" in result and "concept.md" in result


# --------------------------------------------------------------------------- IFACE-4 / DOM-14 inputs


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ws = tmp_path / "ws"
    (ws / "projects" / "demo").mkdir(parents=True)
    monkeypatch.setenv("MEDPAPER_BASE_DIR", str(ws))
    return ws


class _NoCslExporter:
    @staticmethod
    def resolve_csl(csl: str | None) -> str | None:
        return None


def test_iface4_contained_csl_and_reference_doc_accepted(workspace: Path) -> None:
    project_dir = workspace / "projects" / "demo"
    csl = project_dir / "style.csl"
    csl.write_text("<style/>", encoding="utf-8")
    ref = workspace / "ref.docx"
    ref.write_bytes(b"PK")

    assert resolve_export_csl(str(csl), _NoCslExporter(), project_dir) == str(csl.resolve())
    assert resolve_export_reference_doc("", project_dir) is None
    assert resolve_export_reference_doc(str(ref), project_dir) == str(ref.resolve())


@pytest.mark.parametrize(
    "bad",
    ["\\\\evil\\share\\x.csl", "//evil/share/x.csl", "..\\..\\x.csl", "../x.csl", "a.csl:stream"],
)
def test_iface4_unc_traversal_and_streams_rejected(workspace: Path, bad: str) -> None:
    with pytest.raises(PathGuardError):
        resolve_export_csl(bad, _NoCslExporter(), workspace / "projects" / "demo")
    with pytest.raises(PathGuardError):
        resolve_export_reference_doc(bad, workspace / "projects" / "demo")


def test_iface4_path_outside_workspace_rejected(workspace: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside.csl"
    outside.write_text("<style/>", encoding="utf-8")
    with pytest.raises(PathGuardError, match="inside the workspace"):
        resolve_export_csl(str(outside), _NoCslExporter(), workspace / "projects" / "demo")
    doc = tmp_path / "outside.docx"
    doc.write_bytes(b"PK")
    with pytest.raises(PathGuardError):
        resolve_export_reference_doc(str(doc), workspace / "projects" / "demo")


def test_iface4_wrong_suffix_and_missing_file(workspace: Path) -> None:
    project_dir = workspace / "projects" / "demo"
    (project_dir / "notes.txt").write_text("x", encoding="utf-8")
    with pytest.raises(PathGuardError, match="must use one of"):
        resolve_export_reference_doc(str(project_dir / "notes.txt"), project_dir)
    with pytest.raises(FileNotFoundError):
        resolve_export_reference_doc("missing.docx", project_dir)
    with pytest.raises(FileNotFoundError):
        resolve_export_csl("missing.csl", _NoCslExporter(), project_dir)


def test_dom14_unknown_csl_name_is_explicit_error(workspace: Path) -> None:
    with pytest.raises(FileNotFoundError, match="not found"):
        resolve_export_csl("no-such-style", _NoCslExporter(), workspace / "projects" / "demo")


# --------------------------------------------------------------------------- DOM-14 runner


def test_dom14_pandoc_timeout_raises_dedicated_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pandoc_runner.pypandoc, "get_pandoc_path", lambda: "pandoc")
    seen: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        seen.update(kwargs)
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(pandoc_runner.subprocess, "run", fake_run)
    monkeypatch.setenv("MEDPAPER_PANDOC_TIMEOUT", "7")

    with pytest.raises(PandocTimeoutError, match="7s"):
        run_pandoc("# x", "docx", source_format="markdown", output_file=None, extra_args=[])
    assert seen["timeout"] == 7.0


def test_dom14_timeout_env_falls_back_on_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEDPAPER_PANDOC_TIMEOUT", "not-a-number")
    assert pandoc_timeout_seconds() == pandoc_runner.DEFAULT_PANDOC_TIMEOUT_SECONDS
    monkeypatch.setenv("MEDPAPER_PANDOC_TIMEOUT", "-5")
    assert pandoc_timeout_seconds() == pandoc_runner.DEFAULT_PANDOC_TIMEOUT_SECONDS


def test_dom14_nonzero_exit_includes_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pandoc_runner.pypandoc, "get_pandoc_path", lambda: "pandoc")
    monkeypatch.setattr(
        pandoc_runner.subprocess,
        "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 4, b"", b"bad csl"),
    )
    with pytest.raises(RuntimeError, match="bad csl"):
        run_pandoc("x", "docx", source_format="markdown", output_file=None, extra_args=[])


def test_dom14_missing_reference_doc_and_csl_raise(tmp_path: Path) -> None:
    common = {
        "bibliography": None,
        "extra_args": None,
        "filters": None,
    }
    with pytest.raises(FileNotFoundError, match="Reference document"):
        build_pandoc_args(
            reference_doc=str(tmp_path / "nope.docx"), csl=None, resolve_csl=lambda c: c, **common
        )
    with pytest.raises(FileNotFoundError, match="CSL style"):
        build_pandoc_args(reference_doc=None, csl="ghost", resolve_csl=lambda c: None, **common)
    with pytest.raises(ValueError, match="UNC"):
        build_pandoc_args(
            reference_doc="\\\\host\\share\\t.docx", csl=None, resolve_csl=lambda c: c, **common
        )
    with pytest.raises(FileNotFoundError, match="Bibliography"):
        build_pandoc_args(
            reference_doc=None,
            csl=None,
            resolve_csl=lambda c: c,
            bibliography=str(tmp_path / "x.json"),
            extra_args=None,
            filters=None,
        )


def test_dom14_build_args_happy_path(tmp_path: Path) -> None:
    ref = tmp_path / "ref.docx"
    ref.write_bytes(b"PK")
    csl = tmp_path / "s.csl"
    csl.write_text("<style/>", encoding="utf-8")
    bib = tmp_path / "b.json"
    bib.write_text("[]", encoding="utf-8")
    args = build_pandoc_args(
        reference_doc=str(ref),
        csl="s",
        bibliography=str(bib),
        extra_args=None,
        filters=None,
        resolve_csl=lambda c: str(csl),
    )
    assert args[:2] == ["--reference-doc", str(ref)]
    assert "--csl" in args and "--citeproc" in args and "--standalone" in args


# --------------------------------------------------------------------------- IFACE-5 / IFACE-6


def _project_facade(monkeypatch: pytest.MonkeyPatch, project_dir: Path, name: str):
    def fake_resolve_project_context(project=None, **kwargs):
        return (
            {
                "slug": "demo",
                "name": "Demo",
                "project_path": str(project_dir),
                "target_journal": "BJA",
                "paper_type": "original-research",
            },
            None,
        )

    monkeypatch.setattr(project_facade, "resolve_project_context", fake_resolve_project_context)
    return register_project_facade_tools(
        MCPServer(name),
        crud_tools={},
        settings_tools={},
        exploration_tools={},
        workspace_state_tools={},
    )


@pytest.mark.asyncio
async def test_iface5_source_dir_outside_workspace_rejected(
    workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_dir = workspace / "projects" / "demo"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.docx").write_text("x", encoding="utf-8")
    funcs = _project_facade(monkeypatch, project_dir, "iface5")

    for bad in (str(outside), "..\\outside", "\\\\evil\\share\\data"):
        result = await funcs["project_action"](action="source_materials", source_dir=bad)
        assert result.startswith("❌"), bad
    assert not (project_dir / ".audit" / "source-materials.yaml").exists()


@pytest.mark.asyncio
async def test_iface5_source_dir_inside_workspace_accepted(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_dir = workspace / "projects" / "demo"
    (project_dir / ".audit").mkdir()
    data_dir = workspace / "raw"
    data_dir.mkdir()
    (data_dir / "table.docx").write_text("x", encoding="utf-8")
    funcs = _project_facade(monkeypatch, project_dir, "iface5-ok")

    result = await funcs["project_action"](action="source_materials", source_dir="raw")
    assert "status: ok" in result
    assert "pending_asset_aware: 1" in result


@pytest.mark.asyncio
async def test_iface6_journal_profile_not_overwritten_without_confirm(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_dir = workspace / "projects" / "demo"
    profile = project_dir / "journal-profile.yaml"
    profile.write_text("journal:\n  name: Hand edited\n", encoding="utf-8")
    funcs = _project_facade(monkeypatch, project_dir, "iface6")

    refused = await funcs["project_action"](action="journal_profile", target_journal="BJA")
    assert refused.startswith("❌") and "already exists" in refused
    assert profile.read_text(encoding="utf-8") == "journal:\n  name: Hand edited\n"

    ok = await funcs["project_action"](action="journal_profile", target_journal="BJA", confirm=True)
    assert "status: ok" in ok
    assert yaml.safe_load(profile.read_text(encoding="utf-8"))["journal"]["name"] == "BJA"


@pytest.mark.asyncio
async def test_iface6_first_write_needs_no_confirm(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_dir = workspace / "projects" / "demo"
    funcs = _project_facade(monkeypatch, project_dir, "iface6-new")
    result = await funcs["project_action"](action="journal_profile", target_journal="BJA")
    assert "status: ok" in result
    assert (project_dir / "journal-profile.yaml").is_file()


# --------------------------------------------------------------------------- IFACE-7


@pytest.mark.asyncio
async def test_iface7_materialize_keeps_caller_source_notes() -> None:
    captured: dict[str, object] = {}

    def materialize_concept_page(**kwargs):
        captured.update(kwargs)
        return "ok"

    funcs = register_project_facade_tools(
        MCPServer("iface7"),
        crud_tools={},
        settings_tools={},
        exploration_tools={},
        workspace_state_tools={},
        library_tools={"materialize_concept_page": materialize_concept_page},
    )
    await funcs["library_action"](
        action="materialize_concept",
        filename="my-concept",
        source_notes_csv="inbox:a,inbox:b",
    )
    assert captured["source_notes_csv"] == "inbox:a,inbox:b"
    assert captured["filename"] == "my-concept"

    captured.clear()
    await funcs["library_action"](action="materialize_concept", filename="my-concept")
    assert captured["source_notes_csv"] != "my-concept"


# --------------------------------------------------------------------------- IFACE-9


def _library(tmp_path: Path, name: str):
    pm = ProjectManager(base_path=str(tmp_path))
    pm.create_project(name="Library", workflow_mode="library-wiki")
    return pm, register_library_note_tools(MCPServer(name), pm)


def test_iface9_case_conflict_returns_clean_error(tmp_path: Path) -> None:
    _, funcs = _library(tmp_path, "iface9-case")
    first = funcs["write_library_note"](section="inbox", filename="Note-A", content="one")
    assert "created successfully" in first
    second = funcs["write_library_note"](section="inbox", filename="note-a", content="two")
    assert second.startswith("❌")
    assert "Traceback" not in second


def test_iface9_path_traversal_returns_clean_error(tmp_path: Path) -> None:
    _, funcs = _library(tmp_path, "iface9-trav")
    result = funcs["write_library_note"](section="inbox", filename="../../evil", content="x")
    assert result.startswith("❌")
    assert not (tmp_path / "evil.md").exists()


def test_iface9_read_only_tools_do_not_create_directories(tmp_path: Path) -> None:
    import shutil

    _, funcs = _library(tmp_path, "iface9-ro")
    daily = tmp_path / "projects" / "library" / "daily"
    if daily.exists():
        shutil.rmtree(daily)

    listing = funcs["list_library_notes"](section="daily")
    assert isinstance(listing, str)
    assert not daily.exists()
    read = funcs["read_library_note"](section="daily", filename="nothing")
    assert isinstance(read, str)
    assert not daily.exists()
    funcs["search_library_notes"](query="anything", section="daily")
    assert not daily.exists()


# --------------------------------------------------------------------------- IFACE-10


@pytest.mark.parametrize(
    "value",
    [
        'a"\nevil: 1',
        "line1\r\nline2: x",
        "tab\tsep",
        "nul\x00byte",
        "sep\u2028next: 1",
        "back\\slash\" and 'quote'",
        "\x85nel",
    ],
)
def test_iface10_escaped_values_round_trip_without_key_injection(value: str) -> None:
    document = f'title: "{escape_yaml_value(value)}"\nstatus: "inbox"\n'
    loaded = yaml.safe_load(document)
    assert set(loaded) == {"title", "status"}
    assert loaded["title"] == value


# --------------------------------------------------------------------------- IFACE-14


def test_iface14_unknown_surface_logs_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("MEDPAPER_TOOL_SURFACE", "ful")
    with caplog.at_level(logging.WARNING):
        assert resolve_tool_surface() == "compact"
    assert any("MEDPAPER_TOOL_SURFACE" in rec.getMessage() for rec in caplog.records)


@pytest.mark.parametrize(
    "value,expected", [("full", "full"), ("compact", "compact"), ("", "compact")]
)
def test_iface14_valid_surface_values_do_not_warn(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    value: str,
    expected: str,
) -> None:
    monkeypatch.setenv("MEDPAPER_TOOL_SURFACE", value)
    with caplog.at_level(logging.WARNING):
        assert resolve_tool_surface() == expected
    assert not caplog.records
    assert capsys.readouterr().out == ""


# --------------------------------------------------------------------------- IFACE-15


def test_iface15_entry_title_tolerates_null_title() -> None:
    assert entry_title({"title": None}) == "Unknown"
    assert entry_title({}) == "Unknown"
    assert entry_title({"title": "x" * 200}) == "x" * 80


def test_iface15_drafts_dir_must_be_absolute(tmp_path: Path) -> None:
    with pytest.raises(PathGuardError):
        require_drafts_dir({})
    with pytest.raises(PathGuardError):
        require_drafts_dir({"drafts": "drafts"})
    assert require_drafts_dir({"drafts": str(tmp_path / "drafts")}) == str(tmp_path / "drafts")
