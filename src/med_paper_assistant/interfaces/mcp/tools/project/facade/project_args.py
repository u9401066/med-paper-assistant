"""Arguments and aliases for the ``project_action`` facade."""

from __future__ import annotations

from dataclasses import dataclass

from mcp.server.mcpserver import Context

PROJECT_ALIASES = {
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
    "exemplar": "exemplar_usage",
    "exemplars": "exemplar_usage",
    "record_exemplar": "exemplar_usage",
    "record_exemplar_usage": "exemplar_usage",
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


@dataclass(frozen=True)
class ProjectActionArgs:
    """The ``project_action`` tool parameters, captured once per call."""

    action: str
    name: str
    slug: str
    description: str
    target_journal: str
    paper_type: str
    workflow_mode: str
    authors_json: str
    memo: str
    status: str
    citation_style: str
    interaction_style: str
    language_preference: str
    writing_style: str
    graph_views_json: str
    keep_exploration: bool
    include_files: bool
    confirm: bool
    filename: str
    content: str
    content_format: str
    output_dir: str
    rendered_content: str
    rendered_format: str
    rendered_content_format: str
    rendered_filename: str
    source_dir: str
    source_material_id: str
    source_path: str
    exemplar_source_id: str
    exemplar_roles_json: str
    exemplar_target_sections_json: str
    exemplar_purpose: str
    exemplar_source_sha256: str
    asset_aware_doc_id: str
    sections_json: str
    artifact_paths_json: str
    ingestion_status: str
    max_depth: int
    include_markdown: bool
    include_project_files: bool
    ctx: Context | None
