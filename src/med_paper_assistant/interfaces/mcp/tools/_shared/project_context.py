"""
Project Context Validation Module

Provides utilities to validate project context before MCP tool execution.
This ensures Agent always operates on the correct project.
"""

from typing import Optional, Tuple, Dict, Any
from functools import wraps

from med_paper_assistant.infrastructure.persistence import get_project_manager


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
    return pm.get_current_project()


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
        if not is_valid:
            return False, msg, None
        
        # Switch to the project if not already active
        current = pm.get_current_project()
        if current.get("slug") != project_slug:
            switch_result = pm.switch_project(project_slug)
            if not switch_result.get("success"):
                return False, f"Failed to switch to project: {switch_result.get('error')}", None
        
        # Return updated project info
        return True, f"Working on project: {project_info.get('name')}", pm.get_current_project()
    
    else:
        # No project specified - check if we have an active project
        current = pm.get_current_project()
        if current.get("slug"):
            return True, f"Current project: {current.get('name')}", current
        else:
            # Check if any projects exist
            projects = pm.list_projects().get("projects", [])
            if projects:
                slugs = [p.get("slug") for p in projects]
                return False, f"No active project. Please specify one of: {', '.join(slugs)}", None
            else:
                return False, "No projects exist. Create one first with create_project().", None


def format_project_context_error(message: str, available_projects: list = None) -> str:
    """Format a helpful error message for project context issues."""
    lines = [f"⚠️ **Project Context Required**\n", message]
    
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
            "published": "📗"
        }.get(p.get("status", ""), "❓")
        lines.append(f"{marker}`{p.get('slug')}` - {p.get('name')} {status_emoji}")
    
    return "\n".join(lines)
