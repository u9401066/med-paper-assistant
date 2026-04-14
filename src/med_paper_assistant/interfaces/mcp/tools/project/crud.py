"""
Project CRUD Tools

Create, List, Switch, Get Current project operations.
"""

import json
import os

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.domain.paper_types import get_paper_type_dict
from med_paper_assistant.infrastructure.persistence import ProjectManager

from .._shared import (
    get_optional_tool_decorator,
    log_agent_misuse,
    log_tool_call,
    log_tool_error,
    log_tool_result,
)


def register_crud_tools(
    mcp: FastMCP,
    project_manager: ProjectManager,
    *,
    register_public_verbs: bool = True,
):
    """Register project CRUD tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    @tool()
    def create_project(
        name: str,
        description: str = "",
        target_journal: str = "",
        paper_type: str = "",
        authors_json: str = "",
        memo: str = "",
    ) -> str:
        """
        Create new research project. Name MUST be English (translate if needed).

        Args:
            name: English project name (e.g., "Mortality Prediction Study")
            description: Brief research description
            target_journal: Target journal (optional)
            paper_type: original-research|systematic-review|meta-analysis|case-report|review-article|letter|other
            authors_json: JSON array of authors. Each entry can be a name string or structured object:
                [{"name": "Jane Doe", "affiliations": ["Dept X, Uni Y"], "orcid": "0000-...", "email": "jane@example.com", "is_corresponding": true}]
            memo: Initial notes
        """
        log_tool_call(
            "create_project", {"name": name, "description": description, "paper_type": paper_type}
        )

        # Parse authors
        authors: list[object] = []
        if authors_json:
            try:
                authors_payload = json.loads(authors_json)
            except json.JSONDecodeError as e:
                return f"❌ Error parsing authors_json: {e}"
            if not isinstance(authors_payload, list):
                return "❌ Error: authors_json must be a JSON array."
            authors = authors_payload

        try:
            result = project_manager.create_project(
                name=name,
                description=description,
                authors=authors,
                target_journal=target_journal,
                paper_type=paper_type,
                memo=memo,
            )

            if result.get("success"):
                type_info = get_paper_type_dict(paper_type) if paper_type else {}
                type_name = type_info.get("name", "Not specified")

                log_tool_result(
                    "create_project", f"created project slug={result['slug']}", success=True
                )
                return f"""✅ Project Created Successfully!

📁 **Project:** {name}
🔖 **Slug:** {result["slug"]}
📝 **Paper Type:** {type_name}
📂 **Location:** {result["path"]}

**Structure:**
```
{result["slug"]}/
├── project.json    ← Settings & metadata
├── concept.md      ← Research concept (type-specific template)
├── .memory/        ← Project AI memory
│   ├── activeContext.md
│   └── progress.md
├── drafts/         ← Paper sections
├── references/     ← Literature (by PMID)
├── data/           ← Analysis data
└── results/        ← Exported documents
```

**Next Steps:**
1. Use `/mdpaper.project` to configure paper type and preferences (if not set)
2. Edit `concept.md` to define your research
3. Use `/mdpaper.concept` to develop with literature support
"""
            else:
                log_tool_result(
                    "create_project", result.get("error", "Unknown error"), success=False
                )
                return f"❌ Error: {result.get('error', 'Unknown error')}"
        except Exception as e:
            log_tool_error("create_project", e, {"name": name, "paper_type": paper_type})
            return f"❌ Error creating project: {str(e)}"

    @tool()
    def list_projects() -> str:
        """DEPRECATED public verb. Prefer `project_action(action="list")`.

        List all research paper projects with status.
        """
        log_tool_call("list_projects", {})

        result = project_manager.list_projects()
        projects = result.get("projects", [])
        current = result.get("current")

        if not projects:
            log_tool_result("list_projects", "no projects found", success=True)
            return """📭 No projects found.

