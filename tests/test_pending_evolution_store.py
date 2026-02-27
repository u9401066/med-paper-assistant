"""Tests for PendingEvolutionStore — cross-conversation evolution persistence."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from med_paper_assistant.infrastructure.persistence.pending_evolution_store import (
    EvolutionItem,
    PendingEvolutionStore,
)

# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture()
def store(workspace: Path) -> PendingEvolutionStore:
    return PendingEvolutionStore(workspace)


# ── First-run / file creation ─────────────────────────────────────────


def test_first_run_no_audit_dir(store: PendingEvolutionStore, workspace: Path) -> None:
    """On first run .audit/ does not exist — created on first save."""
    assert not (workspace / ".audit").exists()
    store.add(
        EvolutionItem(
            item_type="threshold_adjustment",
            source="test",
            payload={"hook_id": "A5"},
        )
    )
    assert (workspace / ".audit" / PendingEvolutionStore.DATA_FILE).is_file()


def test_fresh_store_no_pending(store: PendingEvolutionStore) -> None:
    """Empty store returns no pending items."""
    assert store.get_pending() == []


def test_fresh_store_summary(store: PendingEvolutionStore) -> None:
    """Empty store summary shows zeros."""
    s = store.summary()
    assert s["total"] == 0
    assert s["pending"] == 0


# ── add ───────────────────────────────────────────────────────────────


def test_add_returns_auto_id(store: PendingEvolutionStore) -> None:
    """add() assigns auto-incrementing PE-NNNN IDs."""
    id1 = store.add(EvolutionItem(item_type="threshold_adjustment", source="test", payload={}))
    id2 = store.add(EvolutionItem(item_type="suggestion", source="test2", payload={}))
    assert id1 == "PE-0001"
    assert id2 == "PE-0002"


def test_add_preserves_user_id(store: PendingEvolutionStore) -> None:
    """add() uses user-provided ID if set."""
    item = EvolutionItem(
        item_type="coverage_gap",
        source="test",
        payload={},
        item_id="CUSTOM-001",
    )
    returned_id = store.add(item)
    assert returned_id == "CUSTOM-001"


def test_add_persists_to_disk(store: PendingEvolutionStore, workspace: Path) -> None:
    """Items are persisted to YAML immediately."""
    store.add(
        EvolutionItem(
            item_type="tool_fix",
            source="health_check",
            payload={"tool": "write_draft"},
            project="test-project",
        )
    )
    data_path = workspace / ".audit" / PendingEvolutionStore.DATA_FILE
    data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    assert len(data["items"]) == 1
    assert data["items"][0]["type"] == "tool_fix"
    assert data["items"][0]["project"] == "test-project"
    assert data["items"][0]["status"] == "pending"


# ── get_pending ───────────────────────────────────────────────────────


def test_get_pending_filters_applied(store: PendingEvolutionStore) -> None:
    """get_pending() only returns items with status='pending'."""
    id1 = store.add(EvolutionItem(item_type="threshold_adjustment", source="test", payload={}))
    store.add(EvolutionItem(item_type="suggestion", source="test", payload={}))
    store.mark_applied(id1, by="agent")

    pending = store.get_pending()
    assert len(pending) == 1
    assert pending[0].type == "suggestion"


# ── mark_applied ──────────────────────────────────────────────────────


def test_mark_applied_changes_status(store: PendingEvolutionStore) -> None:
    item_id = store.add(EvolutionItem(item_type="test", source="test", payload={}))
    assert store.mark_applied(item_id, by="agent")

    all_items = store.get_all()
    assert len(all_items) == 1
    assert all_items[0].status == "applied"
    assert all_items[0].applied_by == "agent"
    assert all_items[0].applied_at is not None


def test_mark_applied_returns_false_for_unknown(store: PendingEvolutionStore) -> None:
    assert not store.mark_applied("PE-9999", by="agent")


def test_mark_applied_idempotent(store: PendingEvolutionStore) -> None:
    """Cannot re-apply an already applied item."""
    item_id = store.add(EvolutionItem(item_type="test", source="test", payload={}))
    assert store.mark_applied(item_id, by="agent")
    assert not store.mark_applied(item_id, by="agent")  # Already applied


# ── mark_dismissed ────────────────────────────────────────────────────


def test_mark_dismissed_changes_status(store: PendingEvolutionStore) -> None:
    item_id = store.add(EvolutionItem(item_type="test", source="test", payload={}))
    assert store.mark_dismissed(item_id, reason="not applicable")

    all_items = store.get_all()
    assert all_items[0].status == "dismissed"
    assert all_items[0].dismissed_reason == "not applicable"


# ── get_stale ─────────────────────────────────────────────────────────


def test_get_stale_returns_old_items(store: PendingEvolutionStore, workspace: Path) -> None:
    """Items older than N days are returned as stale."""
    store.add(EvolutionItem(item_type="test", source="test", payload={}))
    # Manually backdate the item
    data_path = workspace / ".audit" / PendingEvolutionStore.DATA_FILE
    data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    old_date = (datetime.now(tz=timezone.utc) - timedelta(days=10)).isoformat()
    data["items"][0]["created_at"] = old_date
    data_path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    # Reload store to pick up changes
    fresh_store = PendingEvolutionStore(workspace)
    stale = fresh_store.get_stale(days=7)
    assert len(stale) == 1


def test_get_stale_ignores_recent(store: PendingEvolutionStore) -> None:
    """Recently created items are not stale."""
    store.add(EvolutionItem(item_type="test", source="test", payload={}))
    stale = store.get_stale(days=7)
    assert len(stale) == 0


# ── summary ───────────────────────────────────────────────────────────


def test_summary_counts(store: PendingEvolutionStore) -> None:
    id1 = store.add(EvolutionItem(item_type="threshold_adjustment", source="a", payload={}))
    store.add(EvolutionItem(item_type="threshold_adjustment", source="b", payload={}))
    store.add(EvolutionItem(item_type="coverage_gap", source="c", payload={}))
    store.mark_applied(id1, by="agent")

    s = store.summary()
    assert s["total"] == 3
    assert s["pending"] == 2
    assert s["applied"] == 1
    assert s["dismissed"] == 0
    assert s["pending_by_type"]["threshold_adjustment"] == 1
    assert s["pending_by_type"]["coverage_gap"] == 1


# ── EvolutionItem serialization ───────────────────────────────────────


def test_evolution_item_roundtrip() -> None:
    """EvolutionItem can serialize and deserialize correctly."""
    item = EvolutionItem(
        item_type="threshold_adjustment",
        source="meta_learning_D3",
        payload={"hook_id": "A5", "value": 1.15},
        project="test-project",
        auto_apply=True,
        item_id="PE-0042",
    )
    d = item.to_dict()
    rebuilt = EvolutionItem.from_dict(d)

    assert rebuilt.id == "PE-0042"
    assert rebuilt.type == "threshold_adjustment"
    assert rebuilt.source == "meta_learning_D3"
    assert rebuilt.project == "test-project"
    assert rebuilt.auto_apply is True
    assert rebuilt.payload == {"hook_id": "A5", "value": 1.15}
    assert rebuilt.status == "pending"


# ── Persistence across instances ──────────────────────────────────────


def test_data_survives_new_instance(workspace: Path) -> None:
    """Data persisted by one instance is readable by a new instance."""
    store1 = PendingEvolutionStore(workspace)
    store1.add(EvolutionItem(item_type="test", source="instance1", payload={"key": "val"}))

    store2 = PendingEvolutionStore(workspace)
    pending = store2.get_pending()
    assert len(pending) == 1
    assert pending[0].source == "instance1"
    assert pending[0].payload == {"key": "val"}
