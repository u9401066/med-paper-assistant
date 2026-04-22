"""
Project Settings Tools

Update settings, get paper types, update status, interactive setup.
"""

import json

import structlog
from mcp.server.elicitation import AcceptedElicitation, CancelledElicitation, DeclinedElicitation
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from med_paper_assistant.domain.paper_types import get_paper_type_dict
from med_paper_assistant.domain.value_objects.author import Author, generate_author_block
from med_paper_assistant.infrastructure.persistence import ProjectManager
from med_paper_assistant.shared.constants import DEFAULT_WORKFLOW_MODE, WORKFLOW_MODES

from .._shared import get_optional_tool_decorator

# ============================================
# Pydantic Models for Elicitation
# ============================================


class PaperTypeSchema(BaseModel):
    """Schema for paper type selection - uses enum for dropdown."""

    paper_type: str = Field(
        description="Type of paper",
        json_schema_extra={
            "enum": [
                "original-research",
                "systematic-review",
                "meta-analysis",
                "case-report",
                "review-article",
                "letter",
                "other",
            ],
            "enumNames": [
                "Original Research",
                "Systematic Review",
                "Meta-Analysis",
                "Case Report",
                "Review Article",
                "Letter",
                "Other",
            ],
        },
    )


class TextInputSchema(BaseModel):
    """Schema for simple text input."""

    value: str = Field(default="", description="Enter text (optional)")


def register_settings_tools(
    mcp: FastMCP,
    project_manager: ProjectManager,
    *,
    register_public_verbs: bool = True,
):
    """Register project settings tools."""

    tool = get_optional_tool_decorator(mcp, register_public_verbs=register_public_verbs)

    @tool()
    def update_project_settings(
        paper_type: str = "",
        workflow_mode: str = "",
        target_journal: str = "",
        interaction_style: str = "",
        language_preference: str = "",
        writing_style: str = "",
        memo: str = "",
        status: str = "",
        citation_style: str = "",
    ) -> str:
        """
        Update project settings (paper type, status, preferences, citation style, memo).

        Args:
            paper_type: Paper type (use get_paper_types)
            workflow_mode: manuscript|library-wiki
            target_journal: Target journal
            interaction_style: AI interaction style
            language_preference: Language notes
            writing_style: Writing style notes
            memo: Project notes/reminders
            status: Project status (concept|drafting|review|submitted|published)
            citation_style: Citation style (vancouver|apa|harvard|nature|ama)
        """
        # Build interaction preferences dict
        interaction_preferences = {}
        if interaction_style:
            interaction_preferences["interaction_style"] = interaction_style
        if language_preference:
            interaction_preferences["language"] = language_preference
        if writing_style:
            interaction_preferences["writing_style"] = writing_style

        # Handle status update
        if status:
            status_result = project_manager.update_project_status(status)
            if not status_result.get("success"):
                return f"❌ Error updating status: {status_result.get('error', 'Unknown error')}"

        # Handle citation style update
        if citation_style:
            try:
                from med_paper_assistant.infrastructure.services import get_drafter

                drafter = get_drafter()
                drafter.set_citation_style(citation_style)
            except Exception:  # nosec B110 - Citation style is best-effort
                structlog.get_logger().debug(
                    "Citation style update failed (best-effort)", exc_info=True
                )
            # Also save to project settings
            if not interaction_preferences:
                interaction_preferences = {}
            interaction_preferences["citation_style"] = citation_style

        result = project_manager.update_project_settings(
            paper_type=paper_type if paper_type else None,
            workflow_mode=workflow_mode if workflow_mode else None,
            target_journal=target_journal if target_journal else None,
            interaction_preferences=interaction_preferences if interaction_preferences else None,
            memo=memo if memo else None,
        )

        if result.get("success"):
            updated = result.get("updated_fields", [])

            # Get current project info for display
            info = project_manager.get_project_info()
            prefs = info.get("interaction_preferences", {})
            current_workflow_mode = info.get("workflow_mode", DEFAULT_WORKFLOW_MODE)
            workflow_name = WORKFLOW_MODES.get(current_workflow_mode, {}).get(
                "name", current_workflow_mode
            )

            output = f"""✅ Project Settings Updated!

**Updated Fields:** {", ".join(updated)}

## Current Settings

| Setting | Value |
|---------|-------|
| Workflow Mode | {workflow_name} |
| Paper Type | {info.get("paper_type", "Not set")} |
| Target Journal | {info.get("target_journal", "Not set")} |

## Interaction Preferences
- **Style:** {prefs.get("interaction_style", "Not set")}
- **Language:** {prefs.get("language", "Not set")}
- **Writing:** {prefs.get("writing_style", "Not set")}

## Memo
{info.get("memo", "[No memo]")}

---
These settings are saved in `project.json` and `.memory/activeContext.md`
"""
            return output
        else:
            return f"❌ Error: {result.get('error', 'Unknown error')}"

    @tool()
    async def setup_project_interactive(ctx: Context) -> str:
        """
        Interactive project setup wizard using elicitation (paper type, preferences, memo).
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
        project_name = info.get("name", current)
        paper_type = info.get("paper_type", "")
        workflow_mode = info.get("workflow_mode", DEFAULT_WORKFLOW_MODE)
        workflow_name = WORKFLOW_MODES.get(workflow_mode, {}).get("name", workflow_mode)
        prefs = info.get("interaction_preferences", {})
        stats = info.get("stats", {})

        if workflow_mode == "library-wiki":
            return f"""## 📚 專案: {project_name}

