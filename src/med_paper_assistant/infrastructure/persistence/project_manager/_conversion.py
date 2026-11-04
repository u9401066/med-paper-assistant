"""Conversion of the temporary exploration workspace into a formal project."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, NamedTuple, Optional, Union

from ....domain.paper_types import is_valid_paper_type, list_paper_types
from ....shared.constants import WORKFLOW_MODES
from ..project_memory_manager import ProjectMemoryManager
from ..project_transfer import transfer_project_tree


class ConversionPlan(NamedTuple):
    """Validated inputs for converting the exploration workspace."""

    temp_path: Path
    temp_stats: Dict[str, int]
    slug: str
    path: Path
    workflow_mode: str


def plan_conversion(
    manager: Any, name: str, paper_type: str, workflow_mode: str
) -> Union[ConversionPlan, Dict[str, Any]]:
    """Validate a conversion request, or return an error result."""
    temp_path = manager.projects_dir / manager.TEMP_PROJECT_SLUG

    if not temp_path.exists():
        return {
            "success": False,
            "error": "No temporary exploration project found. Use get_or_create_temp_project first.",
        }

    # Get temp project stats before conversion
    temp_stats = manager._get_project_stats(temp_path)

    # Create the new project
    try:
        new_slug, new_path = manager._project_path_for_slug(manager._slugify(name))
    except ValueError as exc:
        return {"success": False, "error": f"Invalid project name: {exc}"}

    if new_path.exists():
        return {
            "success": False,
            "error": f"Project '{new_slug}' already exists. Choose a different name.",
        }

    # Validate paper_type if provided
    if paper_type and not is_valid_paper_type(paper_type):
        return {
            "success": False,
            "error": f"Invalid paper type '{paper_type}'. Valid types: {list_paper_types()}",
        }

    resolved_workflow_mode = workflow_mode or ("manuscript" if paper_type else "library-wiki")
    if resolved_workflow_mode not in WORKFLOW_MODES:
        return {
            "success": False,
            "error": f"Invalid workflow mode '{resolved_workflow_mode}'. Valid modes: {list(WORKFLOW_MODES)}",
        }

    return ConversionPlan(temp_path, temp_stats, new_slug, new_path, resolved_workflow_mode)


def _write_converted_documents(
    manager: Any,
    plan: ConversionPlan,
    name: str,
    paper_type: str,
    target_journal: str,
) -> None:
    # Update concept.md or library workspace seed
    concept_content = manager._build_workspace_seed_document(
        project_name=name,
        paper_type=paper_type,
        target_journal=target_journal,
        memo=f"Converted from exploration workspace.\nReferences: {plan.temp_stats['references']}",
        workflow_mode=plan.workflow_mode,
    )
    (plan.path / "concept.md").write_text(concept_content, encoding="utf-8")

    # Update memory files
    memory_manager = ProjectMemoryManager(plan.path)
    memory_manager.create_memory_files(
        project_name=name,
        paper_type=paper_type,
        workflow_mode=plan.workflow_mode,
        interaction_preferences=None,
        memo=f"Converted from temp exploration project with {plan.temp_stats['references']} references.",
    )


def execute_conversion(
    manager: Any,
    plan: ConversionPlan,
    name: str,
    description: str,
    paper_type: str,
    target_journal: str,
    keep_temp: bool,
) -> Optional[Dict[str, Any]]:
    """Move or copy the exploration workspace; return an error result on failure."""
    try:
        transfer_project_tree(plan.temp_path, plan.path, keep_temp=keep_temp)
    except OSError as exc:
        return {"success": False, "error": f"Conversion failed: {exc}"}

    # Update the config for the new project
    config = manager._create_project_config(
        name=name,
        slug=plan.slug,
        description=description
        or f"Converted from exploration workspace with {plan.temp_stats['references']} references",
        authors=None,
        target_journal=target_journal,
        paper_type=paper_type,
        workflow_mode=plan.workflow_mode,
        interaction_preferences=None,
        memo=f"Originally explored as temp project. Converted on {datetime.now().strftime('%Y-%m-%d')}.",
    )
    manager._save_config(plan.path, config)

    # Ensure the target workflow layout exists even when the source exploration
    # workspace was created with a different directory shape.
    for subdir in manager._directories_for_workflow(plan.workflow_mode):
        (plan.path / subdir).mkdir(exist_ok=True)

    _write_converted_documents(manager, plan, name, paper_type, target_journal)
    return None


def finish_conversion(manager: Any, plan: ConversionPlan, name: str) -> Dict[str, Any]:
    """Activate the converted project and build the success result."""
    # Switch to new project
    manager._save_current_project(plan.slug)

    # Keep Foam project isolation and graph nodes aligned with the converted project.
    manager._update_foam_settings(plan.slug)
    manager._refresh_foam_graph()

    converted_stats = manager._get_project_stats(plan.path)
    conversion_summary = manager._build_conversion_message(plan.workflow_mode, converted_stats)

    return {
        "success": True,
        "message": f"✅ 成功將探索工作區轉換為正式專案！\n\n"
        f"📁 新專案: **{name}**\n"
        f"📚 轉移內容:\n"
        f"{conversion_summary}",
        "slug": plan.slug,
        "path": str(plan.path),
        "workflow_mode": plan.workflow_mode,
        "stats": converted_stats,
        "paths": manager.get_project_paths(plan.slug),
    }
