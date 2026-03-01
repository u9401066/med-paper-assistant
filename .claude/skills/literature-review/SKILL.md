---
name: literature-review
description: 系統性文獻搜尋、篩選、下載、整理。觸發：文獻回顧、找論文、搜尋文獻、systematic review、literature search、PubMed、找文章、搜paper、review、reference、citation、引用、參考文獻、背景調查、background。
---

# 系統性文獻回顧

適用：新研究專案 | Introduction 前調查 | 系統性回顧 | PICO 臨床問題
不適用：快速查一篇 → 直接 `search_literature` | 只需整理 → `format_references`

---

## 工具速查

### pubmed-search MCP

| 類別    | 工具                                                                        | 說明               |
| ------- | --------------------------------------------------------------------------- | ------------------ |
| 搜尋    | `search_literature`                                                         | 基本 PubMed 搜尋   |
|         | `generate_search_queries`                                                   | MeSH + 同義詞材料  |
|         | `parse_pico`                                                                | 解析 PICO 臨床問題 |
|         | `merge_search_results`                                                      | 合併去重           |
| 探索    | `find_related_articles` / `find_citing_articles` / `get_article_references` | 引用網路           |
|         | `get_citation_metrics`                                                      | iCite RCR 排序     |
| 全文    | `get_fulltext(pmcid)`                                                       | 取得 OA 全文       |
|         | `analyze_fulltext_access(pmids)`                                            | 確認 OA 狀態       |
| Session | `get_session_pmids` / `get_session_summary`                                 | 取回搜尋結果       |
| 匯出    | `prepare_export`                                                            | RIS/BibTeX         |

### asset-aware-mcp（全文解析）

| 類別    | 工具                            | 說明                       |
| ------- | ------------------------------- | -------------------------- |
| 解析    | `ingest_documents(file_paths)`  | PDF 結構化解析（雙引擎）    |
|         | `parse_pdf_structure(file_path)`| Marker 高精度解析           |
| 狀態    | `get_job_status(job_id)`        | 追蹤非同步處理進度          |
| 瀏覽    | `inspect_document_manifest(doc_id)` | 取得完整資產清單        |
|         | `list_section_tree(doc_id)`     | 文件章節結構               |
| 提取    | `get_section_content(doc_id, section_path)` | 取得特定段落內容 |
|         | `fetch_document_asset(doc_id, asset_type, asset_id)` | 取得圖表等資產 |
| 知識圖  | `consult_knowledge_graph(query)`| 跨文獻 RAG 查詢            |

### mdpaper 儲存文獻

| 方法                          | 說明                         |
| ----------------------------- | ---------------------------- |
| `save_reference_mcp(pmid)` ✅ | **永遠優先** MCP-to-MCP 驗證 |
| `save_reference(article)` ⚠️  | FALLBACK 僅 API 不可用       |

---

## 工作流

1. **環境準備** — `get_current_project()` + 讀 `.memory/activeContext.md`
2. **搜尋策略** — 一般主題：`generate_search_queries(topic)` → PICO 問題：`parse_pico()` → 並行 `generate_search_queries()` 各元素
3. **並行搜尋** — 多組 `search_literature()` 同時呼叫 → `merge_search_results()`
4. **評估擴展** — <20 篇 `expand_search_queries()` | 引用網路 `find_citing/related/references` | `get_citation_metrics(sort_by="relative_citation_ratio")`
5. **篩選儲存** — 呈現清單（標題/年份/期刊/RCR）→ `save_reference_mcp(pmid)`
6. **全文閱讀** ⭐ — 對每篇已儲存文獻：
   a. `analyze_fulltext_access(pmids)` → 確認哪些有全文可取得
   b. 有全文者：`get_fulltext(pmcid)` 或下載 PDF → asset-aware `ingest_documents(file_paths)` → `get_job_status()` → `inspect_document_manifest()` → `get_section_content(doc_id, "Methods")` / `get_section_content(doc_id, "Results")`
   c. 無全文者：在 metadata.json 記錄 `fulltext_ingested: false` + 原因
   d. 產出 `references/fulltext-ingestion-status.md` 彙總表
   e. **原則**：未讀全文的文獻，後續寫作僅能引用 abstract 結論，不可引用具體方法或數據
7. **Subagent 分析** ⭐⭐ — 每篇論文由獨立 subagent 完成結構化分析（防止 context 汙染）：
   a. `get_reference_for_analysis(pmid)` → 取得該文獻的結構化全文包（abstract + fulltext，≤30K char）
   b. `runSubagent` 啟動獨立 subagent，prompt 必須包含：
      - 步驟 a 的完整全文內容
      - 分析任務：撰寫結構化摘要、評估方法學品質、列出關鍵發現與限制、判斷可用於文章 Introduction/Methods/Results/Discussion 哪些段落
      - 指示 subagent 最後呼叫 `save_reference_analysis(pmid, summary, methodology, key_findings, limitations, usage_sections, relevance_score)`
   c. Subagent 完成後：`analysis.json` 已寫入 reference 目錄，metadata 標記 `analysis_completed: true`
   d. **原則**：主 Agent 後續寫作只使用 `analysis_summary`，不再重讀全文
   e. **Gate**：所有引用的文獻必須通過分析（Pipeline Gate Phase 2.1 + Hook C10 強制檢查）
8. **匯出** — `format_references()` + `prepare_export(format="ris")`
9. **更新記憶** — 寫 `.memory/activeContext.md`（進度 + 關鍵文獻 + 全文閱讀狀態 + 分析狀態 + 觀察筆記）

## 決策點

| 時機               | 選擇                             |
| ------------------ | -------------------------------- |
| 建立專案 or 探索？ | 先探索熟悉文獻                   |
| 關鍵字 or PICO？   | 比較性問題用 PICO                |
| 結果數量           | 50-300 繼續，<20 擴展，>500 限縮 |
| 篩選方式           | <30 逐篇，>30 用 RCR 排序        |
