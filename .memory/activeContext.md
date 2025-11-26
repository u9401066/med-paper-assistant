# Active Context - Development

## Current Focus: MCP Server Refactoring (2025-11-26)

### 重構計畫

**目標**: 整理 mcp_server 模組，提高程式碼品質和可維護性

**現有結構分析**:
```
mcp_server/           (2291 lines total)
├── config.py         (154 lines) - SERVER_INSTRUCTIONS, constants
├── server.py         (113 lines) - Entry point, clean
├── tools/            (1881 lines)
│   ├── __init__.py   (24 lines) - OK
│   ├── project_tools.py (569 lines) - 10 tools, includes elicitation
│   ├── export_tools.py  (317 lines) - 10 tools
│   ├── reference_tools.py (238 lines) - 9 tools
│   ├── search_tools.py  (192 lines) - 7 tools  
│   ├── draft_tools.py   (281 lines) - 10 tools
│   └── analysis_tools.py (260 lines) - 5 tools
└── prompts/          (143 lines)
    ├── __init__.py   (9 lines) - OK
    └── prompts.py    (134 lines) - 7 prompts + completion handler
```

**問題識別**:
1. ✅ `config.py` - SERVER_INSTRUCTIONS 太長，混合憲法和指南
2. ✅ `project_tools.py` - 569 lines，太大，可以拆分
3. ⚠️ Import 風格不統一 (有些用 Literal, 有些不用)
4. ⚠️ Elicitation 相關 imports 需要整理
5. ✅ `prompts.py` - 已經精簡化

**重構步驟**:
1. [x] 分析現有結構
2. [ ] 更新 .memory 文件
3. [ ] 重構 config.py - 分離常數和指令生成
4. [ ] 重構 tools - 統一 import，拆分大檔案
5. [ ] 重構 prompts - 確認精簡化完成
6. [ ] 更新 server.py - 整理入口點
7. [ ] 驗證並提交

---

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
│       ├── config.py               # Tool selection guide (42 tools)
│       ├── tools/                  # 42 tools in 7 modules
│       └── prompts/                # 7 guided workflows
```

## MCP Tools (42 total)
| Category | Count | Module |
|----------|-------|--------|
| Project | 9 | project_tools.py (includes setup_project_interactive) |
| Search | 5 | search_tools.py |
| Reference | 8 | reference_tools.py |
| Draft | 8 | draft_tools.py |
| Analysis | 4 | analysis_tools.py |
| Export | 8 | export_tools.py |

## MCP Prompts (7 total)
All prompts are minimal agent instructions:
- `/mdpaper.project` → setup_project_interactive()
- `/mdpaper.concept` → search + save + write concept
- `/mdpaper.strategy` → configure_search_strategy()
- `/mdpaper.draft` → read concept + write draft
- `/mdpaper.analysis` → analyze tools
- `/mdpaper.clarify` → refine draft
- `/mdpaper.format` → export workflow

---
*Last Updated: 2025-11-26*
