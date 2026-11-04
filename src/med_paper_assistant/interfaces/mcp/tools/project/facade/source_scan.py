"""Phase 0 source-material scan for ``project_action(action="source_materials")``."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ..facade_guards import resolve_source_scan_root

SOURCE_MATERIAL_EXTENSIONS = {
    ".csv": ("table", "native_table"),
    ".doc": ("document", "asset_aware"),
    ".docx": ("document", "asset_aware"),
    ".pdf": ("document", "asset_aware"),
    ".pptx": ("slides", "asset_aware"),
    ".rtf": ("document", "asset_aware"),
    ".tsv": ("table", "native_table"),
    ".txt": ("text", "native_text"),
    ".xls": ("spreadsheet", "asset_aware"),
    ".xlsx": ("spreadsheet", "asset_aware"),
}
_MARKDOWN_SOURCE_EXTENSIONS = {".md", ".markdown"}
_SOURCE_MATERIAL_SKIP_DIRS = {
    ".audit",
    ".git",
    ".github",
    ".memory",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "exports",
    "htmlcov",
    "logs",
    "node_modules",
    "projects",
    "site-packages",
    "src",
    "tests",
    "vscode-extension",
}


def is_relative_to(path: Path, base: Path) -> bool:
    """Return whether path is inside base without relying on platform-specific strings."""
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _safe_relative_path(path: Path, base: Path) -> str:
    """Return a stable display path across Linux/macOS/Windows."""
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path)


def _is_source_suffix(suffix: str, include_markdown: bool) -> bool:
    return suffix in SOURCE_MATERIAL_EXTENSIONS or (
        include_markdown and suffix in _MARKDOWN_SOURCE_EXTENSIONS
    )


def _prune_dirnames(dirnames: list[str], rel_depth: int, depth_limit: int) -> None:
    dirnames[:] = [
        dirname
        for dirname in dirnames
        if dirname not in _SOURCE_MATERIAL_SKIP_DIRS and not dirname.startswith(".")
    ]
    if rel_depth >= depth_limit:
        dirnames[:] = []


def _directory_candidates(
    current_path: Path,
    filenames: list[str],
    *,
    resolved_project: Path,
    include_markdown: bool,
    include_project_files: bool,
) -> list[Path]:
    candidates: list[Path] = []
    for filename in filenames:
        if filename.startswith("~$"):
            continue
        file_path = current_path / filename
        if not _is_source_suffix(file_path.suffix.lower(), include_markdown):
            continue
        if not include_project_files and is_relative_to(file_path, resolved_project):
            continue
        candidates.append(file_path.resolve())
    return candidates


def iter_source_material_files(
    *,
    scan_root: Path,
    project_dir: Path,
    max_depth: int,
    include_markdown: bool,
    include_project_files: bool,
) -> list[Path]:
    """Scan for user-provided source materials without wandering through generated trees."""
    if not scan_root.exists():
        return []
    if scan_root.is_file():
        return [scan_root] if _is_source_suffix(scan_root.suffix.lower(), include_markdown) else []

    root = scan_root.resolve()
    resolved_project = project_dir.resolve()
    depth_limit = max(0, min(max_depth, 8))
    candidates: list[Path] = []

    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        try:
            rel_depth = len(current_path.relative_to(root).parts)
        except ValueError:
            rel_depth = 0

        _prune_dirnames(dirnames, rel_depth, depth_limit)
        candidates.extend(
            _directory_candidates(
                current_path,
                filenames,
                resolved_project=resolved_project,
                include_markdown=include_markdown,
                include_project_files=include_project_files,
            )
        )

    return sorted(set(candidates), key=lambda path: str(path).lower())


def _source_material_entry(path: Path, *, workspace_root: Path, index: int) -> dict[str, Any]:
    """Build one source-material manifest entry."""
    suffix = path.suffix.lower()
    kind, strategy = SOURCE_MATERIAL_EXTENSIONS.get(
        suffix,
        ("markdown", "native_text"),
    )
    requires_asset_aware = strategy == "asset_aware"
    stat = path.stat()
    return {
        "id": f"source-{index:03d}",
        "path": str(path),
        "relative_path": _safe_relative_path(path, workspace_root),
        "filename": path.name,
        "extension": suffix,
        "kind": kind,
        "evidence_priority": "primary_user_material",
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "ingestion": {
            "strategy": strategy,
            "status": "pending_asset_aware" if requires_asset_aware else "ready_for_context",
            "required": requires_asset_aware,
            "suggested_tool": (
                'asset-aware ingest_documents(file_paths=["..."])'
                if requires_asset_aware
                else "mdpaper native table/text read"
            ),
        },
    }


def _build_manifest(
    *,
    project_slug: str,
    workspace_root: Path,
    scan_root: Path,
    entries: list[dict[str, Any]],
    pending_asset_aware: list[dict[str, Any]],
    max_depth: int,
    include_markdown: bool,
    include_project_files: bool,
) -> dict[str, Any]:
    return {
        "schema": "mdpaper.source_materials.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": project_slug,
        "workspace_root": str(workspace_root),
        "scan_root": str(scan_root),
        "scan_policy": {
            "max_depth": max_depth,
            "include_markdown": include_markdown,
            "include_project_files": include_project_files,
            "ignored_dirs": sorted(_SOURCE_MATERIAL_SKIP_DIRS),
        },
        "summary": {
            "total_candidates": len(entries),
            "pending_asset_aware": len(pending_asset_aware),
            "ready_native": len(entries) - len(pending_asset_aware),
        },
        "materials": entries,
        "agent_next_steps": {
            "asset_aware_required": bool(pending_asset_aware),
            "asset_aware_file_paths": [entry["path"] for entry in pending_asset_aware],
            "instruction": (
                "Call asset-aware ingest_documents on asset_aware_file_paths before Phase 5 "
                "and use extracted tables/sections as primary evidence."
                if pending_asset_aware
                else "No asset-aware ingestion required by this scan."
            ),
        },
    }


def _manifest_report_lines(
    manifest: dict[str, Any],
    entries: list[dict[str, Any]],
    pending_asset_aware: list[dict[str, Any]],
) -> list[str]:
    lines = [
        "# Source Materials Intake",
        "",
        f"- Schema: `{manifest['schema']}`",
        f"- Scan root: `{manifest['scan_root']}`",
        f"- Total candidates: {len(entries)}",
        f"- Pending asset-aware ingestion: {len(pending_asset_aware)}",
        "",
        "| ID | File | Kind | Ingestion status |",
        "|---|---|---|---|",
    ]
    if entries:
        for entry in entries:
            lines.append(
                "| {id} | {file} | {kind} | {status} |".format(
                    id=entry["id"],
                    file=entry["relative_path"],
                    kind=entry["kind"],
                    status=entry["ingestion"]["status"],
                )
            )
    else:
        lines.append("| - | No source materials found | - | - |")
    if pending_asset_aware:
        lines.extend(
            [
                "",
                "## Required next step",
                "",
                "Call asset-aware `ingest_documents` for these primary source files before drafting:",
            ]
        )
        for entry in pending_asset_aware[:20]:
            lines.append(f"- `{entry['path']}`")
    return lines


def _scan_entries(
    *,
    scan_root: Path,
    workspace_root: Path,
    project_dir: Path,
    max_depth: int,
    include_markdown: bool,
    include_project_files: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files = iter_source_material_files(
        scan_root=scan_root,
        project_dir=project_dir,
        max_depth=max_depth,
        include_markdown=include_markdown,
        include_project_files=include_project_files,
    )
    entries = [
        _source_material_entry(path, workspace_root=workspace_root, index=index)
        for index, path in enumerate(files, start=1)
    ]
    pending_asset_aware = [
        entry
        for entry in entries
        if entry.get("ingestion", {}).get("status") == "pending_asset_aware"
    ]
    return entries, pending_asset_aware


def write_source_materials_manifest(
    *,
    project_dir: Path,
    project_slug: str,
    source_dir: str,
    max_depth: int,
    include_markdown: bool,
    include_project_files: bool,
) -> tuple[Path, Path, dict[str, Any]]:
    """Scan workspace inputs and write Phase 0 source-material artifacts."""
    scan_root, workspace_root = resolve_source_scan_root(source_dir, project_dir)
    audit_dir = project_dir / ".audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    entries, pending_asset_aware = _scan_entries(
        scan_root=scan_root,
        workspace_root=workspace_root,
        project_dir=project_dir,
        max_depth=max_depth,
        include_markdown=include_markdown,
        include_project_files=include_project_files,
    )
    manifest = _build_manifest(
        project_slug=project_slug,
        workspace_root=workspace_root,
        scan_root=scan_root,
        entries=entries,
        pending_asset_aware=pending_asset_aware,
        max_depth=max_depth,
        include_markdown=include_markdown,
        include_project_files=include_project_files,
    )

    manifest_path = audit_dir / "source-materials.yaml"
    manifest_path.write_text(
        yaml.dump(manifest, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    report_path = audit_dir / "source-materials.md"
    lines = _manifest_report_lines(manifest, entries, pending_asset_aware)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return manifest_path, report_path, manifest
