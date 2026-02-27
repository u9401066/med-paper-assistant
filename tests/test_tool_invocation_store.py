"""Tests for ToolInvocationStore — workspace-level MCP tool telemetry."""

from pathlib import Path

import pytest
import yaml

from med_paper_assistant.infrastructure.persistence.tool_invocation_store import (
    ToolInvocationStore,
)

# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture()
def store(workspace: Path) -> ToolInvocationStore:
    return ToolInvocationStore(workspace)


# ── First-run / file creation ─────────────────────────────────────────


def test_first_run_no_audit_dir(store: ToolInvocationStore, workspace: Path) -> None:
    """On first run .audit/ does not exist — created on first save."""
    assert not (workspace / ".audit").exists()
    store.record_invocation("write_draft")
    assert (workspace / ".audit" / ToolInvocationStore.DATA_FILE).is_file()


def test_fresh_store_get_all_stats_empty(store: ToolInvocationStore) -> None:
    """Empty store returns empty stats without error."""
    assert store.get_all_stats() == {}


def test_fresh_store_get_tool_stats_missing(store: ToolInvocationStore) -> None:
    """Querying unknown tool returns empty dict."""
    assert store.get_tool_stats("nonexistent") == {}


# ── record_invocation ─────────────────────────────────────────────────


def test_record_invocation_increments(store: ToolInvocationStore) -> None:
    store.record_invocation("write_draft")
    store.record_invocation("write_draft")
    assert store.get_tool_stats("write_draft")["invocation_count"] == 2


def test_record_invocation_initialises_all_counters(store: ToolInvocationStore) -> None:
    store.record_invocation("new_tool")
    stats = store.get_tool_stats("new_tool")
    assert stats["success_count"] == 0
    assert stats["error_count"] == 0
    assert stats["misuse_count"] == 0
    assert stats["error_types"] == []


# ── record_success ────────────────────────────────────────────────────


def test_record_success_increments(store: ToolInvocationStore) -> None:
    store.record_invocation("tool_a")
    store.record_success("tool_a")
    assert store.get_tool_stats("tool_a")["success_count"] == 1


def test_record_success_without_prior_invocation(store: ToolInvocationStore) -> None:
    """record_success works even if record_invocation was not called first."""
    store.record_success("tool_b")
    assert store.get_tool_stats("tool_b")["success_count"] == 1


# ── record_error ──────────────────────────────────────────────────────


def test_record_error_increments_count(store: ToolInvocationStore) -> None:
    store.record_error("tool_c", "ValueError")
    assert store.get_tool_stats("tool_c")["error_count"] == 1


def test_record_error_deduplicates_type(store: ToolInvocationStore) -> None:
    store.record_error("tool_d", "ValueError")
    store.record_error("tool_d", "ValueError")  # same type twice
    stats = store.get_tool_stats("tool_d")
    assert stats["error_count"] == 2
    assert stats["error_types"] == ["ValueError"]


def test_record_error_accumulates_distinct_types(store: ToolInvocationStore) -> None:
    store.record_error("tool_e", "ValueError")
    store.record_error("tool_e", "TypeError")
    stats = store.get_tool_stats("tool_e")
    assert stats["error_count"] == 2
    assert set(stats["error_types"]) == {"ValueError", "TypeError"}


def test_record_error_without_type(store: ToolInvocationStore) -> None:
    store.record_error("tool_f")
    stats = store.get_tool_stats("tool_f")
    assert stats["error_count"] == 1
    assert stats["error_types"] == []


# ── record_misuse ─────────────────────────────────────────────────────


def test_record_misuse_increments(store: ToolInvocationStore) -> None:
    store.record_misuse("tool_g")
    assert store.get_tool_stats("tool_g")["misuse_count"] == 1


def test_record_misuse_multiple(store: ToolInvocationStore) -> None:
    for _ in range(3):
        store.record_misuse("list_projects")
    assert store.get_tool_stats("list_projects")["misuse_count"] == 3


# ── Persistence ───────────────────────────────────────────────────────


def test_persistence_survives_new_instance(workspace: Path) -> None:
    """Data written by one instance must be readable by a new instance."""
    s1 = ToolInvocationStore(workspace)
    s1.record_invocation("persistent_tool")
    s1.record_success("persistent_tool")

    s2 = ToolInvocationStore(workspace)
    stats = s2.get_tool_stats("persistent_tool")
    assert stats["invocation_count"] == 1
    assert stats["success_count"] == 1


def test_data_file_is_valid_yaml(workspace: Path) -> None:
    store = ToolInvocationStore(workspace)
    store.record_invocation("some_tool")
    raw = (workspace / ".audit" / ToolInvocationStore.DATA_FILE).read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    assert "version" in data
    assert "tools" in data


def test_data_file_has_updated_at(workspace: Path) -> None:
    store = ToolInvocationStore(workspace)
    store.record_invocation("x")
    raw = yaml.safe_load(
        (workspace / ".audit" / ToolInvocationStore.DATA_FILE).read_text(encoding="utf-8")
    )
    assert "updated_at" in raw


# ── get_all_stats ─────────────────────────────────────────────────────


def test_get_all_stats_returns_all_tools(store: ToolInvocationStore) -> None:
    store.record_invocation("tool_1")
    store.record_invocation("tool_2")
    stats = store.get_all_stats()
    assert "tool_1" in stats
    assert "tool_2" in stats


# ── get_zero_invocation_tools ─────────────────────────────────────────


def test_zero_invocation_tools_excludes_called_tools(store: ToolInvocationStore) -> None:
    store.record_invocation("called_tool")
    result = store.get_zero_invocation_tools(["called_tool", "never_called"])
    assert "never_called" in result
    assert "called_tool" not in result


def test_zero_invocation_tools_all_zero(store: ToolInvocationStore) -> None:
    result = store.get_zero_invocation_tools(["a", "b", "c"])
    assert set(result) == {"a", "b", "c"}


def test_zero_invocation_tools_all_called(store: ToolInvocationStore) -> None:
    for t in ["x", "y"]:
        store.record_invocation(t)
    assert store.get_zero_invocation_tools(["x", "y"]) == []


# ── reset ─────────────────────────────────────────────────────────────


def test_reset_clears_data(workspace: Path) -> None:
    store = ToolInvocationStore(workspace)
    store.record_invocation("z")
    store.reset()
    assert store.get_all_stats() == {}


def test_reset_removes_file(workspace: Path) -> None:
    store = ToolInvocationStore(workspace)
    store.record_invocation("z")
    data_path = workspace / ".audit" / ToolInvocationStore.DATA_FILE
    assert data_path.is_file()
    store.reset()
    assert not data_path.is_file()


# ── Edge cases ────────────────────────────────────────────────────────


def test_graceful_on_corrupt_yaml(workspace: Path) -> None:
    """Corrupt YAML file → falls back to fresh data without raising."""
    audit_dir = workspace / ".audit"
    audit_dir.mkdir(parents=True)
    (audit_dir / ToolInvocationStore.DATA_FILE).write_text(":::invalid yaml:::", encoding="utf-8")

    store = ToolInvocationStore(workspace)
    store.record_invocation("test")
    assert store.get_tool_stats("test")["invocation_count"] == 1


def test_multiple_tools_independent_counters(store: ToolInvocationStore) -> None:
    store.record_invocation("a")
    store.record_invocation("a")
    store.record_invocation("b")
    assert store.get_tool_stats("a")["invocation_count"] == 2
    assert store.get_tool_stats("b")["invocation_count"] == 1
