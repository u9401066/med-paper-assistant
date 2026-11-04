# Research Workflow Guide for Copilot

> 這份指南幫助 Copilot 理解如何正確使用 Zotero + PubMed MCP tools (v0.3.8)

## 🔍 文獻搜尋流程

### 步驟 1: 了解研究問題

由 Agent 將研究問題拆解為 PICO 結構，再用 `validate_pico_plan` 驗證並取得可執行 pipeline：

- **P**opulation: 研究對象
- **I**ntervention: 介入措施
- **C**omparison: 對照組
- **O**utcome: 結果指標

### 步驟 2: 生成搜尋策略

使用 `generate_search_queries` 產生專業的搜尋策略，包含：

- MeSH terms
- Boolean operators
- Field tags

### 步驟 3: 執行搜尋

使用 `unified_search` 搜尋多個來源（PubMed、Europe PMC、CORE 等），注意：

- 結果會自動快取到 Session
- 使用 `get_session_pmids` 取得已搜尋的 PMID
- **不要重複搜尋相同的關鍵字**
- `unified_search` 會自動合併去重多個來源的結果

#### 進階搜尋參數

| 參數                 | 用途                              | 範例                                                   |
| -------------------- | --------------------------------- | ------------------------------------------------------ |
| `include_preprints`  | 搜尋 arXiv/medRxiv/bioRxiv 預印本 | `unified_search(query="...", include_preprints=true)`  |
| `peer_reviewed_only` | 只顯示同行審查文章                | `unified_search(query="...", peer_reviewed_only=true)` |

### 步驟 4: 過濾已有文獻

使用 `search_pubmed_exclude_owned` 直接搜尋「尚未擁有」的新文獻

---

## 📥 匯入 Zotero 流程

### ⚠️ 重要：先詢問 Collection！

在匯入任何文獻前，**必須先詢問用戶**要存入哪個 Collection。

### 匯入方式選擇

| 情境            | 推薦工具                   | 說明                 |
| --------------- | -------------------------- | -------------------- |
| 少量文獻 (1-5)  | `quick_import_pmids`       | 簡單快速             |
| 中量文獻 (5-20) | `import_from_pmids`        | 可指定 collection    |
| 大量文獻 (20+)  | `batch_import_from_pubmed` | 批次處理，有進度回報 |
| 有 RIS 檔案     | `import_ris_to_zotero`     | 標準格式匯入         |

### 匯入前確認清單

1. ✅ 已詢問目標 Collection
2. ✅ 已確認 PMID 列表（使用 `get_session_pmids` 取得）
3. ✅ 已提醒用戶文獻數量

---

## 🔄 Session 管理

### 為什麼需要 Session？

- PubMed 搜尋結果會快取
- 避免重複 API 呼叫
- 保持 PMID 追蹤，不依賴 Agent 記憶

### Session 工具使用時機

| 工具                  | 何時使用                               |
| --------------------- | -------------------------------------- |
| `get_session_pmids`   | 需要取得之前搜尋的 PMID                |
| `list_search_history` | 查看本次對話的搜尋紀錄                 |
| `get_cached_article`  | 取得已快取的文章詳情（避免重複 fetch） |
| `get_session_summary` | 檢查 Session 狀態                      |

---

## 📚 Zotero 書庫管理

### 查詢現有文獻

1. `list_collections` - 先看有哪些 Collections
2. `get_collection_items` - 取得特定 Collection 的文獻
3. `search_items` - 在書庫中搜尋

### 避免重複匯入

使用 `check_articles_owned` 檢查 PMID 是否已存在

### 書庫分析

- `get_library_stats` - 統計分析
- `find_orphan_items` - 找出孤兒文獻（未分類）

---

## 🔬 進階工具

### 引用網路

- `build_citation_tree` - 從一篇文章建構引用網路（前向+後向）
- `find_citing_articles` - 找出引用某篇文章的後續研究
- `get_article_references` - 取得文章的參考文獻

### ICD ↔ MeSH 轉換

- `convert_icd_mesh` - 雙向轉換 ICD 代碼和 MeSH 術語
- `search_by_icd` - 用 ICD 代碼搜尋 PubMed（自動轉換為 MeSH）

### 研究時間軸

- `build_research_timeline` - 建構研究主題的歷史演進時間軸
- `compare_timelines` - 比較多個研究領域的時間軸

### 圖片搜尋

- `search_biomedical_images` - 搜尋 Open-i 和 Europe PMC 的生物醫學圖片

### NCBI 延伸資料庫

- `search_gene` / `get_gene_details` - 基因資訊
- `search_compound` / `get_compound_details` - 化合物/藥物資訊
- `search_clinvar` - 臨床變異搜尋

---

## ⚠️ 常見錯誤避免

### ❌ 錯誤做法

1. 搜尋後直接匯入，沒問 Collection
2. 重複搜尋相同關鍵字
3. 匯入時沒確認 PMID 列表
4. 從 PubMed 重新取摘要（Zotero 已有）

### ✅ 正確做法

1. 搜尋 → 確認結果 → 詢問 Collection → 匯入
2. 用 `get_session_pmids` 取得已有的 PMID
3. 用 `get_item` 從 Zotero 讀取已存文獻的詳情
4. 匯入前用 `check_articles_owned` 檢查重複

---

## 🎯 典型對話流程範例

```
用戶: 幫我找最近的 AI 麻醉研究

Copilot 動作:
1. validate_pico_plan: 驗證 Agent 拆解的 PICO
2. generate_search_queries: 產生搜尋策略
3. unified_search: 執行多來源搜尋
4. [回報結果，詢問是否要存入 Zotero]
5. list_collections: 取得 Collection 列表
6. [詢問用戶要存入哪個 Collection]
7. quick_import_pmids 或 batch_import_from_pubmed: 匯入
8. [確認完成]
```
