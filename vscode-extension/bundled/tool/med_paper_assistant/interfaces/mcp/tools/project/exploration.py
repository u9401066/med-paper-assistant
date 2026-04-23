"""
Project Exploration Tools

Start exploration workspace, convert to project, get exploration status.
"""

from mcp.server.fastmcp import FastMCP

from med_paper_assistant.infrastructure.persistence import ProjectManager

from .._shared import get_optional_tool_decorator


def register_exploration_tools(
    mcp: FastMCP,
    project_manager: ProjectManager,
    *,
    register_public_verbs: bool = True,
):
    """Register exploration workspace tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    @tool()
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

**Workflow Mode:** Library Wiki Path

## Current Contents
- 📚 Saved References: {stats.get("references", 0)}
- 📥 Inbox Notes: {stats.get("inbox", 0)}
- 🧠 Concept Notes: {stats.get("concepts", 0)}
- 🗂️ Synthesis Projects: {stats.get("projects", 0)}

## How to Use

1. **Search Literature**
   ```
    unified_search(query="your topic of interest")
   ```

2. **Save Interesting Papers**
   ```
    save_reference_mcp(pmid="12345678")
   ```

3. **Capture or Curate Notes**
    ```
    write_library_note(section="inbox", filename="new-idea", content="...")
    move_library_note(filename="new-idea", from_section="inbox", to_section="concepts")
    ```

4. **When Ready to Materialize Wiki Pages**
    ```
    materialize_agent_wiki()
    ```

5. **When Ready to Convert to a Named Project**
    Library Wiki Path:
    ```
    convert_exploration_to_project(
         name="My Literature Library",
         workflow_mode="library-wiki"
    )
    ```

    Manuscript Path:
   ```
   convert_exploration_to_project(
       name="Your Research Title",
         workflow_mode="manuscript",
       paper_type="original-research"
   )
   ```

**Paths:**
- References: `{paths.get("references", "")}`
- Inbox: `{paths.get("inbox", "")}`
- Concepts: `{paths.get("concepts", "")}`
- Projects: `{paths.get("projects", "")}`
"""
        else:
            return f"❌ Error: {result.get('error', 'Unknown error')}"

    @tool()
    def convert_exploration_to_project(
        name: str,
        description: str = "",
        paper_type: str = "",
        workflow_mode: str = "",
        target_journal: str = "",
        keep_exploration: bool = False,
    ) -> str:
        """
        Convert exploration workspace to formal project. Transfers all saved content.

        Args:
            name: English project name (translate if needed)
            description: Brief description
            paper_type: original-research|meta-analysis|systematic-review|...
            workflow_mode: manuscript|library-wiki
            target_journal: Target journal
            keep_exploration: True=copy, False=move
        """
        result = project_manager.convert_temp_to_project(
            name=name,
            description=description,
            paper_type=paper_type,
            workflow_mode=workflow_mode,
            target_journal=target_journal,
            keep_temp=keep_exploration,
        )

        if result.get("success"):
            stats = result.get("stats", {})
            resolved_mode = result.get("workflow_mode", workflow_mode or "library-wiki")
            if resolved_mode == "library-wiki":
                structure_block = f"""```
{result.get("slug", "project")}/
├── project.json    ← Project settings
├── concept.md      ← Library workspace seed
├── .memory/        ← AI memory files
├── inbox/          ← {stats.get("inbox", 0)} file(s)
├── concepts/       ← {stats.get("concepts", 0)} file(s)
├── projects/       ← {stats.get("projects", 0)} file(s)
└── references/     ← {stats.get("references", 0)} reference(s)
```"""
                next_steps = """1. Continue curating references and notes
2. Use `write_library_note`, `move_library_note`, and `search_library_notes` to manage markdown notes
3. Build or refresh knowledge pages and dashboards
4. Switch to manuscript mode later if a paper concept emerges
"""
            else:
                structure_block = f"""```
{result.get("slug", "project")}/
├── project.json    ← Project settings
├── concept.md      ← Research concept template
├── .memory/        ← AI memory files
├── drafts/         ← {stats.get("drafts", 0)} file(s) transferred
├── references/     ← {stats.get("references", 0)} reference(s) transferred
├── data/           ← {stats.get("data_files", 0)} file(s) transferred
└── results/        ← Export directory
```"""
                next_steps = """1. Edit `concept.md` to define your research
2. Use `setup_project_interactive` to configure preferences
3. Start writing with `/mdpaper.draft`
"""

            return f"""{result.get("message", "Conversion complete!")}

## New Project Structure
{structure_block}

**Next Steps:**
{next_steps}
"""
        else:
            return f"""❌ Conversion Failed

{result.get("error", "Unknown error")}

**Troubleshooting:**
- Make sure you have an exploration workspace (use `start_exploration` first)
- Choose a unique project name in English
- Check that the paper_type is valid
- If you want a pure library project, set `workflow_mode="library-wiki"`
"""

    return {
        "start_exploration": start_exploration,
        "convert_exploration_to_project": convert_exploration_to_project,
    }
