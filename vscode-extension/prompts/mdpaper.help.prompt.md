---
description: "❓ mdpaper.help - 指令與工作流程參考"
---

# 指令參考

## 兩條路

### Library Wiki Path (LLM Wiki / Karpathy Style)

`project_action(action="create", name="...", workflow_mode="library-wiki")` → `/mdpaper.search` or `unified_search(query)` → `save_reference_mcp` / ingest sources → `write_library_note` → `show_reading_queues` → `create_concept_page` / `move_library_note` → `build_library_dashboard` → query / synthesize → 覺得值得寫稿時再切去 manuscript

### Manuscript Path

`project_action(action="create", name="...", workflow_mode="manuscript", paper_type="...")` → `/mdpaper.search` → `/mdpaper.concept` → `/mdpaper.draft` → `/mdpaper.analysis` → `/mdpaper.clarify` → `/mdpaper.format`

## Prompt Workflows (`/mdpaper.*`)

這些 prompt workflows 來自 workspace prompt files；若是 VSIX 安裝面，先執行 `MedPaper: Setup Workspace` 讓它們落地到工作區。

| 指令                           | 用途                         |
| ------------------------------ | ---------------------------- |
| `/mdpaper.project`             | 建立/切換專案                |
| `/mdpaper.search`              | 文獻搜尋                     |
| `/mdpaper.strategy`            | 搜尋策略                     |
| `/mdpaper.concept`             | 發展概念                     |
| `/mdpaper.draft`               | 撰寫草稿                     |
| `/mdpaper.analysis`            | 資料分析                     |
| `/mdpaper.clarify`             | 潤稿                         |
| `/mdpaper.format`              | 匯出 Word                    |
| `/mdpaper.write-paper`         | 完整論文撰寫（11-Phase）     |
| `/mdpaper.literature-survey`   | 系統性文獻調查 / corpus 建置 |
| `/mdpaper.manuscript-revision` | 稿件修改與回覆審稿意見       |
| `/mdpaper.audit`               | 獨立審計與 review loop       |
| `/mdpaper.help`                | 顯示本說明                   |

## `@mdpaper` Chat 指令

| 指令                  | 用途             |
| --------------------- | ---------------- |
| `@mdpaper /search`    | 文獻搜尋         |
| `@mdpaper /draft`     | 撰寫草稿         |
| `@mdpaper /concept`   | 發展概念         |
| `@mdpaper /project`   | 專案管理         |
| `@mdpaper /format`    | 匯出文件         |
| `@mdpaper /analysis`  | 資料分析         |
| `@mdpaper /strategy`  | 搜尋策略         |
| `@mdpaper /drawio`    | Draw.io 圖表     |
| `@mdpaper /autopaper` | 全自動寫論文     |
| `@mdpaper /help`      | 顯示聊天指令說明 |

## 建議順序

Library Wiki Path (LLM Wiki / Karpathy Style): project → search / literature-survey or `unified_search()` → capture notes → review queues → concept pages / synthesis pages → dashboard / path explain → query → optional manuscript transition

Manuscript Path: project → search → concept → draft / write-paper → analysis → clarify → audit / manuscript-revision → format

## MCP 工具集

| Server        | 用途                                                                                    |
| ------------- | --------------------------------------------------------------------------------------- |
| mdpaper       | 專案/草稿/引用/分析/審查/匯出（full / compact tool surface + 3 prompts + 3 resources；最新計數以 README / validate gate 為準） |
| pubmed-search | 文獻搜尋/全文/引用分析                                                                  |
| cgu           | 創意發想（Novelty 不足時）                                                              |
| zotero-keeper | Zotero 整合（選用）                                                                     |

## 核心規則

- 儲存文獻：`save_reference_mcp(pmid)` 優先
- PubMed 搜尋：快速/多源搜尋優先 `unified_search(query)`；PICO / MeSH 再配 `parse_pico()` / `generate_search_queries()`
- 只有 Manuscript Path 的草稿前：`validation_action(action="concept", filename="concept.md")` 必須 Novelty ≥ 75
- 路徑切換：`project_action(action="update", workflow_mode="manuscript|library-wiki", paper_type="...")`
- 🔒 內容：NOVELTY + SELLING POINTS 不可刪改