| 設定 | 值 |
|------|-----|
| **Workflow Mode** | {workflow_name} |
| **Status** | {info.get("status", "concept")} |
| **Target Journal** | {info.get("target_journal", "Optional later")} |

### 專案內容
- 📚 References: {stats.get("references", 0)} saved
- 📥 Inbox notes: {stats.get("inbox", 0)} files
- 🧠 Concept notes: {stats.get("concepts", 0)} files
- 🗂️ Synthesis projects: {stats.get("projects", 0)} files

### 互動偏好
- **Style:** {prefs.get("interaction_style", "Default")}

### Memo
{info.get("memo", "[No memo]")}

---
**Library Wiki Path 建議順序**
1. `/mdpaper.search` 搜尋並保存文獻
2. `save_reference_mcp` / 匯入 markdown 或 web source 到 inbox
3. 整理成 `concepts/` 原子筆記，並補上 tags / wikilinks
4. 如果要開始寫論文，再用 `update_project_settings(workflow_mode="manuscript", paper_type="...")`
"""

        # Check if project is already configured (has paper_type set)
        if paper_type:
            paper_type_info = get_paper_type_dict(paper_type)

            return f"""## 📁 專案: {project_name}

| 設定 | 值 |
|------|-----|
| **Workflow Mode** | {workflow_name} |
| **Paper Type** | {paper_type_info.get("name", paper_type)} |
| **Status** | {info.get("status", "concept")} |
| **Target Journal** | {info.get("target_journal", "Not set")} |

### 專案內容
- 📝 Drafts: {stats.get("drafts", 0)} files
- 📚 References: {stats.get("references", 0)} saved
- 📊 Data files: {stats.get("data_files", 0)}

### 互動偏好
- **Style:** {prefs.get("interaction_style", "Default")}

### Memo
{info.get("memo", "[No memo]")}

---
**[AGENT: 請詢問用戶想要進行什麼操作]**

建議選項:
1. 📚 搜尋文獻 (`search_literature`)
2. ✍️ 撰寫論文段落 (`/mdpaper.draft`)
3. 📊 分析資料 (`/mdpaper.analysis`)
4. 📄 匯出 Word (`/mdpaper.format`)
5. ⚙️ 修改專案設定 (`update_project_settings`)

