"""
Project CRUD Tools

Create, List, Switch, Get Current project operations.
"""

from mcp.server.fastmcp import FastMCP
from med_paper_assistant.infrastructure.persistence import ProjectManager
from med_paper_assistant.domain.paper_types import get_paper_type_dict


def register_crud_tools(mcp: FastMCP, project_manager: ProjectManager):
    """Register project CRUD tools."""

    @mcp.tool()
    def create_project(
        name: str, 
        description: str = "",
        target_journal: str = "",
        paper_type: str = "",
        memo: str = ""
    ) -> str:
        """
        Create a new research paper project with isolated workspace.
        
        Each project gets its own:
        - concept.md (research concept with type-specific template)
        - .memory/ (project-specific AI memory)
        - drafts/ (paper drafts)
        - references/ (saved literature by PMID)
        - data/ (analysis data files)
        - results/ (exported Word documents)
        
        IMPORTANT: The 'name' parameter MUST be in English for proper slug generation.
        If user provides a non-English name (e.g., Chinese, Japanese, Korean),
        YOU (the Agent) must translate it to English before calling this tool.
        
        Examples:
        - "死亡率預測" → "Mortality Prediction"
        - "鼻腔氣管插管比較" → "Nasotracheal Intubation Comparison"
        
        Args:
            name: Project name in ENGLISH (e.g., "Mortality Prediction Study").
                  Agent must translate non-English names before calling.
            description: Brief description of the research.
            target_journal: Target journal for submission (optional).
            paper_type: Type of paper. One of:
                       - "original-research": Clinical trial, cohort, cross-sectional
                       - "systematic-review": Systematic literature review
                       - "meta-analysis": Systematic review with quantitative synthesis
                       - "case-report": Single case or case series
                       - "review-article": Narrative/invited review
                       - "letter": Brief communication
                       - "other": Editorial, perspective, etc.
            memo: Initial notes/reminders for the project.
            
        Returns:
            Project creation result with paths.
        """
        result = project_manager.create_project(
            name=name,
            description=description,
            target_journal=target_journal,
            paper_type=paper_type,
            memo=memo
        )
        
        if result.get("success"):
            type_info = get_paper_type_dict(paper_type) if paper_type else {}
            type_name = type_info.get("name", "Not specified")
            
            return f"""✅ Project Created Successfully!

📁 **Project:** {name}
🔖 **Slug:** {result['slug']}
📝 **Paper Type:** {type_name}
📂 **Location:** {result['path']}

**Structure:**
```
{result['slug']}/
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
