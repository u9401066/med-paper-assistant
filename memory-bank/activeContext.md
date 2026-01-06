# Active Context

## User Preferences
- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點
實作 CRUD Delete 操作補齊，從最高優先的 `delete_reference` 開始

## 最近變更 (2026-01-06)

### 1. 智慧引用助手 (Citation Assistant) ✅
- 新增 `CitationAssistant` 核心服務
- MCP 工具：`suggest_citations`, `scan_draft_citations`, `find_citation_for_claim`
- 聲稱類型識別 + 本地文獻庫搜尋 + PubMed 查詢建議

### 2. CRUD 盤點完成 ✅
- 52 個 MCP 工具分類盤點
- **關鍵發現**: 所有 6 個 Entity 皆無 Delete 操作
- ROADMAP 更新 Phase 4.5 加入 Delete 操作補齊

### 3. CRUD Delete 操作實作 ⏳ (進行中)
優先順序：
1. `delete_reference(pmid)` ⭐⭐⭐⭐⭐ - 刪除儲存錯誤的文獻
2. `delete_draft(filename)` ⭐⭐⭐ - 刪除草稿
3. `archive_project(slug)` ⭐⭐⭐ - 封存專案

## 相關檔案
- `src/med_paper_assistant/interfaces/mcp/tools/reference/` - Reference 工具
- `src/med_paper_assistant/interfaces/mcp/tools/draft/` - Draft 工具
- `src/med_paper_assistant/interfaces/mcp/tools/project/` - Project 工具

## 待解決問題
- [ ] Dashboard → Copilot 主動通訊（VS Code Chat API 限制）

## 更新時間
2026-01-06 10:00
