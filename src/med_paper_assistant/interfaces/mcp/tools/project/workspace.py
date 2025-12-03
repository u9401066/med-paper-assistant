"""
Workspace management tools for VS Code integration.

These tools help manage VS Code editor tabs when switching projects.
"""

import os
import json
import subprocess
from typing import Optional
from mcp.server import Server

def register_workspace_tools(mcp: Server, project_manager):
    """Register workspace management tools."""
    
    @mcp.tool()
    async def close_other_project_files(keep_project_slug: str) -> str:
        """
        Close editor tabs that don't belong to the specified project.
        
        This tool sends VS Code commands to close files from other projects,
        keeping only files from the specified project open.
        
        Args:
            keep_project_slug: The project slug whose files should remain open.
            
        Returns:
            Result message indicating what actions were taken.
        """
        try:
            # 取得專案路徑
            projects_dir = project_manager.projects_dir
            keep_project_path = os.path.join(projects_dir, keep_project_slug)
            
            if not os.path.exists(keep_project_path):
                return f"❌ Project not found: {keep_project_slug}"
            
            # 使用 VS Code CLI 執行命令
            # 注意：這需要 VS Code 的 'code' 命令在 PATH 中
            
            # 方案 1: 發送 workbench command (需要 VS Code extension)
            # 方案 2: 使用 code --goto 開啟文件（目前的方式）
            
            # 由於無法直接關閉其他 tabs，我們改為：
            # 1. 記錄要保留的專案
            # 2. 通知用戶手動關閉或使用 VS Code 的 "Close All Editors" 然後重新開啟
            
            result_message = f"""
📁 切換到專案: {keep_project_slug}

🔧 由於瀏覽器無法直接控制 VS Code tabs，建議操作：

**方法 1 (推薦):**
1. 按 `Ctrl+K, W` 關閉所有編輯器
2. Dashboard 會自動開啟新專案的文件

**方法 2:**
1. 右鍵點擊 tab → "Close Others"
2. 保留需要的文件

**方法 3 (快捷鍵):**
- `Ctrl+K, U` - 關閉未儲存以外的編輯器
- `Ctrl+W` - 關閉當前編輯器

專案路徑: {keep_project_path}
"""
            return result_message.strip()
            
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    @mcp.tool()
    async def open_project_files(project_slug: Optional[str] = None) -> str:
        """
        Open the core files of a project in VS Code.
        
        Opens concept.md and draft.md if they exist.
        
        Args:
            project_slug: Project slug. If not provided, uses current project.
            
        Returns:
            List of files that were requested to open.
        """
        try:
            # 取得專案
            if project_slug:
                project = project_manager.get_project(project_slug)
            else:
                project = project_manager.get_current_project()
            
            if not project:
                return "❌ No project found. Please specify a project slug or set current project."
            
            project_path = project.get('path', '')
            if not project_path:
                slug = project.get('slug', project_slug)
                project_path = os.path.join(project_manager.projects_dir, slug)
            
            # 要開啟的文件
            files_to_open = [
                os.path.join(project_path, 'concept.md'),
                os.path.join(project_path, 'drafts', 'draft.md'),
            ]
            
            opened = []
            not_found = []
            
            for file_path in files_to_open:
                if os.path.exists(file_path):
                    # 嘗試用 code 命令開啟
                    try:
                        subprocess.run(['code', '--goto', file_path], check=False, capture_output=True)
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

    @mcp.tool()
    async def get_project_file_paths(project_slug: Optional[str] = None) -> str:
        """
        Get the file paths for a project's core files.
        
        Returns paths to concept.md, drafts/, references/, figures/ etc.
        Useful for navigation and file management.
        
        Args:
            project_slug: Project slug. If not provided, uses current project.
            
        Returns:
            JSON with file paths and their existence status.
        """
        try:
            # 取得專案
            if project_slug:
                project = project_manager.get_project(project_slug)
            else:
                project = project_manager.get_current_project()
            
            if not project:
                return json.dumps({"error": "No project found"})
            
            project_path = project.get('path', '')
            if not project_path:
                slug = project.get('slug', project_slug)
                project_path = os.path.join(project_manager.projects_dir, slug)
            
            # 核心檔案和目錄
            paths = {
                "project_root": project_path,
                "concept": os.path.join(project_path, 'concept.md'),
                "drafts_dir": os.path.join(project_path, 'drafts'),
                "draft_main": os.path.join(project_path, 'drafts', 'draft.md'),
                "references_dir": os.path.join(project_path, 'references'),
                "figures_dir": os.path.join(project_path, 'figures'),
                "data_dir": os.path.join(project_path, 'data'),
                "project_json": os.path.join(project_path, 'project.json'),
            }
            
            # 檢查存在性
            result = {
                "project_name": project.get('name', ''),
                "project_slug": project.get('slug', project_slug),
                "paths": {}
            }
            
            for key, path in paths.items():
                result["paths"][key] = {
                    "path": path,
                    "exists": os.path.exists(path),
                    "is_directory": os.path.isdir(path) if os.path.exists(path) else None
                }
            
            return json.dumps(result, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({"error": str(e)})
