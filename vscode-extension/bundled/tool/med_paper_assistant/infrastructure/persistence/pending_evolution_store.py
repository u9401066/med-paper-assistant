"""
PendingEvolutionStore — Cross-conversation persistence for evolution items.

Bridges the gap between conversations: when meta-learning, writing hooks,
or tool health diagnostics produce evolution items (threshold adjustments,
coverage gaps, tool fixes), those items are persisted to disk so the next
conversation can pick them up via get_workspace_state().

Architecture:
    Infrastructure layer service. Workspace-level (not per-project) because
    evolution items may span multiple projects and need to survive across
    any conversation.
    Persists to workspace_root/.audit/pending-evolutions.yaml

CONSTITUTION §23 Compliance:
    - L1/L2 items (auto_apply=True) can be applied automatically
    - L3 items (auto_apply=False) require user confirmation
    - All state changes are logged with timestamps and actor identity
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()

# Auto-incrementing ID counter key in the YAML data
_COUNTER_KEY = "next_id"


class EvolutionItem:
    """A single pending evolution item."""

    def __init__(
        self,
        item_type: str,
        source: str,
        payload: dict[str, Any],
        project: str | None = None,
        auto_apply: bool = False,
        item_id: str | None = None,
    ) -> None:
        self.id = item_id or ""
        self.type = item_type
        self.source = source
        self.created_at = datetime.now(tz=timezone.utc).isoformat()
        self.project = project
        self.status = "pending"
        self.auto_apply = auto_apply
        self.payload = payload
        self.applied_at: str | None = None
        self.applied_by: str | None = None
        self.dismissed_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "created_at": self.created_at,
            "project": self.project,
            "status": self.status,
            "auto_apply": self.auto_apply,
            "payload": self.payload,
        }
        if self.applied_at:
            d["applied_at"] = self.applied_at
        if self.applied_by:
            d["applied_by"] = self.applied_by
        if self.dismissed_reason:
            d["dismissed_reason"] = self.dismissed_reason
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvolutionItem:
        item = cls(
            item_type=data.get("type", "unknown"),
            source=data.get("source", ""),
            payload=data.get("payload", {}),
            project=data.get("project"),
            auto_apply=data.get("auto_apply", False),
            item_id=data.get("id", ""),
        )
        item.status = data.get("status", "pending")
        item.created_at = data.get("created_at", item.created_at)
        item.applied_at = data.get("applied_at")
        item.applied_by = data.get("applied_by")
        item.dismissed_reason = data.get("dismissed_reason")
        return item


class PendingEvolutionStore:
    """
    Workspace-level persistent store for cross-conversation evolution items.

    Data file: workspace_root/.audit/pending-evolutions.yaml

    Usage:
        store = PendingEvolutionStore(workspace_root)
        item_id = store.add(EvolutionItem(
            item_type="threshold_adjustment",
            source="meta_learning_D3",
            payload={"hook_id": "A5", "current": 1.0, "suggested": 1.15},
            auto_apply=True,
        ))
        pending = store.get_pending()
        store.mark_applied(item_id, by="agent")
    """

    DATA_FILE = "pending-evolutions.yaml"

    def __init__(self, workspace_root: str | Path) -> None:
        self._dir = Path(workspace_root) / ".audit"
        self._path = self._dir / self.DATA_FILE
        self._data: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        """Load or initialize evolution data. Caches in memory after first load."""
        if self._data is not None:
            return self._data

        if self._path.is_file():
            try:
                loaded = yaml.safe_load(self._path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    loaded.setdefault("version", 1)
                    loaded.setdefault("items", [])
                    loaded.setdefault(_COUNTER_KEY, 1)
                    self._data = loaded
                    return self._data
            except (yaml.YAMLError, OSError) as e:
                logger.warning("pending_evolution_store.load_failed", error=str(e))

        self._data = {
            "version": 1,
            "items": [],
            _COUNTER_KEY: 1,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        return self._data

    def _save(self) -> None:
        """Persist evolution data to disk."""
        self._dir.mkdir(parents=True, exist_ok=True)
        data = self._load()
        data["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        self._path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def _next_id(self) -> str:
        """Generate next auto-incrementing ID."""
        data = self._load()
        counter = data.get(_COUNTER_KEY, 1)
        item_id = f"PE-{counter:04d}"
        data[_COUNTER_KEY] = counter + 1
        return item_id

    def add(self, item: EvolutionItem) -> str:
        """
        Add a pending evolution item.

        Returns:
            The assigned item ID.
        """
        data = self._load()
        if not item.id:
            item.id = self._next_id()
        data["items"].append(item.to_dict())
        self._save()
        logger.info(
            "pending_evolution.added",
            item_id=item.id,
            item_type=item.type,
            source=item.source,
        )
        return item.id

    def get_pending(self) -> list[EvolutionItem]:
        """Get all items with status 'pending'."""
        data = self._load()
        return [EvolutionItem.from_dict(d) for d in data["items"] if d.get("status") == "pending"]

    def get_all(self) -> list[EvolutionItem]:
        """Get all items regardless of status."""
        data = self._load()
        return [EvolutionItem.from_dict(d) for d in data["items"]]

    def mark_applied(self, item_id: str, by: str) -> bool:
        """
        Mark an item as applied.

        Args:
            item_id: The item ID to mark.
            by: Who applied it ("agent", "ghaw", "user").

        Returns:
            True if the item was found and marked.
        """
        data = self._load()
        for d in data["items"]:
            if d.get("id") == item_id and d.get("status") == "pending":
                d["status"] = "applied"
                d["applied_at"] = datetime.now(tz=timezone.utc).isoformat()
                d["applied_by"] = by
                self._save()
                logger.info("pending_evolution.applied", item_id=item_id, by=by)
                return True
        return False

    def mark_dismissed(self, item_id: str, reason: str) -> bool:
        """
        Mark an item as dismissed (not applicable / rejected).

        Args:
            item_id: The item ID to dismiss.
            reason: Why it was dismissed.

        Returns:
            True if the item was found and dismissed.
        """
        data = self._load()
        for d in data["items"]:
            if d.get("id") == item_id and d.get("status") == "pending":
                d["status"] = "dismissed"
                d["dismissed_reason"] = reason
                d["applied_at"] = datetime.now(tz=timezone.utc).isoformat()
                self._save()
                logger.info("pending_evolution.dismissed", item_id=item_id, reason=reason)
                return True
        return False

    def get_stale(self, days: int = 7) -> list[EvolutionItem]:
        """Get pending items older than N days."""
        cutoff = datetime.now(tz=timezone.utc)
        result = []
        for item in self.get_pending():
            try:
                created = datetime.fromisoformat(item.created_at)
                # Ensure timezone-aware comparison
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                age = (cutoff - created).days
                if age >= days:
                    result.append(item)
            except (ValueError, TypeError):
                # If we can't parse the date, consider it stale
                result.append(item)
        return result

    def summary(self) -> dict[str, Any]:
        """Get summary statistics."""
        data = self._load()
        items = data.get("items", [])
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for d in items:
            status = d.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            if status == "pending":
                item_type = d.get("type", "unknown")
                by_type[item_type] = by_type.get(item_type, 0) + 1

        return {
            "total": len(items),
            "pending": by_status.get("pending", 0),
            "applied": by_status.get("applied", 0),
            "dismissed": by_status.get("dismissed", 0),
            "pending_by_type": by_type,
        }
