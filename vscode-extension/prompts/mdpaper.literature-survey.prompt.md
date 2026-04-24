---
description: "📚 literature-survey - 系統性文獻調查"
---

# 系統性文獻調查 / Library Landscape Survey

編排：parallel-search → literature-review → reference-management

適用兩種輸出：

- Library Wiki Path：建立可查詢的主題地景、比較頁、synthesis page、dashboard
- Manuscript Path：建立可追溯的 review corpus，之後進 concept / draft / PRISMA

## Phase 1: 定義搜尋範圍

問用戶：研究問題、PICO（P/I/C/O）、年份範圍、語言、文章類型

## Phase 2: 多維度搜尋

1. `parse_pico()` / `generate_search_queries(topic, strategy="comprehensive")` → 5 組查詢
2. 並行 `unified_search(query)` 各 100 篇或不同來源
3. 若需要整併多批結果，再用 `merge_search_results()` 去重

## Phase 3: 評估擴展

| 結果數  | 行動                                                                                 |
| ------- | ------------------------------------------------------------------------------------ |
| < 20    | `generate_search_queries(topic, strategy="exploratory")` / `expand_search_queries()` |
| 20-100  | 適中                                                                                 |
| 100-300 | 篩選                                                                                 |
| > 300   | 縮小                                                                                 |

引用網路：`find_related_articles` + `find_citing_articles` + `get_article_references`

## Phase 4: 篩選

`get_citation_metrics(pmids="last", sort_by="relative_citation_ratio")` → 呈現清單（標題/年份/期刊/RCR/全文）

## Phase 5: 儲存

`save_reference_mcp(pmid, agent_notes)` ✅ → 記錄搜尋策略（日期+查詢+結果數）→ `format_references()` + `prepare_export(format="ris")`

## 分流輸出

Library Wiki Path：保存後繼續做 knowledge map / synthesis pages / dashboard notes

Manuscript Path：保存後更新 concept、規劃 PRISMA、準備後續 drafting

## PRISMA（系統性回顧）

記錄：搜尋日期、各查詢結果數、去重→標題篩選→全文篩選→最終納入

## Session 恢復

`get_session_pmids(-1)` / `get_session_summary()`
