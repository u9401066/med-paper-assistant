"""
Workspace management tools for VS Code integration.

These tools help manage VS Code editor tabs when switching projects.
"""

import os
import subprocess  # nosec B404 - intentional VS Code integration
from typing import Any, Optional


def register_workspace_tools(mcp: Any, project_manager: Any) -> None:
    """Register workspace management tools."""

    @mcp.tool()
    async def open_project_files(project_slug: Optional[str] = None) -> str:
        """
        Open project's core files (concept.md, draft.md) in VS Code.

        Args:
            project_slug: Project slug (default: current project)
        """
        try:
            # 取得專案
            if project_slug:
                project = project_manager.get_project(project_slug)
            else:
                project = project_manager.get_current_project()

            if not project:
                return "❌ No project found. Please specify a project slug or set current project."

            project_path = project.get("path", "")
            if not project_path:
                slug = project.get("slug", project_slug)
                project_path = os.path.join(project_manager.projects_dir, slug)

            # 要開啟的文件
            files_to_open = [
                os.path.join(project_path, "concept.md"),
                os.path.join(project_path, "drafts", "draft.md"),
            ]

            opened = []
            not_found = []

            for file_path in files_to_open:
                if os.path.exists(file_path):
                    # 嘗試用 code 命令開啟
                    try:
                        subprocess.run(  # nosec B603 B607 - trusted VS Code CLI
                            ["code", "--goto", file_path], check=False, capture_output=True
                        )
                        opened.append(file_path)
                    except FileNotFoundError:
                        # code 命令不在 PATH 中
                        opened.append(f"{file_path} (use vscode:// URI)")
                else:
                    not_found.append(file_path)

            result = f"📂 專案: {project.get('name', project_slug)}\n\n"

            if opened:
                result += "✅ 開啟的文件:\n"
                for f in opened:
                    result += f"  - {os.path.basename(f)}\n"

            if not_found:
                result += "\n⚠️ 未找到的文件:\n"
                for f in not_found:
                    result += f"  - {os.path.basename(f)}\n"

            return result.strip()

        except Exception as e:
            return f"❌ Error: {str(e)}"
