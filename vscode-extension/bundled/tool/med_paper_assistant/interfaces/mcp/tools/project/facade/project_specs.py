"""Action table for the ``project_action`` facade."""

from __future__ import annotations

from typing import Any

from med_paper_assistant.shared.constants import DEFAULT_WORKFLOW_MODE

from .deps import FacadeDeps, ToolMap
from .project_args import ProjectActionArgs

ActionSpec = tuple[ToolMap, str, dict[str, Any]]


def _project_crud_specs(a: ProjectActionArgs, deps: FacadeDeps) -> dict[str, ActionSpec]:
    crud = deps.crud_tools
    return {
        "create": (
            crud,
            "create_project",
            {
                "name": a.name,
                "description": a.description,
                "target_journal": a.target_journal,
                "paper_type": a.paper_type,
                "workflow_mode": a.workflow_mode or DEFAULT_WORKFLOW_MODE,
                "authors_json": a.authors_json,
                "memo": a.memo,
            },
        ),
        "list": (crud, "list_projects", {}),
        "switch": (crud, "switch_project", {"slug": a.slug}),
        "current": (crud, "get_current_project", {"include_files": a.include_files}),
        "archive": (crud, "archive_project", {"slug": a.slug, "confirm": a.confirm}),
        "delete": (crud, "delete_project", {"slug": a.slug, "confirm": a.confirm}),
    }


def _inline_action_specs(a: ProjectActionArgs) -> dict[str, ActionSpec]:
    return {**_intake_specs(a), **_ingestion_specs(a)}


def _intake_specs(a: ProjectActionArgs) -> dict[str, ActionSpec]:
    return {
        "journal_profile": (
            {},
            "create_journal_profile",
            {
                "slug": a.slug,
                "target_journal": a.target_journal,
                "paper_type": a.paper_type,
                "citation_style": a.citation_style,
                "language_preference": a.language_preference,
                "writing_style": a.writing_style,
            },
        ),
        "source_materials": (
            {},
            "scan_source_materials",
            {
                "slug": a.slug,
                "source_dir": a.source_dir,
                "max_depth": a.max_depth,
                "include_markdown": a.include_markdown,
                "include_project_files": a.include_project_files,
            },
        ),
    }


def _ingestion_specs(a: ProjectActionArgs) -> dict[str, ActionSpec]:
    return {
        "record_asset_ingestion": (
            {},
            "record_asset_ingestion",
            {
                "slug": a.slug,
                "source_material_id": a.source_material_id,
                "source_path": a.source_path,
                "asset_aware_doc_id": a.asset_aware_doc_id,
                "sections_json": a.sections_json,
                "artifact_paths_json": a.artifact_paths_json,
                "ingestion_status": a.ingestion_status,
            },
        ),
        "exemplar_usage": (
            {},
            "record_or_list_exemplar_usage",
            {
                "slug": a.slug,
                "exemplar_source_id": a.exemplar_source_id,
                "exemplar_roles_json": a.exemplar_roles_json,
                "exemplar_target_sections_json": a.exemplar_target_sections_json,
                "exemplar_purpose": a.exemplar_purpose,
                "exemplar_source_sha256": a.exemplar_source_sha256,
            },
        ),
    }


def _settings_specs(a: ProjectActionArgs, deps: FacadeDeps) -> dict[str, ActionSpec]:
    settings = deps.settings_tools
    return {
        "update": (
            settings,
            "update_project_settings",
            {
                "paper_type": a.paper_type,
                "target_journal": a.target_journal,
                "interaction_style": a.interaction_style,
                "language_preference": a.language_preference,
                "writing_style": a.writing_style,
                "graph_views_json": a.graph_views_json,
                "memo": a.memo,
                "status": a.status,
                "citation_style": a.citation_style,
                **({"workflow_mode": a.workflow_mode} if a.workflow_mode else {}),
            },
        ),
        "setup": (settings, "setup_project_interactive", {"ctx": a.ctx}),
        "update_authors": (settings, "update_authors", {"authors_json": a.authors_json}),
    }


def _exploration_specs(a: ProjectActionArgs, deps: FacadeDeps) -> dict[str, ActionSpec]:
    exploration = deps.exploration_tools
    return {
        "start_exploration": (exploration, "start_exploration", {}),
        "convert_exploration": (
            exploration,
            "convert_exploration_to_project",
            {
                "name": a.name,
                "description": a.description,
                "paper_type": a.paper_type,
                "workflow_mode": a.workflow_mode,
                "target_journal": a.target_journal,
                "keep_exploration": a.keep_exploration,
            },
        ),
    }


def _diagram_and_workspace_specs(a: ProjectActionArgs, deps: FacadeDeps) -> dict[str, ActionSpec]:
    return {
        "save_diagram": (
            deps.diagram_tools,
            "save_diagram",
            {
                "filename": a.filename,
                "content": a.content,
                "project": a.slug or None,
                "content_format": a.content_format,
                "description": a.description,
                "output_dir": a.output_dir,
                "rendered_content": a.rendered_content,
                "rendered_format": a.rendered_format,
                "rendered_content_format": a.rendered_content_format,
                "rendered_filename": a.rendered_filename,
            },
        ),
        "list_diagrams": (deps.diagram_tools, "list_diagrams", {"project": a.slug or None}),
        "open_files": (
            deps.workspace_tools,
            "open_project_files",
            {"project_slug": a.slug or None},
        ),
    }


def build_project_action_specs(a: ProjectActionArgs, deps: FacadeDeps) -> dict[str, ActionSpec]:
    """Map each public action to ``(tool group, handler name, handler kwargs)``."""
    crud = _project_crud_specs(a, deps)
    inline = _inline_action_specs(a)
    settings = _settings_specs(a, deps)
    exploration = _exploration_specs(a, deps)
    return {
        "create": crud["create"],
        **inline,
        "list": crud["list"],
        "switch": crud["switch"],
        "current": crud["current"],
        **settings,
        **exploration,
        "archive": crud["archive"],
        "delete": crud["delete"],
        **_diagram_and_workspace_specs(a, deps),
    }
