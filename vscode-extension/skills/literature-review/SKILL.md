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
| Session | `get_session_pmids` / `get_session_summary`                                 | 取回搜尋結果       |
| 匯出    | `prepare_export` / `analyze_fulltext_access`                                | RIS/BibTeX/PMC     |

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
6. **匯出** — `format_references()` + `prepare_export(format="ris")`
7. **更新記憶** — 寫 `.memory/activeContext.md`（進度 + 關鍵文獻 + 觀察筆記）

## 決策點

| 時機               | 選擇                             |
| ------------------ | -------------------------------- |
| 建立專案 or 探索？ | 先探索熟悉文獻                   |
| 關鍵字 or PICO？   | 比較性問題用 PICO                |
| 結果數量           | 50-300 繼續，<20 擴展，>500 限縮 |
| 篩選方式           | <30 逐篇，>30 用 RCR 排序        |
