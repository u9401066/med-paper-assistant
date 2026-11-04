"""Input guards for the project facade (source scan roots, journal profile writes)."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from med_paper_assistant.shared.path_guard import PathGuardError
from med_paper_assistant.shared.workspace_root import resolve_workspace_root

JOURNAL_PROFILE_FILENAME = "journal-profile.yaml"


def infer_workspace_root(project_dir: Path) -> Path:
    """Infer the workspace root from a project path."""
    if project_dir.parent.name == "projects" and not os.environ.get("MEDPAPER_BASE_DIR"):
        return project_dir.parent.parent.resolve()
    return resolve_workspace_root()


def resolve_source_scan_root(source_dir: str, project_dir: Path) -> tuple[Path, Path]:
    """Resolve the source-material scan root as ``(scan_root, workspace_root)``.

    A non-empty ``source_dir`` must live inside the workspace or the project. Relative
    values are anchored at the workspace root. UNC/network paths, control characters and
    any path that escapes the allowed roots (via ``..``, absolute paths or symlinks) are
    rejected with ``PathGuardError``.
    """
    workspace_root = infer_workspace_root(project_dir)
    raw = source_dir.strip()
    if not raw:
        return workspace_root, workspace_root
    if any(ord(ch) < 32 for ch in raw):
        raise PathGuardError("source_dir contains invalid control character(s).")
    if raw.startswith(("\\\\", "//")):
        raise PathGuardError("source_dir must not use UNC/network paths.")
    # Agents frequently send Windows-style separators; treat them as separators on every
    # OS so ``..\\outside`` cannot slip through as a literal POSIX filename.
    candidate = Path(raw.replace("\\", "/")).expanduser()
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    resolved = candidate.resolve()
    roots = (workspace_root.resolve(), project_dir.resolve())
    if not any(resolved == root or resolved.is_relative_to(root) for root in roots):
        raise PathGuardError("source_dir must be inside the workspace or the project directory.")
    return resolved, workspace_root


def source_dir_error(source_dir: str, project_dir: Path) -> str | None:
    """Return a user-facing error when ``source_dir`` is not allowed, else ``None``."""
    try:
        resolve_source_scan_root(source_dir, project_dir)
    except PathGuardError as exc:
        return f"❌ {exc}"
    return None


def write_journal_profile(
    profile_path: Path, profile: dict[str, object], *, overwrite: bool
) -> str | None:
    """Write the journal profile; refuse to clobber an existing one unless ``overwrite``.

    Returns an error message when the write was refused, otherwise ``None``.
    """
    if profile_path.exists() and not overwrite:
        return (
            f"❌ {profile_path.name} already exists and was left unchanged. "
            "Pass confirm=true to overwrite it with a generated profile."
        )
    profile_path.write_text(
        yaml.dump(profile, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return None


__all__ = [
    "JOURNAL_PROFILE_FILENAME",
    "infer_workspace_root",
    "resolve_source_scan_root",
    "source_dir_error",
    "write_journal_profile",
]
