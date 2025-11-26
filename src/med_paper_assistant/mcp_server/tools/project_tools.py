"""
Project Tools Module

MCP tools for managing multiple research paper projects.
Each project has isolated drafts, references, data, and results.
"""

from typing import Optional, List
from mcp.server.fastmcp import FastMCP

from med_paper_assistant.core.project_manager import ProjectManager


def register_project_tools(mcp: FastMCP, project_manager: ProjectManager):
    """Register all project management tools with the MCP server."""
    
    @mcp.tool()
    def create_project(
        name: str, 
        description: str = "",
        target_journal: str = ""
    ) -> str:
        """
        Create a new research paper project with isolated workspace.
        
        Each project gets its own:
        - concept.md (research concept with protected sections)
        - drafts/ (paper drafts)
        - references/ (saved literature by PMID)
        - data/ (analysis data files)
        - results/ (exported Word documents)
        
        Args:
            name: Human-readable project name (e.g., "Nasotracheal Intubation Comparison").
            description: Brief description of the research.
            target_journal: Target journal for submission (optional).
            
        Returns:
            Project creation result with paths.
        """
        result = project_manager.create_project(
            name=name,
            description=description,
            target_journal=target_journal
        )
        
        if result.get("success"):
            return f"""✅ Project Created Successfully!

📁 **Project:** {name}
🔖 **Slug:** {result['slug']}
📂 **Location:** {result['path']}

**Structure:**
```
{result['slug']}/
├── concept.md      ← Start here! Define your research concept
├── drafts/         ← Paper sections
├── references/     ← Literature (by PMID)
├── data/           ← Analysis data
└── results/        ← Exported documents
```

**Next Steps:**
1. Edit `concept.md` to define your research
2. Use `/mdpaper.concept` to develop with literature support
3. Use `search_literature` to find relevant papers
"""
        else:
            return f"❌ Error: {result.get('error', 'Unknown error')}"

    @mcp.tool()
    def list_projects() -> str:
        """
        List all research paper projects.
        
        Shows project name, status, and which one is currently active.
        
        Returns:
            Formatted list of all projects.
        """
        result = project_manager.list_projects()
        projects = result.get("projects", [])
        current = result.get("current")
        
        if not projects:
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
                "published": "📗"
            }.get(p.get("status", ""), "❓")
            
            lines.append(f"{marker}**{p['name']}** ({p['slug']}) {status_emoji} {p.get('status', '')}")
        
        lines.append(f"\n**Total:** {len(projects)} project(s)")
        if current:
            lines.append(f"**Current:** {current}")
        
        return "\n".join(lines)

    @mcp.tool()
    def switch_project(slug: str) -> str:
        """
        Switch to a different research paper project.
        
        All subsequent operations (save_reference, write_draft, etc.) 
        will use this project's directories.
        
        Args:
            slug: Project identifier (use list_projects to see available).
            
        Returns:
            Project info after switching.
        """
        result = project_manager.switch_project(slug)
        
        if result.get("success"):
            stats = result.get("stats", {})
            return f"""✅ Switched to: **{result.get('name', slug)}**

**Status:** {result.get('status', 'unknown')}
**Description:** {result.get('description', 'No description')}

**Contents:**
- 📝 Drafts: {stats.get('drafts', 0)} files
- 📚 References: {stats.get('references', 0)} saved
- 📊 Data files: {stats.get('data_files', 0)}

**Paths:**
- Concept: `{result['paths']['concept']}`
- Drafts: `{result['paths']['drafts']}`
- References: `{result['paths']['references']}`
"""
        else:
            available = result.get("available_projects", [])
            return f"""❌ Project '{slug}' not found.

**Available projects:** {', '.join(available) if available else 'None'}

Use `list_projects` to see all projects, or `create_project` to create a new one.
"""

    @mcp.tool()
    def get_current_project() -> str:
        """
        Get information about the currently active project.
        
        Returns:
            Current project details including paths and statistics.
        """
        result = project_manager.get_project_info()
        
        if result.get("success"):
            stats = result.get("stats", {})
            paths = result.get("paths", {})
            
            return f"""# 📁 Current Project: {result.get('name', 'Unknown')}

**Slug:** {result.get('slug')}
**Status:** {result.get('status', 'unknown')}
**Created:** {result.get('created_at', 'Unknown')[:10]}
**Description:** {result.get('description', 'No description')}

## Statistics
| Content | Count |
|---------|-------|
| Drafts | {stats.get('drafts', 0)} |
| References | {stats.get('references', 0)} |
| Data Files | {stats.get('data_files', 0)} |

## Paths
- **Concept:** `{paths.get('concept', '')}`
- **Drafts:** `{paths.get('drafts', '')}`
- **References:** `{paths.get('references', '')}`
- **Data:** `{paths.get('data', '')}`
- **Results:** `{paths.get('results', '')}`

## Target Journal
{result.get('target_journal', 'Not specified')}
"""
        else:
            return f"""⚠️ {result.get('error', 'No project selected')}

**Quick Start:**
1. `list_projects()` - See existing projects
2. `create_project(name="Your Research")` - Create new project
3. `switch_project(slug="project-name")` - Switch to existing
"""

    @mcp.tool()
    def update_project_status(status: str) -> str:
        """
        Update the status of the current project.
        
        Args:
            status: New status. One of:
                    - "concept": Initial concept development
                    - "drafting": Writing paper sections
                    - "review": Internal review and revision
                    - "submitted": Submitted to journal
                    - "published": Published
                    
        Returns:
            Confirmation of status update.
        """
        result = project_manager.update_project_status(status)
        
        if result.get("success"):
            status_emoji = {
                "concept": "💡",
                "drafting": "✍️",
                "review": "🔍",
                "submitted": "📤",
                "published": "📗"
            }.get(status, "❓")
            
            return f"✅ Project status updated to: {status_emoji} **{status}**"
        else:
            return f"❌ Error: {result.get('error', 'Unknown error')}"

    @mcp.tool()
    def get_project_paths() -> str:
        """
        Get all file paths for the current project.
        
        Use this to know where to save drafts, references, data, and results.
        All other tools automatically use these paths.
        
        Returns:
            Dictionary of path names to absolute paths.
        """
        try:
            paths = project_manager.get_project_paths()
            current = project_manager.get_current_project()
            
            return f"""# 📂 Project Paths: {current}

| Purpose | Path |
|---------|------|
| Root | `{paths['root']}` |
| Concept | `{paths['concept']}` |
| Drafts | `{paths['drafts']}` |
| References | `{paths['references']}` |
| Data | `{paths['data']}` |
| Results | `{paths['results']}` |
| Config | `{paths['config']}` |

**Usage:**
- Save drafts to: `{paths['drafts']}/introduction.md`
- Save references to: `{paths['references']}/{{PMID}}/`
- Save data to: `{paths['data']}/dataset.csv`
- Export results to: `{paths['results']}/paper.docx`
"""
        except ValueError as e:
            return f"⚠️ {str(e)}\n\nUse `create_project` or `switch_project` first."
