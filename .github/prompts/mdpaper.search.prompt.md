---
description: "🔍 mdpaper.search - 智能文獻搜尋與探索"
---

# 智能文獻搜尋

技能：literature-review + reference-management

## 情境判斷

有專案 + concept.md → 情境 A（基於 Concept）| 否則 → 情境 B（探索式）

## 情境 A: 基於 Concept

1. `project_action(action="current")` + `read_draft("concept.md")` → 提取 Research Question、PICO、Key terms
2. 搜尋：快速 `search_literature(query)` / PICO `parse_pico()→generate_queries()` / MeSH `generate_search_queries()` / 擴展 `find_related_articles(pmid)` / 引用 `find_citing_articles(pmid)`
3. `save_reference_mcp(pmid, agent_notes)` ✅

## 情境 B: 探索式

1. `project_action(action="start_exploration")` → 臨時工作區
2. `search_literature(query)` → `save_reference_mcp(pmid)`
3. 準備好時 `project_action(action="convert_exploration", name)`

## 快捷選項

| 選項     | 執行                        |
| -------- | --------------------------- |
| 快速找   | `search_literature()`       |
| 精確找   | `generate_search_queries()` |
| PICO     | `parse_pico()` workflow     |
| 相關論文 | `find_related_articles()`   |
| 誰引用   | `find_citing_articles()`    |

並行搜尋：多組 query → 合併去重 → 呈現
