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

**Root Cause:** 這是 **VS Code Copilot 客戶端的行為**，無法從 MCP Server 端改變：
- MCP Prompts 選擇後會**展開成文字**顯示在對話中
- 如果 prompt 有 `arguments`，VS Code 會跳出對話框詢問

**結論：MCP Prompts 設計限制**
根據 https://code.visualstudio.com/docs/copilot/chat/chat-tools：
- Tools 可以用 `#` 引用（如 `#mdpaper.setup_project_interactive`）
- Prompts 會展開成文字，這是設計如此

**推薦使用方式：**
1. **不使用 /mdpaper.* prompts**
2. **直接用自然語言**：
   - "configure my project" → Agent 調用 setup_project_interactive
   - "search papers about intubation" → Agent 調用 search_literature
   - "write introduction" → Agent 調用 write_draft
3. **或用 # 引用工具**：
   - `#mdpaper.setup_project_interactive`
   - `#mdpaper.search_literature airway management`

**Elicitation 功能仍然有效：**
setup_project_interactive 使用 ctx.elicit() 會顯示結構化輸入對話框

**Reference:** 
- https://code.visualstudio.com/docs/copilot/chat/chat-tools
- https://gofastmcp.com/servers/elicitation

---
*Last Updated: 2025-11-26*
