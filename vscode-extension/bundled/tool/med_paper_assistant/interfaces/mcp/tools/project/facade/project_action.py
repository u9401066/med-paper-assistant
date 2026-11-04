"""``project_action`` facade handler."""

from __future__ import annotations

from mcp.server.mcpserver import Context

from ..._shared import facade_schema_json, invoke_tool_handler, normalize_facade_action
from .deps import FACADE_DEPS, FacadeDeps
from .project_args import PROJECT_ALIASES, ProjectActionArgs
from .project_inline import INLINE_ACTIONS
from .project_specs import ActionSpec, build_project_action_specs


def _help_schema(action_specs: dict[str, ActionSpec]) -> str:
    return facade_schema_json(
        tool="project_action",
        actions={
            name: {"handler": spec[1], "params": sorted(k for k in spec[2] if k != "ctx")}
            for name, spec in sorted(action_specs.items())
        },
        aliases=dict(PROJECT_ALIASES),
        notes=["Use action='list' to list projects; use action='current' for active project."],
    )


async def _dispatch_project_action(args: ProjectActionArgs, deps: FacadeDeps) -> str:
    normalized = normalize_facade_action(args.action, PROJECT_ALIASES)
    action_specs = build_project_action_specs(args, deps)

    if normalized == "help":
        return _help_schema(action_specs)

    inline_action = INLINE_ACTIONS.get(normalized)
    if inline_action is not None:
        return inline_action(args)

    if normalized not in action_specs:
        supported = ", ".join(sorted(action_specs))
        return f"❌ Unsupported action '{args.action}'. Supported actions: {supported}"

    tool_group, handler_name, kwargs = action_specs[normalized]
    handler = tool_group.get(handler_name)
    if handler is None:
        return f"❌ Project facade misconfigured: missing handler '{handler_name}'"

    return await invoke_tool_handler(handler, **kwargs)


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
    exemplar_source_id: str = "",
    exemplar_roles_json: str = "",
    exemplar_target_sections_json: str = "",
    exemplar_purpose: str = "",
    exemplar_source_sha256: str = "",
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
    - exemplar_usage
    - start_exploration
    - convert_exploration
    - archive
    - delete
    - save_diagram
    - list_diagrams
    - open_files
    """
    args = ProjectActionArgs(**locals())
    return await _dispatch_project_action(args, FACADE_DEPS.get())
