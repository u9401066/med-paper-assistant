---
description: "🔍 mdpaper.search - 智能文獻搜尋與探索"
---

# 智能文獻搜尋

技能：literature-review + reference-management

## 情境判斷

先做 `project_action(action="current")` 讀 `workflow_mode`。

- `workflow_mode="manuscript"` + 有 concept.md → 情境 A（基於 Concept）
- `workflow_mode="library-wiki"` → 情境 B（Library Wiki Loop）
- 無專案 → 情境 C（探索式）

## 情境 A: 基於 Concept

1. `project_action(action="current")` + `read_draft("concept.md")` → 提取 Research Question、PICO、Key terms
2. 搜尋：快速 `unified_search(query)` / PICO `parse_pico() → generate_search_queries() → unified_search(query)` / MeSH `generate_search_queries() → unified_search(query)` / 擴展 `find_related_articles(pmid)` / 引用 `find_citing_articles(pmid)`
3. `save_reference_mcp(pmid, agent_notes)` ✅

## 情境 B: Library Wiki Loop (LLM Wiki Architecture)

1. `project_action(action="current")` → 確認是 `workflow_mode="library-wiki"`
2. 搜尋並 `save_reference_mcp(pmid)` (自動建立對應 reference 檔)
3. Triage & Tagging (inbox)：用 `write_library_note(section="inbox", ...)` 捕捉原始筆記，再用 `show_reading_queues()` 看目前 queue 狀態
4. Concept Building (concepts)：用 `create_concept_page(...)` 或 `move_library_note(...)` 把成熟想法整理成 concept pages，並補上 `[[concept]]` 雙向連結
5. Project Synthesis (projects)：把較高階的比較頁、workstream、review outline 移到 `projects/`，必要時用 `build_library_dashboard()` / `explain_library_path()` 回查知識網路

## 情境 C: 探索式

1. `project_action(action="start_exploration")` → 臨時工作區
2. `unified_search(query)` → `save_reference_mcp(pmid)`
3. 準備好時：
	- library 路徑 → `project_action(action="convert_exploration", name, workflow_mode="library-wiki")`
	- manuscript 路徑 → `project_action(action="convert_exploration", name, workflow_mode="manuscript", paper_type="...")`

## 快捷選項

| 選項     | 執行                        |
| -------- | --------------------------- |
| 快速找   | `unified_search()`                              |
| 精確找   | `generate_search_queries()` → `unified_search()` |
| PICO     | `parse_pico()` → `generate_search_queries()` → `unified_search()` |
| 相關論文 | `find_related_articles()`   |
| 誰引用   | `find_citing_articles()`    |

並行搜尋：多組 query → 合併去重 → 呈現
