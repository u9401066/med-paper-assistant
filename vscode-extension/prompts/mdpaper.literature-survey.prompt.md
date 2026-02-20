---
description: "📚 literature-survey - 系統性文獻調查"
---

# 系統性文獻調查

編排：parallel-search → literature-review → reference-management

## Phase 1: 定義搜尋範圍

問用戶：研究問題、PICO（P/I/C/O）、年份範圍、語言、文章類型

## Phase 2: 多維度搜尋

1. `parse_pico()` / `generate_search_queries(topic, strategy="comprehensive")` → 5 組查詢
2. 並行 `search_literature()` 各 100 篇
3. `merge_search_results()` 去重

## Phase 3: 評估擴展

| 結果數  | 行動                      |
| ------- | ------------------------- |
| < 20    | `expand_search_queries()` |
| 20-100  | 適中                      |
| 100-300 | 篩選                      |
| > 300   | 縮小                      |

引用網路：`find_related_articles` + `find_citing_articles` + `get_article_references`

## Phase 4: 篩選

`get_citation_metrics(pmids="last", sort_by="relative_citation_ratio")` → 呈現清單（標題/年份/期刊/RCR/全文）

## Phase 5: 儲存

`save_reference_mcp(pmid, agent_notes)` ✅ → 記錄搜尋策略（日期+查詢+結果數）→ `format_references()` + `prepare_export(format="ris")`

## PRISMA（系統性回顧）

記錄：搜尋日期、各查詢結果數、去重→標題篩選→全文篩選→最終納入

## Session 恢復

`get_session_pmids(-1)` / `get_session_summary()`
