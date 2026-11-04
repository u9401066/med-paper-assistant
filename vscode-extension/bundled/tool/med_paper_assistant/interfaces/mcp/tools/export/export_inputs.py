"""Input policy helpers for Pandoc export tools (CSL / reference-doc / paths)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path, PureWindowsPath
from typing import Any

from med_paper_assistant.shared.path_guard import PathGuardError
from med_paper_assistant.shared.template_paths import get_templates_dir
from med_paper_assistant.shared.workspace_root import resolve_workspace_root


def _allowed_roots(project_dir: str | Path | None) -> list[Path]:
    roots = [resolve_workspace_root(), get_templates_dir().resolve()]
    if project_dir:
        roots.append(Path(project_dir).resolve())
    return roots


def _is_path_like(value: str) -> bool:
    return (
        any(sep in value for sep in ("/", "\\", ":"))
        or value.startswith(".")
        or os.path.isabs(value)
    )


def _validate_raw_path(raw: str, field_name: str) -> None:
    if any(ord(ch) < 32 for ch in raw):
        raise PathGuardError(f"{field_name} contains invalid control character(s).")
    if raw.startswith(("\\\\", "//")):
        raise PathGuardError(f"{field_name} must not use UNC/network paths.")
    drive = PureWindowsPath(raw).drive
    if ":" in raw[len(drive) :]:
        raise PathGuardError(f"{field_name} must not contain ':' (alternate streams).")
    if ".." in PureWindowsPath(raw).parts or ".." in Path(raw).parts:
        raise PathGuardError(f"{field_name} must not contain path traversal segments.")


def _contain(candidate: Path, roots: list[Path], field_name: str) -> Path:
    resolved = candidate.resolve()
    if not any(resolved == root or resolved.is_relative_to(root) for root in roots):
        raise PathGuardError(
            f"{field_name} must be inside the workspace, the project, or the templates directory."
        )
    return resolved


def resolve_export_file(
    value: str,
    *,
    field_name: str,
    suffixes: tuple[str, ...],
    project_dir: str | Path | None,
) -> str:
    """Resolve a user-supplied template/style file path under an allowed root."""
    raw = str(value).strip()
    _validate_raw_path(raw, field_name)
    roots = _allowed_roots(project_dir)
    candidate = Path(raw)
    if not candidate.is_absolute():
        base = Path(project_dir) if project_dir else roots[0]
        candidate = base / candidate
    resolved = _contain(candidate, roots, field_name)
    if resolved.suffix.lower() not in suffixes:
        raise PathGuardError(f"{field_name} must use one of: {', '.join(suffixes)}.")
    if not resolved.is_file():
        raise FileNotFoundError(f"{field_name} file not found: {raw}")
    return str(resolved)


def resolve_export_csl(csl_style: str, exporter: Any, project_dir: str | Path | None) -> str:
    """Return a verified CSL file path for a style name or a contained file path.

    Raises an error for UNC/escaping paths and for style names that cannot be resolved,
    so exports never silently fall back to Pandoc's default citation style.
    """
    raw = str(csl_style or "").strip()
    if not raw:
        raise PathGuardError("csl_style is required.")
    if _is_path_like(raw):
        return resolve_export_file(
            raw, field_name="csl_style", suffixes=(".csl",), project_dir=project_dir
        )
    resolved = exporter.resolve_csl(raw)
    if not resolved:
        raise FileNotFoundError(
            f"CSL style '{raw}' not found in the templates directory; "
            "use a bundled style name or a .csl file inside the workspace."
        )
    _contain(Path(resolved), _allowed_roots(project_dir), "csl_style")
    return str(resolved)


def resolve_export_reference_doc(value: str | None, project_dir: str | Path | None) -> str | None:
    """Return a verified Word reference document path, or None when not requested."""
    if value is None or not str(value).strip():
        return None
    return resolve_export_file(
        str(value),
        field_name="reference_doc",
        suffixes=(".docx", ".dotx"),
        project_dir=project_dir,
    )


def require_drafts_dir(paths: Mapping[str, str]) -> str:
    """Return the project's absolute drafts directory, never a CWD-relative fallback."""
    drafts = paths.get("drafts")
    if not drafts or not os.path.isabs(drafts):
        raise PathGuardError("Project drafts directory could not be resolved to an absolute path.")
    return drafts


def resolve_export_inputs(
    drafts_dir: str, pipeline: Any, csl_style: str, reference_doc: str | None = None
) -> tuple[str, str, str | None]:
    """Return ``(project_dir, csl_file, reference_doc_file)`` after policy checks."""
    project_dir = str(Path(drafts_dir).parent)
    return (
        project_dir,
        resolve_export_csl(csl_style, pipeline._pandoc, project_dir),
        resolve_export_reference_doc(reference_doc, project_dir),
    )


def entry_title(entry: Mapping[str, Any], limit: int = 80) -> str:
    """Short display title for a CSL-JSON entry; tolerates a missing or null title."""
    return str(entry.get("title") or "Unknown")[:limit]


__all__ = [
    "entry_title",
    "require_drafts_dir",
    "resolve_export_csl",
    "resolve_export_file",
    "resolve_export_inputs",
    "resolve_export_reference_doc",
]
