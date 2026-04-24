"""Consolidated project/workspace facade tools."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from mcp.server.fastmcp import Context, FastMCP

from .._shared import (
    facade_schema_json,
    invoke_tool_handler,
    normalize_facade_action,
    resolve_project_context,
)

ToolMap = Mapping[str, Callable[..., Any]]

_SOURCE_MATERIAL_EXTENSIONS = {
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


def _build_journal_profile(
    *,
    target_journal: str,
    paper_type: str,
    citation_style: str,
    language_preference: str,
    writing_style: str,
) -> dict[str, Any]:
    """Build a minimal Phase 0 journal profile that satisfies downstream gates."""
    journal_name = target_journal.strip() or "generic"
    resolved_paper_type = paper_type.strip() or "original-research"
    resolved_citation_style = citation_style.strip() or "vancouver"
    language = language_preference.strip() or "en-US"
    return {
        "schema": "mdpaper.journal_profile.v1",
        "journal": {
            "name": journal_name,
            "locale": language,
        },
        "paper": {
            "type": resolved_paper_type,
            "sections": [
                {"name": "Abstract", "required": True, "counts_toward_total": False},
                {"name": "Introduction", "required": True, "counts_toward_total": True},
                {"name": "Methods", "required": True, "counts_toward_total": True},
                {"name": "Results", "required": True, "counts_toward_total": True},
                {"name": "Discussion", "required": True, "counts_toward_total": True},
                {"name": "References", "required": True, "counts_toward_total": False},
            ],
        },
        "references": {
            "style": resolved_citation_style,
            "minimum_reference_limits": {
                "case-report": 8,
                "letter": 8,
                "original-research": 20,
                "review-article": 30,
                "systematic-review": 40,
            },
        },
        "word_limits": {
            "total_manuscript": 3500,
            "abstract": 250,
            "introduction": 900,
            "methods": 900,
            "results": 900,
            "discussion": 1200,
        },
        "assets": {
            "figures_max": 6,
            "tables_max": 6,
        },
        "pipeline": {
            "review_max_rounds": 3,
            "writing": {
                "prefer_language": "british" if language.lower() in {"en-gb", "gb"} else "american",
                "style": writing_style.strip() or "journal",
            },
        },
        "required_documents": {
            "cover_letter": False,
            "data_availability": True,
            "ethics_statement": True,
            "conflict_of_interest": True,
        },
    }


def _is_relative_to(path: Path, base: Path) -> bool:
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


def _infer_workspace_root(project_dir: Path) -> Path:
    """Infer the workspace root from a project path."""
    configured = os.environ.get("MEDPAPER_BASE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    if project_dir.parent.name == "projects":
        return project_dir.parent.parent.resolve()
    return project_dir.parent.resolve()


def _resolve_source_scan_root(source_dir: str, project_dir: Path) -> tuple[Path, Path]:
    """Resolve the requested source-material scan root."""
    workspace_root = _infer_workspace_root(project_dir)
    if source_dir.strip():
        candidate = Path(source_dir).expanduser()
        if not candidate.is_absolute():
            candidate = workspace_root / candidate
        return candidate.resolve(), workspace_root
    return workspace_root, workspace_root


def _iter_source_material_files(
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
        suffix = scan_root.suffix.lower()
        return [scan_root] if (
            suffix in _SOURCE_MATERIAL_EXTENSIONS
            or (include_markdown and suffix in _MARKDOWN_SOURCE_EXTENSIONS)
        ) else []

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

        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in _SOURCE_MATERIAL_SKIP_DIRS and not dirname.startswith(".")
        ]
        if rel_depth >= depth_limit:
            dirnames[:] = []

        for filename in filenames:
            if filename.startswith("~$"):
                continue
            file_path = current_path / filename
            suffix = file_path.suffix.lower()
            allowed = suffix in _SOURCE_MATERIAL_EXTENSIONS or (
                include_markdown and suffix in _MARKDOWN_SOURCE_EXTENSIONS
            )
            if not allowed:
                continue
            if not include_project_files and _is_relative_to(file_path, resolved_project):
                continue
            candidates.append(file_path.resolve())

    return sorted(set(candidates), key=lambda path: str(path).lower())


def _source_material_entry(path: Path, *, workspace_root: Path, index: int) -> dict[str, Any]:
    """Build one source-material manifest entry."""
    suffix = path.suffix.lower()
    kind, strategy = _SOURCE_MATERIAL_EXTENSIONS.get(
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


def _write_source_materials_manifest(
    *,
    project_dir: Path,
    project_slug: str,
    source_dir: str,
    max_depth: int,
    include_markdown: bool,
    include_project_files: bool,
) -> tuple[Path, Path, dict[str, Any]]:
    """Scan workspace inputs and write Phase 0 source-material artifacts."""
    scan_root, workspace_root = _resolve_source_scan_root(source_dir, project_dir)
    audit_dir = project_dir / ".audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    files = _iter_source_material_files(
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
    manifest = {
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

    manifest_path = audit_dir / "source-materials.yaml"
    manifest_path.write_text(
        yaml.dump(manifest, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    report_path = audit_dir / "source-materials.md"
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
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return manifest_path, report_path, manifest


def _parse_json_list(raw: str, field_name: str) -> tuple[list[Any], str]:
    """Parse a JSON list/dict field for facade inputs."""
    if not raw.strip():
        return [], ""
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [], f"invalid {field_name} JSON: {exc.msg}"
    if isinstance(loaded, list):
        return loaded, ""
    if isinstance(loaded, dict):
        if isinstance(loaded.get("sections"), list):
            return loaded["sections"], ""
        if isinstance(loaded.get("items"), list):
            return loaded["items"], ""
        return list(loaded.keys()), ""
    return [], f"{field_name} must be a JSON list or object"


def _refresh_source_materials_summary(manifest: dict[str, Any]) -> None:
    """Refresh summary and next-step fields after ingestion receipt updates."""
    materials = manifest.get("materials", [])
    if not isinstance(materials, list):
        materials = []
        manifest["materials"] = materials

    pending = [
        entry
        for entry in materials
        if isinstance(entry, dict)
        and entry.get("ingestion", {}).get("status") == "pending_asset_aware"
    ]
    manifest["summary"] = {
        "total_candidates": len(materials),
        "pending_asset_aware": len(pending),
        "ready_native": len(materials) - len(pending),
        "ingested_asset_aware": len(
            [
                entry
                for entry in materials
                if isinstance(entry, dict)
                and entry.get("ingestion", {}).get("status") == "ingested_asset_aware"
            ]
        ),
    }
    manifest["agent_next_steps"] = {
        "asset_aware_required": bool(pending),
        "asset_aware_file_paths": [str(entry.get("path")) for entry in pending if entry.get("path")],
        "instruction": (
            "Call asset-aware ingest_documents on asset_aware_file_paths before Phase 5 "
            "and use extracted tables/sections as primary evidence."
            if pending
            else "No pending asset-aware ingestion remains."
        ),
    }


def _write_source_materials_report_from_manifest(project_dir: Path, manifest: dict[str, Any]) -> Path:
    """Write a compact markdown source-material report from the manifest."""
    report_path = project_dir / ".audit" / "source-materials.md"
    summary = manifest.get("summary", {})
    materials = manifest.get("materials", [])
    lines = [
        "# Source Materials Intake",
        "",
        f"- Schema: `{manifest.get('schema', 'mdpaper.source_materials.v1')}`",
        f"- Scan root: `{manifest.get('scan_root', '')}`",
        f"- Total candidates: {summary.get('total_candidates', 0)}",
        f"- Pending asset-aware ingestion: {summary.get('pending_asset_aware', 0)}",
        f"- Ingested asset-aware materials: {summary.get('ingested_asset_aware', 0)}",
        "",
        "| ID | File | Kind | Ingestion status | Asset-aware doc |",
        "|---|---|---|---|---|",
    ]
    if isinstance(materials, list) and materials:
        for entry in materials:
            if not isinstance(entry, dict):
                continue
            ingestion = entry.get("ingestion") if isinstance(entry.get("ingestion"), dict) else {}
            lines.append(
                "| {id} | {file} | {kind} | {status} | {doc_id} |".format(
                    id=entry.get("id", ""),
                    file=entry.get("relative_path") or entry.get("filename") or "",
                    kind=entry.get("kind", ""),
                    status=ingestion.get("status", ""),
                    doc_id=ingestion.get("asset_aware_doc_id", ""),
                )
            )
    else:
        lines.append("| - | No source materials found | - | - | - |")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def _record_asset_ingestion_receipt(
    *,
    project_dir: Path,
    source_material_id: str,
    source_path: str,
    asset_aware_doc_id: str,
    sections: list[Any],
    artifact_paths: list[Any],
    ingestion_status: str,
) -> tuple[bool, str]:
    """Record an asset-aware ingestion receipt in `.audit/source-materials.yaml`."""
    manifest_path = project_dir / ".audit" / "source-materials.yaml"
    if not manifest_path.is_file():
        return False, "MISSING .audit/source-materials.yaml — run project_action(action=\"source_materials\") first"
    if not asset_aware_doc_id.strip():
        return False, "asset_aware_doc_id is required"

    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return False, f"invalid source-materials.yaml: {exc}"
    if not isinstance(manifest, dict):
        return False, "source-materials.yaml must be a mapping"

    materials = manifest.get("materials", [])
    if not isinstance(materials, list):
        return False, "source-materials.yaml materials must be a list"

    target: dict[str, Any] | None = None
    source_path_text = source_path.strip()
    for entry in materials:
        if not isinstance(entry, dict):
            continue
        refs = {
            str(entry.get("id") or ""),
            str(entry.get("path") or ""),
            str(entry.get("relative_path") or ""),
            str(entry.get("filename") or ""),
        }
        refs.add(Path(str(entry.get("path") or "")).name)
        refs.add(Path(str(entry.get("relative_path") or "")).name)
        if (source_material_id and source_material_id in refs) or (
            source_path_text and source_path_text in refs
        ):
            target = entry
            break

    if target is None:
        return False, "source material not found; pass source_material_id or source_path from source-materials.yaml"

    ingestion = target.setdefault("ingestion", {})
    if not isinstance(ingestion, dict):
        ingestion = {}
        target["ingestion"] = ingestion

    status = ingestion_status.strip() or "ingested_asset_aware"
    ingestion.update(
        {
            "status": status,
            "required": False if status == "ingested_asset_aware" else ingestion.get("required", True),
            "asset_aware_doc_id": asset_aware_doc_id.strip(),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    target["asset_aware_doc_id"] = asset_aware_doc_id.strip()
    if sections:
        target["fulltext_sections"] = sections
        ingestion["sections"] = sections
    if artifact_paths:
        target["asset_aware_artifacts"] = artifact_paths
        ingestion["artifact_paths"] = artifact_paths

    _refresh_source_materials_summary(manifest)
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(
        yaml.dump(manifest, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    report_path = _write_source_materials_report_from_manifest(project_dir, manifest)
    return True, (
        f"recorded ingestion for {target.get('id')} -> {asset_aware_doc_id.strip()}; "
        f"manifest={manifest_path.relative_to(project_dir).as_posix()}; "
        f"report={report_path.relative_to(project_dir).as_posix()}"
    )


def register_project_facade_tools(
    mcp: FastMCP,
    crud_tools: ToolMap,
    settings_tools: ToolMap,
    exploration_tools: ToolMap,
    workspace_state_tools: ToolMap,
    library_tools: ToolMap | None = None,
    diagram_tools: ToolMap | None = None,
    workspace_tools: ToolMap | None = None,
):
    """Register stable public verbs for project and workspace state management."""

    library_tools = library_tools or {}
    diagram_tools = diagram_tools or {}
    workspace_tools = workspace_tools or {}

    @mcp.tool()
    async def project_action(
        action: str,
        name: str = "",
        slug: str = "",
        description: str = "",
        target_journal: str = "",
        paper_type: str = "",
        workflow_mode: str = "",
        authors_json: str = "",
        memo: str = "",
        status: str = "",
        citation_style: str = "",
        interaction_style: str = "",
        language_preference: str = "",
        writing_style: str = "",
        graph_views_json: str = "",
        keep_exploration: bool = False,
        include_files: bool = False,
        confirm: bool = False,
        filename: str = "",
        content: str = "",
        content_format: str = "xml",
        output_dir: str = "",
        rendered_content: str = "",
        rendered_format: str = "",
        rendered_content_format: str = "auto",
        rendered_filename: str = "",
        source_dir: str = "",
        source_material_id: str = "",
        source_path: str = "",
        asset_aware_doc_id: str = "",
        sections_json: str = "",
        artifact_paths_json: str = "",
        ingestion_status: str = "",
        max_depth: int = 3,
        include_markdown: bool = False,
        include_project_files: bool = False,
        ctx: Context | None = None,
    ) -> str:
        """
        Run consolidated project-management actions through one stable entrypoint.

        Actions:
        - create
        - list
        - switch
        - current
        - update
        - setup
        - update_authors
        - journal_profile
        - source_materials
        - record_asset_ingestion
        - start_exploration
        - convert_exploration
        - archive
        - delete
        - save_diagram
        - list_diagrams
        - open_files
        """
        aliases = {
            "actions": "help",
            "get": "current",
            "help": "help",
            "journal": "journal_profile",
            "journal_profile": "journal_profile",
            "create_journal_profile": "journal_profile",
            "profile": "journal_profile",
            "materials": "source_materials",
            "scan_materials": "source_materials",
            "scan_source_materials": "source_materials",
            "source_materials": "source_materials",
            "sources": "source_materials",
            "asset_ingestion": "record_asset_ingestion",
            "ingestion_receipt": "record_asset_ingestion",
            "record_asset_ingestion": "record_asset_ingestion",
            "settings": "update",
            "supported": "help",
            "configure": "setup",
            "explore": "start_exploration",
            "convert": "convert_exploration",
            "authors": "update_authors",
            "diagram_save": "save_diagram",
            "diagram_list": "list_diagrams",
            "open": "open_files",
        }
        normalized = normalize_facade_action(action, aliases)

        action_specs: dict[str, tuple[ToolMap, str, dict[str, Any]]] = {
            "create": (
                crud_tools,
                "create_project",
                {
                    "name": name,
                    "description": description,
                    "target_journal": target_journal,
                    "paper_type": paper_type,
                    "workflow_mode": workflow_mode,
                    "authors_json": authors_json,
                    "memo": memo,
                },
            ),
            "journal_profile": (
                {},
                "create_journal_profile",
                {
                    "slug": slug,
                    "target_journal": target_journal,
                    "paper_type": paper_type,
                    "citation_style": citation_style,
                    "language_preference": language_preference,
                    "writing_style": writing_style,
                },
            ),
            "source_materials": (
                {},
                "scan_source_materials",
                {
                    "slug": slug,
                    "source_dir": source_dir,
                    "max_depth": max_depth,
                    "include_markdown": include_markdown,
                    "include_project_files": include_project_files,
                },
            ),
            "record_asset_ingestion": (
                {},
                "record_asset_ingestion",
                {
                    "slug": slug,
                    "source_material_id": source_material_id,
                    "source_path": source_path,
                    "asset_aware_doc_id": asset_aware_doc_id,
                    "sections_json": sections_json,
                    "artifact_paths_json": artifact_paths_json,
                    "ingestion_status": ingestion_status,
                },
            ),
            "list": (crud_tools, "list_projects", {}),
            "switch": (crud_tools, "switch_project", {"slug": slug}),
            "current": (
                crud_tools,
                "get_current_project",
                {"include_files": include_files},
            ),
            "update": (
                settings_tools,
                "update_project_settings",
                {
                    "paper_type": paper_type,
                    "target_journal": target_journal,
                    "interaction_style": interaction_style,
                    "language_preference": language_preference,
                    "writing_style": writing_style,
                    "graph_views_json": graph_views_json,
                    "memo": memo,
                    "status": status,
                    "citation_style": citation_style,
                    **({"workflow_mode": workflow_mode} if workflow_mode else {}),
                },
            ),
            "setup": (
                settings_tools,
                "setup_project_interactive",
                {"ctx": ctx},
            ),
            "update_authors": (
                settings_tools,
                "update_authors",
                {"authors_json": authors_json},
            ),
            "start_exploration": (exploration_tools, "start_exploration", {}),
            "convert_exploration": (
                exploration_tools,
                "convert_exploration_to_project",
                {
                    "name": name,
                    "description": description,
                    "paper_type": paper_type,
                    "workflow_mode": workflow_mode,
                    "target_journal": target_journal,
                    "keep_exploration": keep_exploration,
                },
            ),
            "archive": (
                crud_tools,
                "archive_project",
                {"slug": slug, "confirm": confirm},
            ),
            "delete": (
                crud_tools,
                "delete_project",
                {"slug": slug, "confirm": confirm},
            ),
            "save_diagram": (
                diagram_tools,
                "save_diagram",
                {
                    "filename": filename,
                    "content": content,
                    "project": slug or None,
                    "content_format": content_format,
                    "description": description,
                    "output_dir": output_dir,
                    "rendered_content": rendered_content,
                    "rendered_format": rendered_format,
                    "rendered_content_format": rendered_content_format,
                    "rendered_filename": rendered_filename,
                },
            ),
            "list_diagrams": (
                diagram_tools,
                "list_diagrams",
                {"project": slug or None},
            ),
            "open_files": (
                workspace_tools,
                "open_project_files",
                {"project_slug": slug or None},
            ),
        }

        if normalized == "help":
            return facade_schema_json(
                tool="project_action",
                actions={
                    name: {"handler": spec[1], "params": sorted(k for k in spec[2] if k != "ctx")}
                    for name, spec in sorted(action_specs.items())
                },
                aliases=aliases,
                notes=["Use action='list' to list projects; use action='current' for active project."],
            )

        if normalized == "journal_profile":
            project_info, workflow_error = resolve_project_context(slug or None)
            if workflow_error or project_info is None:
                return workflow_error or "❌ Project context could not be resolved."
            project_dir = Path(project_info["project_path"])
            profile = _build_journal_profile(
                target_journal=target_journal or project_info.get("target_journal", ""),
                paper_type=paper_type or project_info.get("paper_type", ""),
                citation_style=citation_style,
                language_preference=language_preference,
                writing_style=writing_style,
            )
            profile_path = project_dir / "journal-profile.yaml"
            profile_path.write_text(
                yaml.dump(profile, default_flow_style=False, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            return (
                "status: ok\n"
                "action: journal_profile\n"
                f"file: {profile_path.relative_to(project_dir).as_posix()}\n"
                f"journal: {profile['journal']['name']}\n"
                f"paper_type: {profile['paper']['type']}\n"
                f"citation_style: {profile['references']['style']}\n"
                "next: project_action(action=\"source_materials\"), then pipeline_action(action=\"validate_phase\", phase=0)"
            )

        if normalized == "source_materials":
            project_info, workflow_error = resolve_project_context(slug or None)
            if workflow_error or project_info is None:
                return workflow_error or "❌ Project context could not be resolved."
            project_dir = Path(project_info["project_path"])
            manifest_path, report_path, manifest = _write_source_materials_manifest(
                project_dir=project_dir,
                project_slug=str(project_info.get("slug", slug or project_dir.name)),
                source_dir=source_dir,
                max_depth=max_depth,
                include_markdown=include_markdown,
                include_project_files=include_project_files,
            )
            summary = manifest["summary"]
            pending_paths = manifest["agent_next_steps"]["asset_aware_file_paths"][:10]
            pending_lines = "\n".join(f"  - {path}" for path in pending_paths)
            if not pending_lines:
                pending_lines = "  []"
            return (
                "status: ok\n"
                "action: source_materials\n"
                f"manifest: {manifest_path.relative_to(project_dir).as_posix()}\n"
                f"report: {report_path.relative_to(project_dir).as_posix()}\n"
                f"scan_root: {manifest['scan_root']}\n"
                f"total_candidates: {summary['total_candidates']}\n"
                f"pending_asset_aware: {summary['pending_asset_aware']}\n"
                f"ready_native: {summary['ready_native']}\n"
                "asset_aware_file_paths:\n"
                f"{pending_lines}\n"
                "next: call asset-aware ingest_documents for pending paths, then pipeline_action(action=\"validate_phase\", phase=0)"
            )

        if normalized == "record_asset_ingestion":
            project_info, workflow_error = resolve_project_context(slug or None)
            if workflow_error or project_info is None:
                return workflow_error or "❌ Project context could not be resolved."
            sections, sections_error = _parse_json_list(sections_json, "sections_json")
            if sections_error:
                return f"❌ {sections_error}"
            artifact_paths, artifact_error = _parse_json_list(
                artifact_paths_json,
                "artifact_paths_json",
            )
            if artifact_error:
                return f"❌ {artifact_error}"

            ok, message = _record_asset_ingestion_receipt(
                project_dir=Path(project_info["project_path"]),
                source_material_id=source_material_id,
                source_path=source_path,
                asset_aware_doc_id=asset_aware_doc_id,
                sections=sections,
                artifact_paths=artifact_paths,
                ingestion_status=ingestion_status,
            )
            if not ok:
                return f"❌ {message}"
            return (
                "status: ok\n"
                "action: record_asset_ingestion\n"
                f"{message}\n"
                "next: pipeline_action(action=\"validate_phase\", phase=21)"
            )

        if normalized not in action_specs:
            supported = ", ".join(sorted(action_specs))
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        tool_group, handler_name, kwargs = action_specs[normalized]
        handler = tool_group.get(handler_name)
        if handler is None:
            return f"❌ Project facade misconfigured: missing handler '{handler_name}'"

        return await invoke_tool_handler(handler, **kwargs)

    @mcp.tool()
    async def library_action(
        action: str,
        section: str = "all",
        from_section: str = "",
        to_section: str = "",
        filename: str = "",
        content: str = "",
        title: str = "",
        tags_csv: str = "",
        add_tags_csv: str = "",
        remove_tags_csv: str = "",
        related_notes_csv: str = "",
        source_notes_csv: str = "",
        template: str = "",
        note_type: str = "",
        status: str = "",
        query: str = "",
        queue: str = "all",
        view: str = "overview",
        limit: int = 10,
        source_note: str = "",
        target_note: str = "",
        project: Optional[str] = None,
    ) -> str:
        """
        Run library-wiki note and dashboard actions through one stable entrypoint.

        Actions:
        - list_notes
        - read_note
        - write_note
        - move_note
        - triage_note
        - update_metadata
        - search_notes
        - show_queues
        - create_concept
        - materialize_concept
        - explain_path
        - build_dashboard
        """
        aliases = {
            "list": "list_notes",
            "read": "read_note",
            "write": "write_note",
            "move": "move_note",
            "triage": "triage_note",
            "metadata": "update_metadata",
            "frontmatter": "update_metadata",
            "search": "search_notes",
            "queues": "show_queues",
            "concept": "create_concept",
            "materialize": "materialize_concept",
            "path": "explain_path",
            "dashboard": "build_dashboard",
        }
        normalized = normalize_facade_action(action, aliases)
        action_specs: dict[str, tuple[str, dict[str, Any]]] = {
            "list_notes": (
                "list_library_notes",
                {"section": section, "project": project},
            ),
            "read_note": (
                "read_library_note",
                {"section": section, "filename": filename, "project": project},
            ),
            "write_note": (
                "write_library_note",
                {
                    "section": section,
                    "filename": filename,
                    "content": content,
                    "title": title,
                    "tags_csv": tags_csv,
                    "template": template,
                    "source_notes_csv": source_notes_csv,
                    "related_notes_csv": related_notes_csv,
                    "status": status,
                    "project": project,
                },
            ),
            "move_note": (
                "move_library_note",
                {
                    "filename": filename,
                    "from_section": from_section,
                    "to_section": to_section,
                    "project": project,
                },
            ),
            "triage_note": (
                "triage_library_note",
                {
                    "note_ref": source_note or filename,
                    "target_section": to_section or (section if section != "all" else ""),
                    "status": status,
                    "tags_csv": tags_csv,
                    "related_notes_csv": related_notes_csv,
                    "project": project,
                },
            ),
            "update_metadata": (
                "update_library_note_metadata",
                {
                    "note_ref": source_note or filename,
                    "title": title,
                    "status": status,
                    "tags_csv": tags_csv,
                    "add_tags_csv": add_tags_csv,
                    "remove_tags_csv": remove_tags_csv,
                    "related_notes_csv": related_notes_csv,
                    "note_type": note_type,
                    "project": project,
                },
            ),
            "search_notes": (
                "search_library_notes",
                {"query": query, "section": section, "project": project},
            ),
            "show_queues": (
                "show_reading_queues",
                {"queue": queue, "limit": limit, "project": project},
            ),
            "create_concept": (
                "create_concept_page",
                {
                    "filename": filename,
                    "title": title,
                    "summary": content,
                    "source_notes_csv": source_notes_csv or query,
                    "tags_csv": tags_csv,
                    "open_questions": status,
                    "project": project,
                },
            ),
            "materialize_concept": (
                "materialize_concept_page",
                {
                    "filename": filename,
                    "title": title,
                    "summary": content,
                    "source_notes_csv": query or source_note or filename,
                    "tags_csv": tags_csv,
                    "open_questions": status,
                    "project": project,
                },
            ),
            "explain_path": (
                "explain_library_path",
                {
                    "source_note": source_note or filename,
                    "target_note": target_note or query,
                    "project": project,
                },
            ),
            "build_dashboard": (
                "build_library_dashboard",
                {"view": view, "limit": limit, "project": project},
            ),
        }

        if normalized not in action_specs:
            supported = ", ".join(sorted(action_specs))
            return f"❌ Unsupported action '{action}'. Supported actions: {supported}"

        handler_name, kwargs = action_specs[normalized]
        handler = library_tools.get(handler_name)
        if handler is None:
            return f"❌ Library facade misconfigured: missing handler '{handler_name}'"

        return await invoke_tool_handler(handler, **kwargs)

    @mcp.tool(structured_output=True)
    async def workspace_state_action(
        action: str,
        doing: Optional[str] = None,
        next_action: Optional[str] = None,
        context: Optional[str] = None,
        clear: bool = False,
        section: str = "",
        plan: str = "",
        notes: str = "",
        references_in_use: str = "",
    ) -> dict[str, Any]:
        """
        Manage workspace recovery state through one stable entrypoint.

        Actions:
        - get
        - sync
        - checkpoint
        """
        aliases = {
            "actions": "list",
            "help": "list",
            "recover": "get",
            "save": "sync",
            "supported": "list",
        }
        normalized = normalize_facade_action(action, aliases)

        if normalized == "list":
            return {
                "status": "ok",
                "action": "list",
                "schema": "mdpaper.facade_actions.v1",
                "tool": "workspace_state_action",
                "actions": {
                    "get": {"handler": "get_workspace_state", "params": []},
                    "sync": {
                        "handler": "sync_workspace_state",
                        "params": ["doing", "next_action", "context", "clear"],
                    },
                    "checkpoint": {
                        "handler": "checkpoint_writing_context",
                        "params": ["section", "plan", "notes", "references_in_use"],
                    },
                },
                "aliases": aliases,
            }

        if normalized == "get":
            handler = workspace_state_tools.get("get_workspace_state")
            if handler is None:
                return {"status": "error", "message": "Missing handler 'get_workspace_state'"}
            result = await invoke_tool_handler(handler)
            return {"status": "ok", "action": "get", **result}

        if normalized == "sync":
            handler = workspace_state_tools.get("sync_workspace_state")
            if handler is None:
                return {"status": "error", "message": "Missing handler 'sync_workspace_state'"}
            message = await invoke_tool_handler(
                handler,
                doing=doing,
                next_action=next_action,
                context=context,
                clear=clear,
            )
            return {"status": "ok", "action": "sync", "message": message}

        if normalized == "checkpoint":
            handler = workspace_state_tools.get("checkpoint_writing_context")
            if handler is None:
                return {
                    "status": "error",
                    "message": "Missing handler 'checkpoint_writing_context'",
                }
            message = await invoke_tool_handler(
                handler,
                section=section,
                plan=plan,
                notes=notes,
                references_in_use=references_in_use,
            )
            return {"status": "ok", "action": "checkpoint", "message": message}

        return {
            "status": "error",
            "message": (
                f"Unsupported action '{action}'. Supported actions: checkpoint, get, list, sync"
            ),
        }

    return {
        "library_action": library_action,
        "project_action": project_action,
        "workspace_state_action": workspace_state_action,
    }
