"""
Project Tools Module

MCP tools for managing multiple research paper projects.
Each project has isolated drafts, references, data, and results.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.elicitation import AcceptedElicitation, DeclinedElicitation, CancelledElicitation

from med_paper_assistant.core.project_manager import ProjectManager


# ============================================
# Pydantic Models for Elicitation
# ============================================

class PaperTypeSelection(BaseModel):
    """Schema for paper type selection during interactive setup."""
    paper_type: Literal[
        'original-research', 
        'systematic-review', 
        'meta-analysis', 
        'case-report', 
        'review-article', 
        'letter', 
        'other'
    ] = Field(description="Type of research paper you are writing")


class InteractionPreferences(BaseModel):
    """Schema for interaction preferences during interactive setup."""
    interaction_style: str = Field(
        default="",
        description="How should I interact? (e.g., 'Be concise', 'Explain reasoning', '中文回答')"
    )
    language_preference: str = Field(
        default="",
        description="Language preferences (e.g., 'British English', 'Technical vocabulary')"
    )
    writing_style: str = Field(
        default="",
        description="Writing style notes (e.g., 'Formal academic', 'Active voice')"
    )


class ProjectMemo(BaseModel):
    """Schema for project memo during interactive setup."""
    memo: str = Field(
        default="",
        description="Notes, reminders, deadlines, or context for this project"
    )


def register_project_tools(mcp: FastMCP, project_manager: ProjectManager):
    """Register all project management tools with the MCP server."""
    
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
        
        Args:
            name: Human-readable project name (e.g., "Nasotracheal Intubation Comparison").
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
            type_info = project_manager.PAPER_TYPES.get(paper_type, {})
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
    def get_paper_types() -> str:
        """
        Get available paper types and their characteristics.
        
        Use this to understand what paper types are available when creating a project.
        
        Returns:
            List of paper types with descriptions and typical structure.
        """
        types = project_manager.get_paper_types()
        
        lines = ["**Which type of paper are you writing?**\n"]
        
        for key, info in types.items():
            lines.append(f"- **{info['name']}** (`{key}`) - {info['description']}")
        
        lines.append("")
        lines.append("Please tell me the type (e.g., 'original-research' or 'meta-analysis').")
        
        return "\n".join(lines)

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

    @mcp.tool()
    def update_project_settings(
        paper_type: str = "",
        target_journal: str = "",
        interaction_style: str = "",
        language_preference: str = "",
        writing_style: str = "",
        memo: str = ""
    ) -> str:
        """
        Update settings for the current project.
        
        Use this to configure paper type, preferences, and notes.
        These settings affect concept templates, writing style, and AI interaction.
        
        Args:
            paper_type: Type of paper (use get_paper_types to see options).
            target_journal: Target journal for submission.
            interaction_style: How you want the AI to interact (e.g., 
                              "Ask before making major changes", 
                              "Be concise", "Explain reasoning").
            language_preference: Language notes (e.g., "Use British English",
                                "Technical but accessible").
            writing_style: Writing style notes (e.g., "Formal academic",
                          "Active voice preferred").
            memo: Additional notes and reminders for this project.
            
        Returns:
            Confirmation of updated settings.
        """
        # Build interaction preferences dict
        interaction_preferences = {}
        if interaction_style:
            interaction_preferences["interaction_style"] = interaction_style
        if language_preference:
            interaction_preferences["language"] = language_preference
        if writing_style:
            interaction_preferences["writing_style"] = writing_style
        
        result = project_manager.update_project_settings(
            paper_type=paper_type if paper_type else None,
            target_journal=target_journal if target_journal else None,
            interaction_preferences=interaction_preferences if interaction_preferences else None,
            memo=memo if memo else None
        )
        
        if result.get("success"):
            updated = result.get("updated_fields", [])
            
            # Get current project info for display
            info = project_manager.get_project_info()
            prefs = info.get("interaction_preferences", {})
            
            output = f"""✅ Project Settings Updated!

**Updated Fields:** {', '.join(updated)}

## Current Settings

