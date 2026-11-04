"""Handlers that list, switch and inspect projects."""

import os

from med_paper_assistant.shared.constants import DEFAULT_WORKFLOW_MODE, WORKFLOW_MODES

from ..._shared import log_agent_misuse, log_tool_call, log_tool_result
from .._deps import PROJECT_MANAGER
from ._formatting import contents_block, detail_paths, paths_block, stats_table


def list_projects() -> str:
    """DEPRECATED public verb. Prefer `project_action(action="list")`.

    List all research paper projects with status.
    """
    project_manager = PROJECT_MANAGER.get()
    log_tool_call("list_projects", {})

    result = project_manager.list_projects()
    projects = result.get("projects", [])
    current = result.get("current")

    if not projects:
        log_tool_result("list_projects", "no projects found", success=True)
        return """📭 No projects found.

Use `create_project` to start a new project:
```
create_project(name="My Library", description="Brief description", workflow_mode="library-wiki")
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
        workflow_mode = p.get("workflow_mode", DEFAULT_WORKFLOW_MODE)
        workflow_name = WORKFLOW_MODES.get(workflow_mode, {}).get("name", workflow_mode)

        lines.append(
            f"{marker}**{p['name']}** ({p['slug']}) [{workflow_name}] {status_emoji} {p.get('status', '')}"
        )

    lines.append(f"\n**Total:** {len(projects)} project(s)")
    if current:
        lines.append(f"**Current:** {current}")

    log_tool_result("list_projects", f"found {len(projects)} projects", success=True)
    return "\n".join(lines)


def switch_project(slug: str) -> str:
    """
    Switch to a different project. All subsequent operations use this project.

    Args:
        slug: Project identifier (from list_projects)
    """
    project_manager = PROJECT_MANAGER.get()
    log_tool_call("switch_project", {"slug": slug})

    result = project_manager.switch_project(slug)

    if result.get("success"):
        stats = result.get("stats", {})
        workflow_mode = result.get("workflow_mode", DEFAULT_WORKFLOW_MODE)
        workflow_name = WORKFLOW_MODES.get(workflow_mode, {}).get("name", workflow_mode)
        log_tool_result("switch_project", f"switched to {slug}", success=True)
        return f"""✅ Switched to: **{result.get("name", slug)}**

**Workflow:** {workflow_name}
**Status:** {result.get("status", "unknown")}
**Description:** {result.get("description", "No description")}

**Contents:**
{contents_block(stats, workflow_mode)}

**Paths:**
{paths_block(result["paths"], workflow_mode)}
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


def get_current_project(include_files: bool = False) -> str:
    """
    DEPRECATED public verb. Prefer `project_action(action="current")`.

    Get current project info including paths, statistics, and exploration status.

    Args:
        include_files: Include detailed file listing with existence checks (default: False)
    """
    project_manager = PROJECT_MANAGER.get()
    log_tool_call("get_current_project", {"include_files": include_files})

    result = project_manager.get_project_info()

    if result.get("success"):
        stats = result.get("stats", {})
        paths = result.get("paths", {})
        workflow_mode = result.get("workflow_mode", DEFAULT_WORKFLOW_MODE)
        workflow_name = WORKFLOW_MODES.get(workflow_mode, {}).get("name", workflow_mode)

        output = f"""# 📁 Current Project: {result.get("name", "Unknown")}

**Slug:** {result.get("slug")}
**Workflow:** {workflow_name}
**Paper Type:** {result.get("paper_type", "Not set") or "Optional later"}
**Status:** {result.get("status", "unknown")}
**Created:** {result.get("created_at", "Unknown")[:10]}
**Description:** {result.get("description", "No description")}

## Statistics
| Content | Count |
|---------|-------|
{stats_table(stats, workflow_mode)}

## Paths
{paths_block(paths, workflow_mode)}

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
            file_paths = detail_paths(paths, workflow_mode)
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

**Workflow:** Library Wiki Path
**Created:** {temp_result.get("created_at", "Unknown")[:10]}

## Contents
- 📚 **References:** {ref_count}
- 📥 **Inbox Notes:** {temp_stats.get("inbox", 0)}
- 🧠 **Concept Notes:** {temp_stats.get("concepts", 0)}
- 🗂️ **Synthesis Projects:** {temp_stats.get("projects", 0)}

"""
                if ref_count >= 5:
                    output += "## ✅ Ready to Convert!\n"
                    output += "Library Wiki Path:\n"
                    output += '```\nconvert_exploration_to_project(name="Your Library", workflow_mode="library-wiki")\n```\n'
                    output += "Manuscript Path:\n"
                    output += '```\nconvert_exploration_to_project(name="Your Research Title", workflow_mode="manuscript", paper_type="original-research")\n```\n'
                elif ref_count > 0:
                    output += f"## 💡 {ref_count} references saved. Keep exploring or convert when ready.\n"
                else:
                    output += '## 💡 Start by searching literature:\n```\nunified_search(query="your topic")\n```\n'

                log_tool_result("get_current_project", "exploration workspace", success=True)
                return output

        log_tool_result(
            "get_current_project", result.get("error", "No project selected"), success=False
        )
        return f"""⚠️ {result.get("error", "No project selected")}

**Quick Start:**
1. `list_projects()` - See existing projects
2. `create_project(name="Your Library", workflow_mode="library-wiki")` - Create a library/wiki project
3. `switch_project(slug="project-name")` - Switch to existing
4. `start_exploration()` - Browse literature without a project
"""
