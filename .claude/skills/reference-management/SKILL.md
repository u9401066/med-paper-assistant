# Reference Management Skill

觸發：存這篇、save、儲存文獻、列出 references、citation、格式化、PDF、foam、wikilink

## 🔒 核心規則：MCP-to-MCP 優先

| 方法 | 資料來源 | 使用時機 |
|------|----------|----------|
| `save_reference_mcp(pmid)` | pubmed-search API 直取 | **永遠優先** |
| `save_reference(article)` | Agent 傳遞 metadata | 僅 API 不可用時 fallback |

信任層：🔒 VERIFIED（PubMed 原始）→ 🤖 AGENT（`agent_notes`）→ ✏️ USER（人類筆記，AI 不碰）

---

## MCP Tools

| 工具 | 用途 | 關鍵參數 |
|------|------|----------|
| `save_reference_mcp` ⭐ | 用 PMID 儲存（推薦）| `pmid`, `agent_notes?`, `project?` |
| `save_reference` | API 不可用時備援 | `article` (dict), `agent_notes?` |
| `list_saved_references` | 列出所有已儲存文獻 | `project?` |
| `search_local_references` | 在已存文獻中搜尋 | `query` |
| `get_reference_details` | 取得單篇完整資訊+格式化引用 | `pmid` |
| `check_reference_exists` | 檢查是否已儲存 | `pmid` |
| `read_reference_fulltext` | 讀取已下載 PDF | `pmid`, `max_chars?` (預設 10000) |
| `format_references` | 格式化引用清單 | `pmids` (逗號分隔), `style?`, `journal?` |
| `set_citation_style` | 設定預設引用格式 | `style` (vancouver/apa/harvard/nature/ama) |
| `rebuild_foam_aliases` | 重建 Foam wikilink 檔案 | `project?` |

---

## 標準工作流

1. `pubmed-search` 搜尋文獻
2. 用戶選擇要儲存的文獻
3. `save_reference_mcp(pmid="...")` → 成功則完成
4. 失敗 → 改用 `save_reference(article={...})`

## agent_notes 指南

好：`"Key SR on remimazolam safety. Covers: CV stability, respiratory effects. Limitation: only ICU."`
壞：`"重要文獻"` ← 太模糊。應包含：關聯性、關鍵發現、方法學優缺、可引用數據。

---

## 相關技能

| Skill | 關係 |
|-------|------|
| literature-review | 搜尋後呼叫本技能儲存 |
| draft-writing | 寫草稿時引用已儲存文獻 |
| concept-development | 驗證 novelty 時需文獻支持 |
