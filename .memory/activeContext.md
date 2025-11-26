# Active Context - Development

## Current Focus
- MCP Server for VS Code + GitHub Copilot
- **Multi-Project Support** with per-project `.memory/`
- Project-aware prompts and tools

## System Memory vs Project Memory

| Type | Location | Purpose |
|------|----------|---------|
| **System Memory** | `.memory/` | Development notes, architecture, tool registry |
| **Project Memory** | `projects/{slug}/.memory/` | Research context, user preferences, progress |

## Architecture (Current)
```
med-paper-assistant/
├── .memory/                        # SYSTEM MEMORY (development)
│   ├── activeContext.md            # This file
│   ├── progress.md                 # Development milestones
│   └── .agent_constitution.md      # Agent behavior rules
├── projects/                       # RESEARCH PROJECTS
│   └── {project-slug}/
│       ├── project.json            # Settings (paper_type, preferences, memo)
│       ├── concept.md              # Research concept (type-specific template)
│       ├── .memory/                # PROJECT MEMORY
│       │   ├── activeContext.md    # User preferences, interaction style
│       │   └── progress.md         # Research milestones
│       ├── drafts/
│       ├── references/
│       ├── data/
│       └── results/
├── src/med_paper_assistant/
│   ├── core/
│   │   ├── project_manager.py      # Project management (paper types, settings)
│   │   ├── entrez/                 # Modular Entrez package (6 submodules)
│   │   ├── reference_manager.py    # Uses project paths
│   │   └── drafter.py              # Uses project paths
│   └── mcp_server/
│       ├── server.py               # Entry point
│       ├── config.py               # Tool selection guide (41 tools)
│       ├── tools/                  # 41 tools in 7 modules
│       └── prompts/                # 7 guided workflows
```

## MCP Prompts (7 total)
| Command | Description |
|---------|-------------|
| `/mdpaper.project` | **NEW** Setup project with paper type & preferences |
| `/mdpaper.concept` | Develop research concept |
| `/mdpaper.strategy` | Configure search strategy |
| `/mdpaper.draft` | Write paper sections |
| `/mdpaper.analysis` | Analyze data |
| `/mdpaper.clarify` | Refine content |
| `/mdpaper.format` | Export to Word |

## MCP Tools (41 total)
| Category | Count | Key Tools |
|----------|-------|-----------|
| Project | 8 | create_project, list_projects, switch_project, **get_paper_types**, **update_project_settings** |
| Search | 5 | search_literature, find_related/citing_articles |
| Reference | 8 | save_reference, read_reference_fulltext, format_references |
| Draft | 8 | write_draft, validate_concept, count_words |
| Analysis | 4 | analyze_dataset, generate_table_one, create_plot |
| Export | 8 | read_template → insert_section → save_document |

## Paper Types (7)
- `original-research`: Clinical trial, cohort, cross-sectional (IMRAD)
- `systematic-review`: PRISMA format
- `meta-analysis`: PRISMA + forest plots
- `case-report`: Intro, Case, Discussion
- `review-article`: Narrative review
- `letter`: Brief communication
- `other`: Editorial, perspective

## 🔴 Known Issues / TODO

### ✅ Prompt Design Issue (2025-11-26) - FIXED
**Problem:** MCP prompts (`/mdpaper.*`) 目前會把所有 prompt 內容直接輸出到 Copilot 輸入欄位

**Solution Applied:**
- 所有 prompts 改為極簡的 `[AGENT INSTRUCTION]` 格式
- Prompt 只包含 Agent 需要執行的步驟
- Agent 收到指令後應該用自己的話開始對話
- 字數從 1500-3000 減少到 300-900

### 🟡 MCP Prompt UX Limitation (2025-11-26)
**User Request:** 用戶想要 `/mdpaper.project` 像 `/speckit.specify` 一樣：
- 變成藍色後，用戶可以在後面繼續輸入文字
- 不跳出額外視窗詢問參數

**Root Cause:** 這是 **VS Code Copilot 客戶端的行為**，不是 FastMCP 可以控制的：
- 如果 prompt 定義了 `arguments`，VS Code 會跳出對話框詢問
- 如果沒有 arguments，prompt 內容會直接展開到對話中

**✅ Solution Found: Elicitation (2025-11-26)**
FastMCP 支援 **Elicitation** 功能（`mcp` 1.22.0）：
- 讓 tool 可以暫停執行並向用戶請求輸入
- 用戶在客戶端看到對話框填寫資料
- 支援 Pydantic schema 定義輸入格式

**Implementation:**
```python
from mcp.server.elicitation import AcceptedElicitation, DeclinedElicitation
from pydantic import BaseModel
from typing import Literal

class PaperTypeSelection(BaseModel):
    paper_type: Literal['original-research', 'meta-analysis', ...]

@mcp.tool
async def configure_project(ctx: Context) -> str:
    result = await ctx.elicit("What type of paper?", schema=PaperTypeSelection)
    if result.action == "accept":
        # result.data.paper_type contains the selection
        ...
```

**Reference:** https://gofastmcp.com/servers/elicitation

---
*Last Updated: 2025-11-26*