Use `create_project` to start a new research paper project:
```
create_project(name="My Research Topic", description="Brief description")
```
"""

        lines = ["# 📚 Research Paper Projects\n"]

        for p in projects:
            marker = "→ " if p.get("is_current") else "  "
            status_emoji = {
                "concept": "💡",
                "drafting": "✍️",
                "review": "🔍",
                "submitted": "📤",
                "published": "📗",
            }.get(p.get("status", ""), "❓")

            lines.append(
                f"{marker}**{p['name']}** ({p['slug']}) {status_emoji} {p.get('status', '')}"
            )

        lines.append(f"\n**Total:** {len(projects)} project(s)")
        if current:
            lines.append(f"**Current:** {current}")

        log_tool_result("list_projects", f"found {len(projects)} projects", success=True)
        return "\n".join(lines)

    @tool()
    def switch_project(slug: str) -> str:
        """
        Switch to a different project. All subsequent operations use this project.

        Args:
            slug: Project identifier (from list_projects)
        """
        log_tool_call("switch_project", {"slug": slug})

        result = project_manager.switch_project(slug)

        if result.get("success"):
            stats = result.get("stats", {})
            log_tool_result("switch_project", f"switched to {slug}", success=True)
            return f"""✅ Switched to: **{result.get("name", slug)}**

**Status:** {result.get("status", "unknown")}
**Description:** {result.get("description", "No description")}

**Contents:**
- 📝 Drafts: {stats.get("drafts", 0)} files
- 📚 References: {stats.get("references", 0)} saved
- 📊 Data files: {stats.get("data_files", 0)}

**Paths:**
- Concept: `{result["paths"]["concept"]}`
- Drafts: `{result["paths"]["drafts"]}`
- References: `{result["paths"]["references"]}`
"""
        else:
            available = result.get("available_projects", [])
            log_agent_misuse(
                "switch_project",
                "valid project slug required",
                {"slug": slug},
                f"available: {available}",
            )
            return f"""❌ Project '{slug}' not found.

**Available projects:** {", ".join(available) if available else "None"}

Use `list_projects` to see all projects, or `create_project` to create a new one.
"""

    @tool()
    def get_current_project(include_files: bool = False) -> str:
        """
        DEPRECATED public verb. Prefer `project_action(action="current")`.

        Get current project info including paths, statistics, and exploration status.

        Args:
            include_files: Include detailed file listing with existence checks (default: False)
        """
        log_tool_call("get_current_project", {"include_files": include_files})

        result = project_manager.get_project_info()

        if result.get("success"):
            stats = result.get("stats", {})
            paths = result.get("paths", {})

            output = f"""# 📁 Current Project: {result.get("name", "Unknown")}

**Slug:** {result.get("slug")}
**Status:** {result.get("status", "unknown")}
**Created:** {result.get("created_at", "Unknown")[:10]}
**Description:** {result.get("description", "No description")}

## Statistics
| Content | Count |
|---------|-------|
| Drafts | {stats.get("drafts", 0)} |
| References | {stats.get("references", 0)} |
| Data Files | {stats.get("data_files", 0)} |

## Paths
- **Concept:** `{paths.get("concept", "")}`
- **Drafts:** `{paths.get("drafts", "")}`
- **References:** `{paths.get("references", "")}`
- **Data:** `{paths.get("data", "")}`
- **Results:** `{paths.get("results", "")}`

## Target Journal
{result.get("target_journal", "Not specified")}
"""
            # Show authors if present
            authors_data = result.get("authors", [])
            if authors_data:
                output += "\n## Authors\n"
                for a in authors_data:
                    if isinstance(a, dict):
                        name = a.get("name", "")
                        affs = a.get("affiliations", [])
                        corr = " *(corresponding)*" if a.get("is_corresponding") else ""
                        output += f"- **{name}**{corr}"
                        if affs:
                            output += f" — {'; '.join(affs)}"
                        output += "\n"
                    else:
                        output += f"- {a}\n"
            else:
                output += "\n## Authors\nNot specified. Use `update_authors` to add.\n"

            if include_files:
                project_path = paths.get("root", "") or paths.get("concept", "").rsplit("/", 1)[0]
                file_paths = {
                    "project_root": project_path,
                    "concept": paths.get("concept", ""),
                    "drafts_dir": paths.get("drafts", ""),
                    "references_dir": paths.get("references", ""),
                    "data_dir": paths.get("data", ""),
                    "results_dir": paths.get("results", ""),
                }
                output += "\n## File Details\n\n"
                output += "| Path | Exists |\n"
                output += "|------|--------|\n"
                for key, path in file_paths.items():
                    exists = os.path.exists(path) if path else False
                    output += f"| `{key}`: {path} | {'✅' if exists else '❌'} |\n"

            log_tool_result("get_current_project", f"current: {result.get('slug')}", success=True)
            return output
        else:
            # Check for exploration workspace
            temp_path = project_manager.projects_dir / project_manager.TEMP_PROJECT_SLUG
            if temp_path.exists():
                temp_result = project_manager.get_project_info(project_manager.TEMP_PROJECT_SLUG)
                if temp_result.get("success"):
                    temp_stats = temp_result.get("stats", {})
                    ref_count = temp_stats.get("references", 0)

                    output = f"""# 🔍 Exploration Workspace Active

