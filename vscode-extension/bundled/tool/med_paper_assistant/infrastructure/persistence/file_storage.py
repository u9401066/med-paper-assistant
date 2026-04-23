"""
File Storage - General file storage operations.
"""

import shutil
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import List, Optional


class FileStorage:
    """
    General file storage service.

    Handles reading, writing, and managing files on disk.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()

    def _safe_path(self, filename: str) -> Path:
        """Resolve filename and ensure it stays within base_dir (path traversal protection)."""
        raw = str(filename or "").strip()
        if not raw:
            raise ValueError("File path is required")
        if raw == ".":
            raise ValueError("Refusing to target storage root")
        if ".." in Path(raw).parts:
            raise ValueError(f"Path traversal blocked: {filename}")
        if PureWindowsPath(raw).is_absolute() or "\\" in raw or ":" in raw:
            raise ValueError(f"Unsafe cross-platform path blocked: {filename}")
        path = (self.base_dir / filename).resolve()
        if not path.is_relative_to(self.base_dir):
            raise ValueError(f"Path traversal blocked: {filename}")
        return path

    def read(self, filename: str) -> str:
        """Read a file's content."""
        path = self._safe_path(filename)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filename}")
        return path.read_text(encoding="utf-8")

    def write(self, filename: str, content: str) -> Path:
        """Write content to a file."""
        path = self._safe_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def append(self, filename: str, content: str) -> Path:
        """Append content to a file."""
        path = self._safe_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return path

    def exists(self, filename: str) -> bool:
        """Check if a file exists."""
        return self._safe_path(filename).exists()

    def delete(self, filename: str):
        """Delete a file."""
        path = self._safe_path(filename)
        if path == self.base_dir:
            raise ValueError("Refusing to delete storage root")
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

    def list_files(self, pattern: str = "*") -> List[Path]:
        """List files matching a pattern."""
        raw = str(pattern or "*").strip()
        if any(ord(ch) < 32 for ch in raw):
            raise ValueError("Glob pattern contains invalid control character(s)")
        if PureWindowsPath(raw).is_absolute() or "\\" in raw or ":" in raw:
            raise ValueError(f"Unsafe cross-platform glob pattern blocked: {pattern}")
        if Path(raw).is_absolute() or ".." in Path(raw).parts:
            raise ValueError(f"Path traversal blocked in glob pattern: {pattern}")
        return [p for p in self.base_dir.glob(raw) if p.resolve().is_relative_to(self.base_dir)]

    def list_dirs(self) -> List[Path]:
        """List subdirectories."""
        if not self.base_dir.exists():
            return []
        return [p for p in self.base_dir.iterdir() if p.is_dir()]

    def get_modified_time(self, filename: str) -> Optional[datetime]:
        """Get file modification time."""
        path = self._safe_path(filename)
        if not path.exists():
            return None
        return datetime.fromtimestamp(path.stat().st_mtime)

    def copy(self, src: str, dst: str) -> Path:
        """Copy a file."""
        src_path = self._safe_path(src)
        dst_path = self._safe_path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        return dst_path

    def move(self, src: str, dst: str) -> Path:
        """Move a file."""
        src_path = self._safe_path(src)
        dst_path = self._safe_path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src_path, dst_path)
        return dst_path
