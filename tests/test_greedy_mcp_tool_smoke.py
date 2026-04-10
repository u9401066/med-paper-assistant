from __future__ import annotations

import importlib.util
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "greedy_mcp_tool_smoke.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("greedy_mcp_tool_smoke", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load greedy_mcp_tool_smoke.py")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()
SmokeContext = MODULE.SmokeContext
build_tool_arguments = MODULE.build_tool_arguments
build_stable_summary = MODULE.build_stable_summary
classify_call_outcome = MODULE.classify_call_outcome
prepare_project_fixtures = MODULE.prepare_project_fixtures
prioritize_tool_names = MODULE.prioritize_tool_names
serialize_outcome = MODULE.serialize_outcome
should_skip_tool = MODULE.should_skip_tool
summarize_counts = MODULE.summarize_counts
ToolOutcome = MODULE.ToolOutcome


class _FakeResult:
    def __init__(self, *, is_error: bool = False):
        self.isError = is_error


def test_prioritize_tool_names_bootstraps_project_first() -> None:
    names = [
        "validate_concept",
        "list_projects",
        "create_project",
        "project_action",
        "pipeline_action",
        "analyze_dataset",
    ]

    ordered = prioritize_tool_names(names)

    assert ordered[0] == "create_project"
    assert ordered[1] == "project_action"
    assert ordered[2] == "pipeline_action"
    assert ordered.index("project_action") < ordered.index("list_projects")
    assert ordered[-1] == "validate_concept"


def test_build_tool_arguments_uses_context_specific_defaults(tmp_path: Path) -> None:
    context = SmokeContext(workspace_root=tmp_path, project_slug="smoke-project")
    schema = {
        "type": "object",
        "required": ["filename", "project"],
        "properties": {
            "filename": {"type": "string"},
            "project": {"type": "string"},
            "run_novelty_check": {"type": "boolean"},
            "structure_only": {"type": "boolean"},
        },
    }

    args = build_tool_arguments("validate_concept", schema, context)

    assert args == {
        "filename": "concept.md",
        "project": "smoke-project",
        "run_novelty_check": False,
        "structure_only": True,
    }


def test_build_tool_arguments_returns_none_for_unfillable_required_pmid(tmp_path: Path) -> None:
    context = SmokeContext(workspace_root=tmp_path, project_slug="smoke-project")
    schema = {
        "type": "object",
        "required": ["pmid"],
        "properties": {"pmid": {"type": "string"}},
    }

    args = build_tool_arguments("save_reference_mcp", schema, context)

    assert args is None


def test_build_tool_arguments_fills_reference_fixture_defaults(tmp_path: Path) -> None:
    context = SmokeContext(workspace_root=tmp_path, project_slug="smoke-project")
    schema = {
        "type": "object",
        "required": ["filename", "target_text", "pmid", "pdf_content"],
        "properties": {
            "filename": {"type": "string"},
            "target_text": {"type": "string"},
            "pmid": {"type": "string"},
            "pdf_content": {"type": "string"},
        },
    }

    args = build_tool_arguments("insert_citation", schema, context)

    assert args == {
        "filename": "manuscript.md",
        "target_text": "Synthetic CSV data were analyzed.",
        "pmid": "27345583",
        "pdf_content": "JVBERi0xLjQKU21va2UgcGRmIGZpeHR1cmUKJSVFT0Y=",
    }


@pytest.mark.parametrize(
    ("tool_name", "expected_action"),
    [
        ("run_quality_checks", "writing_hooks"),
        ("pipeline_action", "heartbeat"),
        ("project_action", "current"),
        ("workspace_state_action", "get"),
        ("export_document", "session_start"),
        ("inspect_export", "list_templates"),
    ],
)
def test_build_tool_arguments_uses_facade_specific_actions(
    tmp_path: Path,
    tool_name: str,
    expected_action: str,
) -> None:
    context = SmokeContext(workspace_root=tmp_path, project_slug="smoke-project")
    schema = {
        "type": "object",
        "required": ["action"],
        "properties": {"action": {"type": "string"}},
    }

    args = build_tool_arguments(tool_name, schema, context)

    assert args == {"action": expected_action}


def test_should_skip_tool_marks_external_reference_tools() -> None:
    schema = {"type": "object", "required": ["pmid"], "properties": {}}

    decision = should_skip_tool("save_reference_mcp", schema)

    assert decision is not None
    assert decision.category == "external"
    assert decision.reason == "requires live PubMed/network metadata"