💡 **Journal Profile 提示**: 系統內建麻醉學前 20 大期刊的投稿設定（`templates/journal-profiles/`），
可直接請 Copilot 讀取期刊設定檔（如 `bja.yaml`、`anesthesiology.yaml`）來建立 `journal-profile.yaml`。
"""

        # Project not configured yet - run setup wizard
        # Step 1: Paper Type (Required)
        paper_type_result = await ctx.elicit(
            message=f"Setting up project: **{project_name}**\n\nSelect paper type:",
            schema=PaperTypeSchema,
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
            message="Interaction preferences? (e.g., '中文回答', 'Be concise', 'Explain reasoning')\n\nLeave blank to skip.",
            schema=TextInputSchema,
        )

        if isinstance(prefs_result, AcceptedElicitation) and prefs_result.data.value:
            project_manager.update_project_settings(
                interaction_preferences={"interaction_style": prefs_result.data.value}
            )

        # Step 3: Project Memo (Optional)
        memo_result = await ctx.elicit(
            message="Project notes/memo? (e.g., deadlines, co-authors, IRB info)\n\nLeave blank to skip.",
            schema=TextInputSchema,
        )

        if isinstance(memo_result, AcceptedElicitation) and memo_result.data.value:
            project_manager.update_project_settings(memo=memo_result.data.value)

        # Get final settings
        final_info = project_manager.get_project_info(current)
        final_prefs = final_info.get("interaction_preferences", {})

        paper_type_info = get_paper_type_dict(paper_type) if paper_type else {}

        return f"""✅ Project Setup Complete!

## {project_name}

| Setting | Value |
|---------|-------|
| **Workflow Mode** | {workflow_name} |
| **Paper Type** | {paper_type_info.get("name", paper_type)} |
| **Typical Sections** | {paper_type_info.get("sections", "N/A")} |
| **Target Journal** | {final_info.get("target_journal", "Not set")} |

### Interaction Preferences
- **Style:** {final_prefs.get("interaction_style", "Default")}
- **Language:** {final_prefs.get("language", "Default")}
- **Writing:** {final_prefs.get("writing_style", "Default")}

### Memo
{final_info.get("memo", "[No memo]")}

---
**Next Steps:**
1. 📋 設定期刊 profile — 請 Copilot 讀取 `templates/journal-profiles/` 內建期刊設定，
   或提供投稿指南 URL，自動產生 `journal-profile.yaml`
2. Edit `concept.md` to define your research concept
3. Use `search_literature` to find relevant papers
4. Use `write_draft` to start writing sections

💡 **Tip**: 系統內建麻醉學前 20 大期刊投稿設定，直接告訴 Copilot 目標期刊名稱即可自動套用。
"""

    @tool()
    def update_authors(authors_json: str) -> str:
        """
        Set or update the author list for the current project.

        Each author entry can be a name string or a structured object.
        Structured format supports affiliations, ORCID, email, and
        corresponding author flag.

        Args:
            authors_json: JSON array of authors. Examples:
                Simple: '["Author One", "Author Two"]'
                Structured: '[{"name": "Tz-Ping Gau", "affiliations": ["Dept of Anesthesiology, Kaohsiung Medical University Hospital, Kaohsiung, Taiwan"], "orcid": "0000-0001-2345-6789", "email": "gau@example.com", "is_corresponding": true, "order": 1}]'
        """
        try:
            authors = json.loads(authors_json)
        except json.JSONDecodeError as e:
            return f"❌ Error parsing authors_json: {e}"

        if not isinstance(authors, list):
            return "❌ Error: authors_json must be a JSON array."

        result = project_manager.update_authors(authors)

        if not result.get("success"):
            return f"❌ Error: {result.get('error', 'Unknown error')}"

        # Display formatted author info
        stored = result.get("authors", [])
        author_objs = [Author.from_dict(a) for a in stored]
        block = generate_author_block(author_objs)

        output = f"✅ Updated {len(stored)} author(s)!\n\n"
        output += "### Author Block Preview\n\n"
        output += block if block else "(No authors)\n"
        output += "\n---\n"
        output += "This info is stored in `project.json` and used for title page generation."

        return output

    return {
        "update_project_settings": update_project_settings,
        "setup_project_interactive": setup_project_interactive,
        "update_authors": update_authors,
    }
