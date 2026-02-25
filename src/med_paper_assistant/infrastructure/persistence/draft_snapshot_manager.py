"""
Draft Snapshot Manager — Automatic versioning for draft files.

Provides a safety net independent of git: before any draft overwrite,
a timestamped snapshot is saved to `.snapshots/` within the drafts directory.

Architecture:
  Infrastructure layer service. Called by Drafter before every file write.
  Zero-config: snapshots are automatic. Cleanup is automatic (max N per file).

Design rationale (CONSTITUTION §22):
  - Auditable: every draft change is traceable
  - Recomposable: can restore any snapshot without git
  - No agent cooperation required: the snapshot happens in write path
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default: keep last 20 snapshots per file
_DEFAULT_MAX_SNAPSHOTS = 20


class DraftSnapshotManager:
    """
    Automatic snapshot manager for draft files.

    Usage:
        snap = DraftSnapshotManager(drafts_dir="projects/my-paper/drafts")

        # Before overwriting a draft:
        snap.snapshot_before_write("introduction.md")

        # List snapshots:
        snaps = snap.list_snapshots("introduction.md")

        # Restore a snapshot:
        snap.restore_snapshot("introduction.md", snaps[-1]["path"])
    """

    def __init__(
        self,
        drafts_dir: str,
        max_snapshots: int = _DEFAULT_MAX_SNAPSHOTS,
    ) -> None:
        self._drafts_dir = Path(drafts_dir)
        self._snapshots_dir = self._drafts_dir / ".snapshots"
        self._max_snapshots = max_snapshots

    @property
    def snapshots_dir(self) -> Path:
        return self._snapshots_dir

    def snapshot_before_write(self, filename: str, reason: str = "auto") -> str | None:
        """
        Create a snapshot of a draft file before it is overwritten.

        Args:
            filename: Draft filename (e.g., "introduction.md")
            reason: Why the snapshot was taken ("auto", "manual", "pre-patch", etc.)

        Returns:
            Path to the snapshot file, or None if the draft doesn't exist yet.
        """
        source = self._drafts_dir / filename
        if not source.is_file():
            return None  # Nothing to snapshot — new file

        # Create snapshot directory
        file_snap_dir = self._snapshots_dir / Path(filename).stem
        file_snap_dir.mkdir(parents=True, exist_ok=True)

        # Timestamp-based filename (microseconds for uniqueness)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        snap_name = f"{Path(filename).stem}_{ts}{Path(filename).suffix}"
        snap_path = file_snap_dir / snap_name

        # Copy the file
        shutil.copy2(str(source), str(snap_path))

        # Write metadata
        meta_path = snap_path.with_suffix(".meta.json")
        meta = {
            "original": filename,
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "size_bytes": source.stat().st_size,
        }
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

        logger.debug("Snapshot created: %s (reason: %s)", snap_path, reason)

        # Cleanup old snapshots
        self._cleanup(filename)

        return str(snap_path)

    def list_snapshots(self, filename: str) -> list[dict[str, Any]]:
        """
        List all snapshots for a draft file, newest first.

        Returns:
            List of dicts: {path, timestamp, reason, size_bytes}
        """
        file_snap_dir = self._snapshots_dir / Path(filename).stem
        if not file_snap_dir.is_dir():
            return []

        snapshots = []
        for meta_file in sorted(file_snap_dir.glob("*.meta.json"), reverse=True):
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                snap_file = meta_file.with_suffix("").with_suffix(Path(filename).suffix)
                if snap_file.is_file():
                    meta["path"] = str(snap_file)
                    snapshots.append(meta)
            except (json.JSONDecodeError, OSError):
                continue

        return snapshots

    def restore_snapshot(self, filename: str, snapshot_path: str) -> str:
        """
        Restore a draft from a snapshot.

        Creates a snapshot of the current version first (reason: "pre-restore"),
        then copies the snapshot back.

        Returns:
            Path to the restored draft file.
        """
        snap = Path(snapshot_path)
        if not snap.is_file():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")

        target = self._drafts_dir / filename

        # Snapshot the current version before restoring
        if target.is_file():
            self.snapshot_before_write(filename, reason="pre-restore")

        # Restore
        shutil.copy2(str(snap), str(target))
        logger.info("Restored %s from snapshot %s", filename, snap.name)

        return str(target)

    def get_diff_summary(self, filename: str, snapshot_path: str) -> dict[str, Any]:
        """
        Compare current draft with a snapshot (line-level summary).

        Returns:
            Dict with added_lines, removed_lines, unchanged_lines counts.
        """
        current = self._drafts_dir / filename
        snap = Path(snapshot_path)

        if not current.is_file() or not snap.is_file():
            return {"error": "File not found"}

        current_lines = current.read_text(encoding="utf-8").splitlines()
        snap_lines = snap.read_text(encoding="utf-8").splitlines()

        current_set = set(current_lines)
        snap_set = set(snap_lines)

        return {
            "current_lines": len(current_lines),
            "snapshot_lines": len(snap_lines),
            "added_lines": len(current_set - snap_set),
            "removed_lines": len(snap_set - current_set),
            "unchanged_lines": len(current_set & snap_set),
        }

    def snapshot_count(self, filename: str) -> int:
        """How many snapshots exist for a file."""
        file_snap_dir = self._snapshots_dir / Path(filename).stem
        if not file_snap_dir.is_dir():
            return 0
        return len(list(file_snap_dir.glob("*.meta.json")))

    def _cleanup(self, filename: str) -> int:
        """Remove oldest snapshots beyond max_snapshots limit. Returns count removed."""
        file_snap_dir = self._snapshots_dir / Path(filename).stem
        if not file_snap_dir.is_dir():
            return 0

        meta_files = sorted(file_snap_dir.glob("*.meta.json"))
        removed = 0

        while len(meta_files) > self._max_snapshots:
            oldest_meta = meta_files.pop(0)
            # Remove both .meta.json and the actual snapshot file
            snap_file = oldest_meta.with_suffix("").with_suffix(Path(filename).suffix)
            try:
                oldest_meta.unlink()
                if snap_file.is_file():
                    snap_file.unlink()
                removed += 1
            except OSError as e:
                logger.warning("Failed to cleanup snapshot: %s", e)

        return removed