def test_should_skip_tool_marks_elicitation_only_tool() -> None:
    decision = should_skip_tool("setup_project_interactive", {"type": "object"})

    assert decision is not None
    assert decision.category == "interactive"
    assert decision.reason == "requires an elicitation-capable MCP client"


def test_classify_call_outcome_distinguishes_precondition_from_broken() -> None:
    precondition_status, _ = classify_call_outcome(
        _FakeResult(is_error=False),
        "❌ Error: Concept file not found: concept.md",
    )
    broken_status, _ = classify_call_outcome(
        _FakeResult(is_error=True),
        "internal exception",
    )

    assert precondition_status == "precondition"
    assert broken_status == "broken"


def test_summarize_counts_tallies_statuses() -> None:
    outcomes = [
        ToolOutcome("a", "ok", ""),
        ToolOutcome("b", "skipped", "", skip_category="interactive"),
        ToolOutcome("c", "skipped", "", skip_category="external"),
        ToolOutcome("d", "skipped", "", skip_category="other"),
        ToolOutcome("e", "broken", ""),
    ]

    counts = summarize_counts(outcomes)

    assert counts["total"] == 5
    assert counts["ok"] == 1
    assert counts["skipped"] == 3
    assert counts["skipped_interactive"] == 1
    assert counts["skipped_external"] == 1
    assert counts["skipped_other"] == 1
    assert counts["broken"] == 1


def test_build_stable_summary_is_ci_friendly_and_splits_skip_categories(tmp_path: Path) -> None:
    workspace_root = tmp_path / "temp-workspace"
    args = SimpleNamespace(match="", limit=0, stop_on="broken")
    outcomes = [
        ToolOutcome("create_project", "ok", "created"),
        ToolOutcome(
            "setup_project_interactive",
            "skipped",
            "requires an elicitation-capable MCP client",
            skip_category="interactive",
        ),
        ToolOutcome(
            "save_reference_mcp",
            "skipped",
            "requires live PubMed/network metadata",
            skip_category="external",
        ),
        ToolOutcome("validate_concept", "precondition", f"Concept file not found: {workspace_root}\\concept.md"),
    ]

    counts = summarize_counts(outcomes)
    summary = build_stable_summary(outcomes, counts, args, workspace_root, "temporary")

    assert summary["summary_format"] == "greedy-smoke-summary-v1"
    assert summary["workspace_mode"] == "temporary"
    assert summary["counts"]["skipped_external"] == 1
    assert summary["counts"]["skipped_interactive"] == 1
    assert summary["grouped_tools"]["skipped"]["interactive"] == ["setup_project_interactive"]
    assert summary["grouped_tools"]["skipped"]["external"] == ["save_reference_mcp"]
    assert summary["execution"][1] == {
        "tool": "setup_project_interactive",
        "status": "skipped",
        "skip_category": "interactive",
        "detail": "requires an elicitation-capable MCP client",
    }
    assert summary["execution"][3]["detail"] == "Concept file not found: <workspace>/concept.md"


def test_serialize_outcome_includes_skip_category_only_for_skips() -> None:
    skipped_outcome = ToolOutcome("tool", "skipped", "later", skip_category="external")
    ok_outcome = ToolOutcome("tool", "ok", "done", {"project": "demo"})

    skipped_payload = serialize_outcome(skipped_outcome)
    ok_payload = serialize_outcome(ok_outcome)

    assert skipped_payload["skip_category"] == "external"
    assert "skip_category" not in ok_payload


def test_serialize_outcome_supports_slots_dataclass() -> None:
    outcome = ToolOutcome("tool", "ok", "done", {"project": "demo"})

    payload = serialize_outcome(outcome)

    assert payload == {
        "name": "tool",
        "status": "ok",
        "detail": "done",
        "arguments": {"project": "demo"},
    }


def test_prepare_project_fixtures_creates_reference_and_draft_assets(tmp_path: Path) -> None:
    context = SmokeContext(
        workspace_root=tmp_path,
        project_slug="smoke-project",
        project_path=tmp_path / "projects" / "smoke-project",
    )

    prepare_project_fixtures(context)

    draft_path = context.project_path / "drafts" / "manuscript.md"
    metadata_path = context.project_path / "references" / "27345583" / "metadata.json"
    note_path = context.project_path / "references" / "27345583" / "greer2017_27345583.md"

    assert draft_path.exists()
    assert "Synthetic CSV data were analyzed." in draft_path.read_text(encoding="utf-8")
    assert metadata_path.exists()
    assert '"citation_key": "greer2017_27345583"' in metadata_path.read_text(encoding="utf-8")
    assert note_path.exists()


