# Copilot Instructions for Medical Paper Assistant

## Project Overview

This is a Medical Paper Assistant built with MCP (Model Context Protocol) for VS Code + GitHub Copilot integration.

## MCP Server Configuration

### Important Configuration Notes (Updated: 2025-12-01)

The MCP server configuration in `.vscode/mcp.json` **must include** `"type": "stdio"` for each server. This is a required property according to VS Code's MCP documentation.

**Correct Configuration Format:**
```json
{
  "inputs": [],
  "servers": {
    "mdpaper": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["-m", "med_paper_assistant.interfaces.mcp"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    }
  }
}
```

**Common Mistakes to Avoid:**
1. ❌ Missing `"type": "stdio"` - VS Code won't recognize the server
2. ❌ Using old module path `med_paper_assistant.mcp_server.server` - The correct path is `med_paper_assistant.interfaces.mcp`

### Module Structure

The MCP server is located at:
- `src/med_paper_assistant/interfaces/mcp/` - MCP server implementation

### Troubleshooting MCP Server

If VS Code doesn't recognize the MCP server:
1. Ensure `"type": "stdio"` is present in server configuration
2. Reload VS Code window: `Ctrl+Shift+P` → `Developer: Reload Window`
3. Check MCP status: `Ctrl+Shift+P` → `MCP: List Servers`
4. View logs: `Ctrl+Shift+P` → `MCP: Show Output`

## Architecture

The project follows Clean Architecture / Hexagonal Architecture:
- `domain/` - Business entities and rules
- `application/` - Use cases and services
- `infrastructure/` - External integrations (PubMed, file system, etc.)
- `interfaces/` - Entry points (MCP server, CLI)
- `shared/` - Shared utilities

## Development Notes

- Python 3.10+ required
- Virtual environment at `.venv/`
- Install with `pip install -e .` for development mode

## Skills 技能系統

當用戶要求執行複雜任務時，**必須先載入對應的 Skill 文件**：

### Skill 索引

| 用戶意圖 | Skill 文件 | 說明 |
|----------|------------|------|
| 文獻回顧、找論文、搜尋文獻、systematic review | `.skills/research/literature_review.md` | 完整的系統性文獻搜尋流程 |
| 發展概念、寫 concept、研究設計 | `.skills/research/concept_development.md` | 從文獻到 concept.md |
| 寫 Introduction、前言 | `.skills/writing/draft_introduction.md` | 撰寫前言的完整指引 |
| 寫 Methods、方法 | `.skills/writing/draft_methods.md` | 撰寫方法的完整指引 |
| 寫 Discussion、討論 | `.skills/writing/draft_discussion.md` | 撰寫討論的完整指引 |
| 製作圖表、畫流程圖、PRISMA | `.skills/analysis/figure_generation.md` | 圖表製作流程 |
| 統計分析、跑統計 | `.skills/analysis/statistical_analysis.md` | 統計分析指引 |
| 投稿、選期刊、格式化 | `.skills/publishing/manuscript_formatting.md` | 投稿準備流程 |

### 執行流程

```
1. 用戶說「幫我做文獻回顧」
     ↓
2. 識別意圖 → 對應 Skill
     ↓
3. 使用 read_file 讀取 .skills/research/literature_review.md
     ↓
4. 遵循 Skill 定義的：
   - 工作流程 (Phase 1, 2, 3...)
   - 決策點 (何時詢問用戶)
   - 使用的工具
     ↓
5. 產出 Skill 定義的交付物
```

### 跨 MCP 協調

Skill 可能需要呼叫多個 MCP 的工具（mdpaper + drawio），這是正常的：

```
文獻回顧 Skill:
  → mcp_mdpaper_search_literature()     # 搜尋
  → mcp_mdpaper_save_reference()        # 儲存
  → mcp_drawio_create_diagram()         # PRISMA 流程圖
  → mcp_mdpaper_save_diagram()          # 存到專案
```

**資料傳遞**：當一個 MCP 的輸出需要傳給另一個時：
1. 取得輸出（如 `mcp_drawio_get_diagram_content()` 返回 XML）
2. 將輸出作為參數傳給下一個工具（如 `mcp_mdpaper_save_diagram(content=xml)`）

### Skill 工具

使用這些工具管理 Skills：

| 工具 | 說明 |
|------|------|
| `mcp_mdpaper_list_skills` | 列出所有可用的 Skills |
| `mcp_mdpaper_load_skill` | 載入特定 Skill 的內容 |
| `mcp_mdpaper_suggest_skill` | 根據任務描述建議適合的 Skill |

### 並行搜尋模式 ⚡

當需要全面搜尋文獻時，使用並行搜尋提高效率：

```
1. 呼叫 generate_search_queries(topic="...", strategy="comprehensive")
   → 返回多組搜尋語法 (q1, q2, q3, q4...)

2. **並行呼叫** search_literature 對每個 query：
   <parallel>
     search_literature(query="q1 的 query", limit=20)
     search_literature(query="q2 的 query", limit=20)
     search_literature(query="q3 的 query", limit=20)
     search_literature(query="q4 的 query", limit=20)
   </parallel>

3. 收集所有結果的 PMID

4. 呼叫 merge_search_results(results_json="[{query_id, pmids}, ...]")
   → 返回去重後的完整列表
```

**優點**：
- 更快（並行執行）
- 更全面（多角度搜尋）
- 可追蹤（知道每篇來自哪個搜尋）