| Setting | Value |
|---------|-------|
| Paper Type | {info.get('paper_type', 'Not set')} |
| Target Journal | {info.get('target_journal', 'Not set')} |

## Interaction Preferences
- **Style:** {prefs.get('interaction_style', 'Not set')}
- **Language:** {prefs.get('language', 'Not set')}
- **Writing:** {prefs.get('writing_style', 'Not set')}

## Memo
{info.get('memo', '[No memo]')}

---
These settings are saved in `project.json` and `.memory/activeContext.md`
"""
            return output
        else:
            return f"❌ Error: {result.get('error', 'Unknown error')}"

    # ============================================
    # Interactive Setup Tool with Elicitation
    # ============================================
    
    @mcp.tool()
    async def setup_project_interactive(ctx: Context) -> str:
        """
        Interactively configure the current project step-by-step.
        
        Uses elicitation to ask user for:
        1. Paper type (required)
        2. Interaction preferences (optional)
        3. Project memo/notes (optional)
        
        This provides a guided setup experience.
        
        Returns:
            Configuration summary after setup.
        """
        current = project_manager.get_current_project()
        
        if not current:
            return """❌ No project selected!

Please first select or create a project:
- `list_projects()` - see available projects
- `switch_project(slug)` - select a project
- `create_project(name="...")` - create new project
"""
        
        info = project_manager.get_project_info(current)
        project_name = info.get('name', current)
        
        # Step 1: Paper Type (Required)
        paper_type_result = await ctx.elicit(
            message=f"Setting up project: **{project_name}**\n\nWhat type of paper are you writing?",
            schema=PaperTypeSelection
        )
        
        if isinstance(paper_type_result, CancelledElicitation):
            return "Setup cancelled."
        
        if isinstance(paper_type_result, DeclinedElicitation):
            return "Setup declined. You can run this tool again when ready."
        
        # Save paper type immediately
        paper_type = paper_type_result.data.paper_type
        project_manager.update_project_settings(paper_type=paper_type)
        
        # Step 2: Interaction Preferences (Optional)
        prefs_result = await ctx.elicit(
            message="How would you like me to interact with you?\n\n(Leave blank to skip)",
            schema=InteractionPreferences
        )
        
        if isinstance(prefs_result, AcceptedElicitation):
            prefs = prefs_result.data
            interaction_preferences = {}
            if prefs.interaction_style:
                interaction_preferences["interaction_style"] = prefs.interaction_style
            if prefs.language_preference:
                interaction_preferences["language"] = prefs.language_preference
            if prefs.writing_style:
                interaction_preferences["writing_style"] = prefs.writing_style
            
            if interaction_preferences:
                project_manager.update_project_settings(
                    interaction_preferences=interaction_preferences
                )
        
        # Step 3: Project Memo (Optional)
        memo_result = await ctx.elicit(
            message="Any notes, reminders, or context for this project?\n\n(e.g., deadlines, co-authors, IRB info)",
            schema=ProjectMemo
        )
        
        if isinstance(memo_result, AcceptedElicitation) and memo_result.data.memo:
            project_manager.update_project_settings(memo=memo_result.data.memo)
        
        # Get final settings
        final_info = project_manager.get_project_info(current)
        final_prefs = final_info.get("interaction_preferences", {})
        
        paper_type_info = project_manager.PAPER_TYPES.get(paper_type, {})
        
        return f"""✅ Project Setup Complete!

## {project_name}

| Setting | Value |
|---------|-------|
| **Paper Type** | {paper_type_info.get('name', paper_type)} |
| **Typical Sections** | {paper_type_info.get('sections', 'N/A')} |
| **Target Journal** | {final_info.get('target_journal', 'Not set')} |

### Interaction Preferences
- **Style:** {final_prefs.get('interaction_style', 'Default')}
- **Language:** {final_prefs.get('language', 'Default')}
- **Writing:** {final_prefs.get('writing_style', 'Default')}

### Memo
{final_info.get('memo', '[No memo]')}

---
**Next Steps:**
1. Edit `concept.md` to define your research concept
2. Use `search_literature` to find relevant papers
3. Use `write_draft` to start writing sections
"""
