"""Tests for the ``constraint_action`` MCP tool (review/constraint.py).

These cover the *dispatch / wrapping* layer that exposes ConstraintLedger as a
single facade-style MCP tool. The ledger semantics themselves live in
``test_constraint_ledger.py``; here we verify argument handling, action
routing, error surfaces, and that nothing ever raises out of the tool.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from med_paper_assistant.infrastructure.persistence.constraint_ledger import ConstraintLedger
from med_paper_assistant.interfaces.mcp.tools.review.constraint import (
    register_constraint_tools,
)

_KEY_RE = re.compile(r"key:\s*(c_[0-9a-f]{12})")


def _mock_project_context(project_dir: Path):
    """Patch resolve_project_context in the constraint module to always succeed."""
    project_info = {
        "slug": "test-project",
        "name": "Test Project",
        "project_path": str(project_dir),
        "success": True,
    }
    return patch(
        "med_paper_assistant.interfaces.mcp.tools.review.constraint.resolve_project_context",
        return_value=(project_info, None),
    )


@pytest.fixture
def project_dir(tmp_path):
    p = tmp_path / "test-project"
    (p / ".audit").mkdir(parents=True)
    return p


@pytest.fixture
def constraint_action(project_dir):
    """Return the registered constraint_action handler (no real MCP needed)."""
    funcs = register_constraint_tools(MagicMock(), register_public_verbs=False)
    return funcs["constraint_action"]


def _add(fn, project_dir, **kwargs) -> str:
    """Helper: add a constraint and return its key."""
    defaults = {
        "action": "add",
        "source": "P7",
        "description": "Malformed DOI",
        "project": "test-project",
    }
    defaults.update(kwargs)
    with _mock_project_context(project_dir):
        result = fn(**defaults)
    match = _KEY_RE.search(result)
    assert match, f"expected a key in: {result}"
    return match.group(1)


# ── registration ──────────────────────────────────────────────────────


def test_register_returns_single_tool():
    funcs = register_constraint_tools(MagicMock(), register_public_verbs=False)
    assert set(funcs) == {"constraint_action"}
    assert callable(funcs["constraint_action"])


# ── read actions (smoke-safe defaults) ──────────────────────────────────


def test_status_is_default_and_read_only(constraint_action, project_dir):
    """Bare invocation (smoke test path) returns ledger status, never an error."""
    with _mock_project_context(project_dir):
        result = constraint_action(project="test-project")
    assert "❌" not in result
    # No ledger file should be created by a pure read.
    assert not (project_dir / ".audit" / ConstraintLedger.LEDGER_FILE).is_file()


@pytest.mark.parametrize("action", ["status", "summary", "list", "report", "markdown"])
def test_all_read_actions_succeed(constraint_action, project_dir, action):
    with _mock_project_context(project_dir):
        result = constraint_action(action=action, project="test-project")
    assert isinstance(result, str)
    assert "❌" not in result


@pytest.mark.parametrize("action", ["help", "actions", "supported"])
def test_help_lists_supported_actions(constraint_action, project_dir, action):
    with _mock_project_context(project_dir):
        result = constraint_action(action=action, project="test-project")
    assert result.startswith("supported_actions:")
    for verb in ("add", "satisfy", "waive", "reopen", "ingest", "status"):
        assert verb in result


# ── add ─────────────────────────────────────────────────────────────────


def test_add_records_constraint(constraint_action, project_dir):
    with _mock_project_context(project_dir):
        result = constraint_action(
            action="add",
            source="P7",
            description="Malformed DOI on smith2024",
            severity="critical",
            project="test-project",
        )
    assert "✅ Constraint recorded" in result
    assert "severity: CRITICAL" in result  # normalized to upper
    assert _KEY_RE.search(result)


def test_add_requires_source_and_description(constraint_action, project_dir):
    with _mock_project_context(project_dir):
        missing_desc = constraint_action(action="add", source="P7", project="test-project")
        missing_src = constraint_action(
            action="add", description="something", project="test-project"
        )
    assert "❌" in missing_desc and "requires both source and description" in missing_desc
    assert "❌" in missing_src


def test_add_is_idempotent(constraint_action, project_dir):
    key1 = _add(constraint_action, project_dir)
    key2 = _add(constraint_action, project_dir)
    assert key1 == key2


# ── lifecycle transitions ───────────────────────────────────────────────


def test_satisfy_marks_converged(constraint_action, project_dir):
    key = _add(constraint_action, project_dir)
    with _mock_project_context(project_dir):
        result = constraint_action(
            action="satisfy", key=key, reason="fixed DOI", project="test-project"
        )
    assert "✅ Constraint satisfied" in result
    assert "converged: True" in result


def test_satisfy_requires_key(constraint_action, project_dir):
    with _mock_project_context(project_dir):
        result = constraint_action(action="satisfy", project="test-project")
    assert "❌" in result and "requires a constraint key" in result


def test_satisfy_unknown_key(constraint_action, project_dir):
    with _mock_project_context(project_dir):
        result = constraint_action(action="satisfy", key="c_000000000000", project="test-project")
    assert "❌ No constraint found" in result


def test_waive_requires_reason(constraint_action, project_dir):
    key = _add(constraint_action, project_dir)
    with _mock_project_context(project_dir):
        result = constraint_action(action="waive", key=key, project="test-project")
    assert "❌" in result and "requires a reason" in result


def test_waive_with_reason_succeeds(constraint_action, project_dir):
    key = _add(constraint_action, project_dir)
    with _mock_project_context(project_dir):
        result = constraint_action(
            action="waive", key=key, reason="accepted risk", project="test-project"
        )
    assert "✅ Constraint waived" in result
    assert "converged: True" in result


def test_reopen_requires_reason(constraint_action, project_dir):
    key = _add(constraint_action, project_dir)
    with _mock_project_context(project_dir):
        constraint_action(action="satisfy", key=key, reason="fixed", project="test-project")
        result = constraint_action(action="reopen", key=key, project="test-project")
    assert "❌" in result and "requires a reason" in result


def test_reopen_after_satisfy(constraint_action, project_dir):
    key = _add(constraint_action, project_dir)
    with _mock_project_context(project_dir):
        constraint_action(action="satisfy", key=key, reason="fixed", project="test-project")
        result = constraint_action(
            action="reopen", key=key, reason="regressed in edit", project="test-project"
        )
    assert "✅ Constraint reopened" in result
    assert "converged: False" in result


# ── ingest ───────────────────────────────────────────────────────────────


def test_ingest_valid_issues(constraint_action, project_dir):
    issues = (
        '[{"hook_id": "B13", "severity": "WARNING", "section": "Discussion", '
        '"message": "Missing limitations paragraph"}]'
    )
    with _mock_project_context(project_dir):
        result = constraint_action(action="ingest", issues=issues, project="test-project")
    assert "✅ Ingested 1 new constraint" in result


def test_ingest_invalid_json(constraint_action, project_dir):
    with _mock_project_context(project_dir):
        result = constraint_action(action="ingest", issues="{not json", project="test-project")
    assert "❌" in result and "valid JSON array" in result


def test_ingest_non_list_json(constraint_action, project_dir):
    with _mock_project_context(project_dir):
        result = constraint_action(
            action="ingest", issues='{"hook_id": "B13"}', project="test-project"
        )
    assert "❌" in result and "JSON array" in result


def test_ingest_empty_is_noop(constraint_action, project_dir):
    with _mock_project_context(project_dir):
        result = constraint_action(action="ingest", issues="", project="test-project")
    assert "✅ Ingested 0 new constraint" in result


# ── error surfaces ─────────────────────────────────────────────────────────


def test_unsupported_action(constraint_action, project_dir):
    with _mock_project_context(project_dir):
        result = constraint_action(action="frobnicate", project="test-project")
    assert "❌ Unsupported action" in result


def test_workflow_error_is_returned(constraint_action, project_dir):
    """If resolve_project_context returns an error string, it is surfaced verbatim."""
    with patch(
        "med_paper_assistant.interfaces.mcp.tools.review.constraint.resolve_project_context",
        return_value=(None, "❌ No active project. Run create_project first."),
    ):
        result = constraint_action(action="status")
    assert result == "❌ No active project. Run create_project first."
