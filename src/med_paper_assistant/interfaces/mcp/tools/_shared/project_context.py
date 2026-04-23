"""
Project Context Validation Module

Provides utilities to validate project context before MCP tool execution.
This ensures Agent always operates on the correct project.
"""

import os
from typing import Any, Dict, Optional, Tuple

from med_paper_assistant.infrastructure.persistence import get_project_manager
from med_paper_assistant.shared.constants import DEFAULT_WORKFLOW_MODE, WORKFLOW_MODES


class ProjectContextError(Exception):
    """Raised when project context validation fails."""

    pass


def get_current_project_info() -> Dict[str, Any]:
    """
    Get current project information.

    Returns:
        Dict with project info or empty dict if no project active.
    """
    pm = get_project_manager()
    current_slug = pm.get_current_project()
    if current_slug:
        return pm.get_project_info(current_slug)
    return {}


def validate_project_slug(project_slug: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Validate that a project slug exists and return project info.

    Args:
        project_slug: The project slug to validate.

    Returns:
        Tuple of (is_valid, message, project_info)
    """
    pm = get_project_manager()
    projects = pm.list_projects().get("projects", [])

    for p in projects:
        if p.get("slug") == project_slug:
            return True, f"Project '{p.get('name')}' found", p

    # Project not found - provide helpful error
    available = [p.get("slug") for p in projects]
    if available:
        return False, f"Project '{project_slug}' not found. Available: {', '.join(available)}", None
    else:
        return False, "No projects exist. Create one first with create_project().", None


def ensure_project_context(project_slug: Optional[str] = None) -> Tuple[bool, str, Optional[Dict]]:
    """
    Ensure we have a valid project context.

    If project_slug is provided, validate it exists and switch to it.
    If not provided, check if there's an active project.

    Args:
        project_slug: Optional project slug to validate and switch to.

    Returns:
        Tuple of (is_valid, message, project_info)
    """
    pm = get_project_manager()

    if project_slug:
        # Validate the specified project
        is_valid, msg, project_info = validate_project_slug(project_slug)
        if not is_valid or project_info is None:
            return False, msg, None

        # Switch to the project if not already active
        current_slug = pm.get_current_project()  # Returns str, not dict
        if current_slug != project_slug:
            switch_result = pm.switch_project(project_slug)
            if not switch_result.get("success"):
                return False, f"Failed to switch to project: {switch_result.get('error')}", None

        # Return updated project info
        return (
            True,
            f"Working on project: {project_info.get('name')}",
            pm.get_project_info(project_slug),
        )

    else:
        # No project specified - check if we have an active project
        current_slug = pm.get_current_project()  # Returns str, not dict
        if current_slug:
            project_info = pm.get_project_info(current_slug)
            return True, f"Current project: {project_info.get('name', current_slug)}", project_info
        else:
            # Check if any projects exist
            projects = pm.list_projects().get("projects", [])
            if projects:
                slugs = [p.get("slug") for p in projects]
                return False, f"No active project. Please specify one of: {', '.join(slugs)}", None
            else:
                return False, "No projects exist. Create one first with create_project().", None


def format_project_context_error(message: str, available_projects: Optional[list] = None) -> str:
    """Format a helpful error message for project context issues."""
    lines = ["⚠️ **Project Context Required**\n", message]

    if available_projects:
        lines.append("\n**Available projects:**")
        for p in available_projects:
            status = p.get("status", "unknown")
            lines.append(f"- `{p.get('slug')}` - {p.get('name')} ({status})")

    lines.append("\n**To specify a project, include `project` parameter in your tool call.**")

    return "\n".join(lines)


def get_project_list_for_prompt() -> str:
    """
    Get a formatted list of projects for Agent to present to user.

    Returns:
        Formatted string listing available projects.
    """
    pm = get_project_manager()
    result = pm.list_projects()
    projects = result.get("projects", [])
    current_slug = result.get("current")

    if not projects:
        return "No projects available. Create one with create_project()."

    lines = ["**Available Projects:**"]
    for p in projects:
        marker = "→ " if p.get("slug") == current_slug else "  "
        status_emoji = {
            "concept": "💡",
            "drafting": "✍️",
            "review": "🔍",
            "submitted": "📤",
            "published": "📗",
        }.get(p.get("status", ""), "❓")
        lines.append(f"{marker}`{p.get('slug')}` - {p.get('name')} {status_emoji}")

    return "\n".join(lines)


# ─── Shared path helpers (used by draft/writing, draft/editing, draft/templates) ───


def get_project_path() -> Optional[str]:
    """Get the current project's root directory path."""
    pm = get_project_manager()
    current_info = pm.get_project_info()
    if current_info and current_info.get("project_path"):
        return str(current_info["project_path"])
    return None


def get_drafts_dir() -> Optional[str]:
    """Get the current project's drafts directory."""
    project_path = get_project_path()
    if project_path:
        return os.path.join(project_path, "drafts")
    return None


def get_concept_path() -> Optional[str]:
    """Get the path to the current project's concept.md file."""
    project_path = get_project_path()
    if project_path:
        return os.path.join(project_path, "concept.md")
    return None


def validate_project_for_tool(project: Optional[str] = None) -> tuple[bool, str]:
    """Validate project context before tool operations.

    Returns:
        (is_valid, error_message) — error_message is empty string when valid.
    """
    is_valid, msg, _project_info = ensure_project_context(project)
    if not is_valid:
        return False, f"❌ {msg}\n\n{get_project_list_for_prompt()}"
    return True, ""


def validate_project_for_workflow(
    project: Optional[str] = None,
    *,
    required_mode: str,
) -> tuple[bool, str]:
    """Validate project context and enforce a specific workflow mode."""
    project_info, error_msg = resolve_project_context(
        project,
        required_mode=required_mode,
    )
    if error_msg:
        return False, error_msg

    if project_info is None:
        return False, "❌ Project context could not be resolved."

    return True, ""


def _format_workflow_mode_error(current_mode: str, required_mode: str) -> str:
    """Build a stable workflow mismatch message."""
    current_mode_name = WORKFLOW_MODES.get(current_mode, {}).get("name", current_mode)
    required_mode_name = WORKFLOW_MODES.get(required_mode, {}).get("name", required_mode)
    return (
        "❌ This tool is only available for "
        f"{required_mode_name} projects.\n\n"
        f"Current workflow: {current_mode_name}.\n"
        "Switch project or update the current project workflow before retrying.\n\n"
        "Suggested fix:\n"
        f"- `project_action(action=\"update\", workflow_mode=\"{required_mode}\")`\n"
        "- or switch to a project that already uses the required workflow mode."
    )


def resolve_project_context(
    project: Optional[str] = None,
    *,
    required_mode: Optional[str] = None,
    project_manager: Any | None = None,
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Resolve project metadata through a single shared guard entrypoint."""
    if project_manager is None:
        is_valid, msg, project_info = ensure_project_context(project)
        if not is_valid or project_info is None:
            return None, f"❌ {msg}\n\n{get_project_list_for_prompt()}"
    else:
        pm = project_manager
        target_slug = project or pm.get_current_project()
        if not target_slug:
            available = pm.list_projects().get("projects", [])
            available_slugs = ", ".join(p.get("slug", "") for p in available if p.get("slug"))
            if available_slugs:
                return None, f"❌ No active project. Please specify one of: {available_slugs}"
            return None, "❌ No projects exist. Create one first with create_project()."

        if project and pm.get_current_project() != project:
            switch_result = pm.switch_project(project)
            if not switch_result.get("success"):
                return None, f"❌ {switch_result.get('error', 'Unable to switch project.')}"

        project_info = pm.get_project_info(target_slug)
        if not isinstance(project_info, dict):
            return None, "❌ Project not found."
        if "success" in project_info and not project_info.get("success"):
            return None, f"❌ {project_info.get('error', 'Project not found.')}"

    if required_mode is not None:
        current_mode = project_info.get("workflow_mode", DEFAULT_WORKFLOW_MODE)
        if current_mode != required_mode:
            return None, _format_workflow_mode_error(current_mode, required_mode)

    return project_info, None
