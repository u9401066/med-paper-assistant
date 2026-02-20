"""
Project Exploration Tools

Start exploration workspace, convert to project, get exploration status.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager


def register_exploration_tools(mcp: FastMCP, project_manager: ProjectManager):
    """Register exploration workspace tools."""

    @mcp.tool()
    def start_exploration() -> str:
        """
        Start literature exploration workspace without formal project.
        Save papers freely, convert to project later with convert_exploration_to_project.
        """
        result = project_manager.get_or_create_temp_project()

        if result.get("success"):
            stats = result.get("stats", {})
            paths = result.get("paths", {})

            return f"""🔍 **Literature Exploration Workspace**

{result.get("message", "Ready to explore!")}

## Current Contents
- 📚 Saved References: {stats.get("references", 0)}
- 📝 Draft Notes: {stats.get("drafts", 0)}
- 📊 Data Files: {stats.get("data_files", 0)}

## How to Use

1. **Search Literature**
   ```
   search_literature(query="your topic of interest")
   ```

2. **Save Interesting Papers**
   ```
   save_reference(pmid="12345678")
   ```

3. **When Ready to Start Writing**
   ```
   convert_exploration_to_project(
       name="Your Research Title",
       paper_type="original-research"
   )
   ```

**Paths:**
- References: `{paths.get("references", "")}`
- Notes: `{paths.get("drafts", "")}`
"""
        else:
            return f"❌ Error: {result.get('error', 'Unknown error')}"

    @mcp.tool()
    def convert_exploration_to_project(
        name: str,
        description: str = "",
        paper_type: str = "",
        target_journal: str = "",
        keep_exploration: bool = False,
    ) -> str:
        """
        Convert exploration workspace to formal project. Transfers all saved content.

        Args:
            name: English project name (translate if needed)
            description: Brief description
            paper_type: original-research|meta-analysis|systematic-review|...
            target_journal: Target journal
            keep_exploration: True=copy, False=move
        """
        result = project_manager.convert_temp_to_project(
            name=name,
            description=description,
            paper_type=paper_type,
            target_journal=target_journal,
            keep_temp=keep_exploration,
        )

        if result.get("success"):
            stats = result.get("stats", {})

            return f"""{result.get("message", "Conversion complete!")}

## New Project Structure
```
{result.get("slug", "project")}/
├── project.json    ← Project settings
├── concept.md      ← Research concept template
├── .memory/        ← AI memory files
├── drafts/         ← {stats.get("drafts", 0)} file(s) transferred
├── references/     ← {stats.get("references", 0)} reference(s) transferred
├── data/           ← {stats.get("data_files", 0)} file(s) transferred
└── results/        ← Export directory
```

**Next Steps:**
1. Edit `concept.md` to define your research
2. Use `setup_project_interactive` to configure preferences
3. Start writing with `/mdpaper.draft`
"""
        else:
            return f"""❌ Conversion Failed

{result.get("error", "Unknown error")}

**Troubleshooting:**
- Make sure you have an exploration workspace (use `start_exploration` first)
- Choose a unique project name in English
- Check that the paper_type is valid
"""
