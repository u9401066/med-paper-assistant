# Active Context

## User Preferences
- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點
CRUD Delete 操作已完成，可繼續 Phase 4 其他功能

## 最近變更 (2026-01-06)

### 1. CRUD Delete 操作實作 ✅ (剛完成)
- **delete_reference(pmid)** - 刪除文獻（含確認機制）
- **delete_draft(filename)** - 刪除草稿（含確認機制）
- **archive_project(slug)** - 軟刪除/封存專案
- **delete_project(slug)** - 永久刪除專案

### 2. 智慧引用助手 (Citation Assistant) ✅
- `CitationAssistant` 核心服務
- MCP 工具：`suggest_citations`, `scan_draft_citations`, `find_citation_for_claim`
- 聲稱類型識別 + 本地文獻庫搜尋 + PubMed 查詢建議

### 3. CRUD 盤點完成 ✅
- 52 → 56 個 MCP 工具（+4 Delete）
- 所有 6 個 Entity 皆已有 Delete 操作

## 相關檔案
- `src/med_paper_assistant/infrastructure/persistence/reference_manager.py` - delete_reference 方法
- `src/med_paper_assistant/interfaces/mcp/tools/reference/manager.py` - delete_reference 工具
- `src/med_paper_assistant/interfaces/mcp/tools/draft/writing.py` - delete_draft 工具
- `src/med_paper_assistant/interfaces/mcp/tools/project/crud.py` - archive_project, delete_project 工具

## 待解決問題
- [ ] Dashboard → Copilot 主動通訊（VS Code Chat API 限制）

## 下一步 (Phase 4 MVP)
- [ ] `generate_table_one` - 自動生成 Table 1
- [ ] `check_manuscript_consistency` - 跨章節一致性檢查
- [ ] `create_reviewer_response` - Reviewer Response 生成器

## 更新時間
2026-01-06 10:30
