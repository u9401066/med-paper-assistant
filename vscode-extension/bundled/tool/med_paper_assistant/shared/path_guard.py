"""Cross-platform path guards for user-supplied filenames."""

from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath
from typing import Iterable


class PathGuardError(ValueError):
    """Raised when a user-supplied filename/path is unsafe."""


WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

WINDOWS_INVALID_FILENAME_CHARS = set('<>:"/\\|?*')


def _normalise_suffixes(suffixes: Iterable[str] | None) -> set[str] | None:
    if suffixes is None:
        return None
    return {s.lower() if s.startswith(".") else f".{s.lower()}" for s in suffixes}


def normalize_relative_filename(
    value: str | None,
    *,
    field_name: str = "filename",
    default_suffix: str | None = None,
    allowed_suffixes: Iterable[str] | None = None,
    allow_hidden: bool = False,
) -> str:
    """Validate a user-supplied basename and return a normalized filename.

    This accepts only a single file basename, never a directory path. It rejects
    POSIX and Windows absolute paths, path traversal, Windows drive syntax, and
    characters that are invalid on Windows so Linux/macOS/Windows behaviour is
    consistent.
    """
    raw = str(value or "").strip()
    if not raw:
        raise PathGuardError(f"{field_name} is required.")

    if any(ord(ch) < 32 for ch in raw):
        raise PathGuardError(f"{field_name} contains invalid control character(s).")

    if os.path.isabs(raw) or PureWindowsPath(raw).is_absolute():
        raise PathGuardError(f"{field_name} must be relative, not absolute.")

    if raw in {".", ".."} or ".." in PureWindowsPath(raw).parts or ".." in Path(raw).parts:
        raise PathGuardError(f"{field_name} must not contain path traversal segments.")

    invalid = sorted({ch for ch in raw if ch in WINDOWS_INVALID_FILENAME_CHARS})
    if invalid:
        raise PathGuardError(
            f"{field_name} contains invalid cross-platform character(s): {''.join(invalid)}"
        )

    if Path(raw).name != raw or PureWindowsPath(raw).name != raw:
        raise PathGuardError(f"{field_name} must not include directory components.")

    if not allow_hidden and raw.startswith("."):
        raise PathGuardError(f"{field_name} must not be hidden or empty.")

    if raw.rstrip(" .") != raw:
        raise PathGuardError(f"{field_name} must not end with a dot or space.")

    if default_suffix:
        suffix = default_suffix if default_suffix.startswith(".") else f".{default_suffix}"
        if not Path(raw).suffix:
            raw = f"{raw}{suffix}"

    allowed = _normalise_suffixes(allowed_suffixes)
    suffix = Path(raw).suffix.lower()
    if allowed is not None and suffix not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise PathGuardError(f"{field_name} must use one of: {allowed_list}.")

    stem = Path(raw).stem.rstrip(" .").upper()
    if not stem or stem in WINDOWS_RESERVED_NAMES:
        raise PathGuardError(f"{field_name} is not valid on Windows.")

    return raw


def resolve_child_path(
    base_dir: str | Path,
    filename: str | None,
    *,
    field_name: str = "filename",
    default_suffix: str | None = None,
    allowed_suffixes: Iterable[str] | None = None,
    allow_hidden: bool = False,
) -> Path:
    """Resolve a safe basename under ``base_dir`` and verify containment."""
    safe_name = normalize_relative_filename(
        filename,
        field_name=field_name,
        default_suffix=default_suffix,
        allowed_suffixes=allowed_suffixes,
        allow_hidden=allow_hidden,
    )
    root = Path(base_dir).resolve()
    path = (root / safe_name).resolve()
    if path.parent != root:
        raise PathGuardError(f"{field_name} must stay within {root}.")
    if root.exists():
        safe_casefold = safe_name.casefold()
        for child in root.iterdir():
            if child.name.casefold() == safe_casefold and child.name != safe_name:
                raise PathGuardError(
                    f"{field_name} conflicts with existing file differing only by case: "
                    f"{child.name}."
                )
    return path


def resolve_child_directory(
    base_dir: str | Path,
    relative_dir: str | None,
    *,
    field_name: str = "directory",
    allow_current: bool = True,
    allow_hidden: bool = False,
) -> Path:
    """Resolve a safe relative directory path under ``base_dir``.

    Unlike :func:`resolve_child_path`, this accepts multiple POSIX-style
    directory segments. It still rejects absolute paths, Windows drive/UNC
    paths, backslashes, traversal, control characters, Windows-invalid
    characters, and Windows reserved segment names.
    """
    raw = str(relative_dir or "").strip()
    if not raw:
        if allow_current:
            raw = "."
        else:
            raise PathGuardError(f"{field_name} is required.")

    if any(ord(ch) < 32 for ch in raw):
        raise PathGuardError(f"{field_name} contains invalid control character(s).")

    windows_path = PureWindowsPath(raw)
    if os.path.isabs(raw) or windows_path.is_absolute() or windows_path.drive:
        raise PathGuardError(f"{field_name} must be relative, not absolute.")

    invalid_dir_chars = WINDOWS_INVALID_FILENAME_CHARS - {"/"}
    invalid = sorted({ch for ch in raw if ch in invalid_dir_chars})
    if invalid:
        raise PathGuardError(
            f"{field_name} contains invalid cross-platform character(s): {''.join(invalid)}"
        )

    parts = [part for part in Path(raw).parts if part not in {"", "."}]
    if not parts:
        if allow_current:
            return Path(base_dir).resolve()
        raise PathGuardError(f"{field_name} is required.")

    for part in parts:
        if part == "..":
            raise PathGuardError(f"{field_name} must not contain path traversal segments.")
        if not allow_hidden and part.startswith("."):
            raise PathGuardError(f"{field_name} must not contain hidden segments.")
        if Path(part).name != part or PureWindowsPath(part).name != part:
            raise PathGuardError(f"{field_name} must use plain directory segments.")
        stem = Path(part).stem.rstrip(" .").upper()
        if not stem or stem in WINDOWS_RESERVED_NAMES:
            raise PathGuardError(f"{field_name} contains a segment that is not valid on Windows.")

    root = Path(base_dir).resolve()
    current = root
    for part in parts:
        if current.exists():
            for child in current.iterdir():
                if child.name.casefold() == part.casefold() and child.name != part:
                    raise PathGuardError(
                        f"{field_name} conflicts with existing path differing only by case: "
                        f"{child.name}."
                    )
        current = current / part

    path = current.resolve()
    if path != root and not path.is_relative_to(root):
        raise PathGuardError(f"{field_name} must stay within {root}.")
    return path


__all__ = [
    "PathGuardError",
    "normalize_relative_filename",
    "resolve_child_directory",
    "resolve_child_path",
]