**Created:** {temp_result.get("created_at", "Unknown")[:10]}

## Contents
- 📚 **References:** {ref_count}
- 📝 **Draft Notes:** {temp_stats.get("drafts", 0)}
- 📊 **Data Files:** {temp_stats.get("data_files", 0)}

"""
                    if ref_count >= 5:
                        output += "## ✅ Ready to Convert!\n"
                        output += '```\nconvert_exploration_to_project(name="Your Research Title", paper_type="original-research")\n```\n'
                    elif ref_count > 0:
                        output += f"## 💡 {ref_count} references saved. Keep exploring or convert when ready.\n"
                    else:
                        output += '## 💡 Start by searching literature:\n```\nsearch_literature(query="your topic")\n```\n'

                    log_tool_result("get_current_project", "exploration workspace", success=True)
                    return output

            log_tool_result(
                "get_current_project", result.get("error", "No project selected"), success=False
            )
            return f"""⚠️ {result.get("error", "No project selected")}

**Quick Start:**
1. `list_projects()` - See existing projects
2. `create_project(name="Your Research")` - Create new project
3. `switch_project(slug="project-name")` - Switch to existing
4. `start_exploration()` - Browse literature without a project
"""

    @tool()
    def archive_project(slug: str, confirm: bool = False) -> str:
        """
        Archive project (soft delete). Data preserved, can restore manually.

        Args:
            slug: Project slug to archive
            confirm: False=preview, True=execute
        """
        import shutil
        from datetime import datetime

        log_tool_call("archive_project", {"slug": slug, "confirm": confirm})

        # Get project info
        result = project_manager.get_project_info(slug)
        if not result.get("success"):
            error_msg = f"❌ Project '{slug}' not found.\n\n"
            error_msg += "Use `list_projects()` to see available projects."
            log_agent_misuse("archive_project", "valid project slug", {"slug": slug}, error_msg)
            return error_msg

        name = result.get("name", slug)
        stats = result.get("stats", {})
        paths = result.get("paths", {})
        project_path = paths.get("root", "")

        if not confirm:
            # Preview mode
            output = "⚠️ **即將封存專案 (Preview)**\n\n"
            output += f"**專案名稱**: {name}\n"
            output += f"**Slug**: {slug}\n"
            output += f"**狀態**: {result.get('status', 'unknown')}\n\n"
            output += "**統計**:\n"
            output += f"  - 📝 草稿: {stats.get('drafts', 0)} files\n"
            output += f"  - 📚 文獻: {stats.get('references', 0)} saved\n"
            output += f"  - 📊 資料: {stats.get('data_files', 0)} files\n\n"
            output += "**封存後**:\n"
            output += f"  - 專案將被重命名為 `_archived_{{timestamp}}_{slug}`\n"
            output += "  - 所有資料都會保留\n"
            output += "  - 可以手動還原\n\n"
            output += f'請使用 `archive_project(slug="{slug}", confirm=True)` 確認封存。'
            log_tool_result("archive_project", "preview shown", success=True)
            return output

        # Actually archive
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archived_slug = f"_archived_{timestamp}_{slug}"
            archived_path = project_manager.projects_dir / archived_slug

            # Move the project directory
            shutil.move(project_path, archived_path)

            # Clear current if this was the current project
            if project_manager.get_current_project() == slug:
                if project_manager.state_file.exists():
                    project_manager.state_file.unlink()

            result_msg = "✅ **已封存專案**\n\n"
            result_msg += f"**原專案**: {name} (`{slug}`)\n"
            result_msg += f"**封存名稱**: `{archived_slug}`\n"
            result_msg += f"**封存位置**: `{archived_path}`\n\n"
            result_msg += "**已封存內容**:\n"
            result_msg += f"  - 📝 草稿: {stats.get('drafts', 0)} files\n"
            result_msg += f"  - 📚 文獻: {stats.get('references', 0)} saved\n"
            result_msg += f"  - 📊 資料: {stats.get('data_files', 0)} files\n\n"
            result_msg += "💡 如需還原，請手動將資料夾重新命名為原始 slug。"

            log_tool_result("archive_project", f"archived {slug}", success=True)
            return result_msg

        except Exception as e:
            error_msg = f"❌ 封存失敗: {str(e)}"
            log_tool_error("archive_project", e, {"slug": slug})
            return error_msg

    @tool()
    def delete_project(slug: str, confirm: bool = False) -> str:
        """
        ⚠️ PERMANENTLY delete project. Cannot undo! Use archive_project for soft delete.

        Args:
            slug: Project slug to delete
            confirm: False=preview, True=execute
        """
        log_tool_call("delete_project", {"slug": slug, "confirm": confirm})

        # Get project info
        result = project_manager.get_project_info(slug)
        if not result.get("success"):
            error_msg = f"❌ Project '{slug}' not found.\n\n"
            error_msg += "Use `list_projects()` to see available projects."
            log_agent_misuse("delete_project", "valid project slug", {"slug": slug}, error_msg)
            return error_msg

        name = result.get("name", slug)
        stats = result.get("stats", {})
        paths = result.get("paths", {})

        if not confirm:
            # Preview mode
            output = "⚠️ **即將永久刪除專案 (Preview)**\n\n"
            output += f"**專案名稱**: {name}\n"
            output += f"**Slug**: {slug}\n"
            output += f"**狀態**: {result.get('status', 'unknown')}\n\n"
            output += "**將被刪除的內容**:\n"
            output += f"  - 📝 草稿: {stats.get('drafts', 0)} files\n"
            output += f"  - 📚 文獻: {stats.get('references', 0)} saved\n"
            output += f"  - 📊 資料: {stats.get('data_files', 0)} files\n"
            output += f"  - 📁 整個專案目錄: `{paths.get('root', '')}`\n\n"
            output += "⛔ **此操作無法復原！所有資料將永久消失！**\n\n"
            output += "💡 建議改用 `archive_project` 進行軟刪除。\n\n"
            output += f'如確定要刪除，請使用 `delete_project(slug="{slug}", confirm=True)`'
            log_tool_result("delete_project", "preview shown", success=True)
            return output

        # Actually delete
        delete_result = project_manager.delete_project(slug, confirm=True)

        if delete_result.get("success"):
            result_msg = "🗑️ **已永久刪除專案**\n\n"
            result_msg += f"**專案名稱**: {name}\n"
            result_msg += f"**Slug**: {slug}\n\n"
            result_msg += "**已刪除的內容**:\n"
            result_msg += f"  - 📝 草稿: {stats.get('drafts', 0)} files\n"
            result_msg += f"  - 📚 文獻: {stats.get('references', 0)} saved\n"
            result_msg += f"  - 📊 資料: {stats.get('data_files', 0)} files\n"
            log_tool_result("delete_project", f"deleted {slug}", success=True)
            return result_msg
        else:
            error_msg = f"❌ {delete_result.get('error', '未知錯誤')}"
            log_tool_result("delete_project", error_msg, success=False)
            return error_msg

    return {
        "create_project": create_project,
        "list_projects": list_projects,
        "switch_project": switch_project,
        "get_current_project": get_current_project,
        "archive_project": archive_project,
        "delete_project": delete_project,
    }
