"""
Workspace management tools for VS Code integration.

These tools help manage VS Code editor tabs when switching projects.
"""

import asyncio
import os
from typing import Any, Optional

from .._shared import get_optional_tool_decorator
from .vscode_launcher import open_files_in_vscode, render_launch_report


def register_workspace_tools(
    mcp: Any,
    project_manager: Any,
    *,
    register_public_verbs: bool = True,
) -> dict[str, Any]:
    """Register workspace management tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    @tool()
    async def open_project_files(project_slug: Optional[str] = None) -> str:
        """
        Open project's core files (concept.md, draft.md) in VS Code.

        Args:
            project_slug: Project slug (default: current project)
        """
        try:
            resolved_slug = project_slug or project_manager.get_current_project()
            if not resolved_slug:
                return "❌ No project found. Please specify a project slug or set current project."

            project = project_manager.get_project_info(resolved_slug)
            if not project.get("success"):
                return f"❌ {project.get('error', f'Project {resolved_slug!r} not found.')}"

            project_path = project.get("project_path", "")
            if not project_path:
                project_path = os.path.join(project_manager.projects_dir, resolved_slug)

            # 要開啟的文件
            files_to_open = [
                os.path.join(project_path, "concept.md"),
                os.path.join(project_path, "drafts", "draft.md"),
            ]

            existing = [p for p in files_to_open if os.path.exists(p)]
            not_found = [p for p in files_to_open if not os.path.exists(p)]

            launch = await asyncio.to_thread(open_files_in_vscode, existing) if existing else None
            return render_launch_report(
                project.get("name", resolved_slug), existing, not_found, launch
            )

        except Exception as e:
            return f"❌ Error: {str(e)}"

    return {"open_project_files": open_project_files}
