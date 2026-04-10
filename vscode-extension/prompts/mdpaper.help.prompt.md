---
description: "❓ mdpaper.help - 指令與工作流程參考"
---

# 指令參考

## 可用指令

| 指令                | 用途          |
| ------------------- | ------------- |
| `/mdpaper.project`  | 建立/切換專案 |
| `/mdpaper.search`   | 文獻搜尋      |
| `/mdpaper.strategy` | 搜尋策略      |
| `/mdpaper.concept`  | 發展概念      |
| `/mdpaper.draft`    | 撰寫草稿      |
| `/mdpaper.analysis` | 資料分析      |
| `/mdpaper.clarify`  | 潤稿          |
| `/mdpaper.format`   | 匯出 Word     |

## 建議順序

project → search → concept → draft → analysis → clarify → format

## MCP 工具集

| Server        | 用途                                 |
| ------------- | ------------------------------------ |
| mdpaper       | 專案/草稿/引用/分析/審查/匯出（88 tools + 3 prompts + 3 resources） |
| pubmed-search | 文獻搜尋/全文/引用分析               |
| cgu           | 創意發想（Novelty 不足時）           |
| zotero-keeper | Zotero 整合（選用）                  |

## 核心規則

- 儲存文獻：`save_reference_mcp(pmid)` 優先
- 草稿前：`validate_concept()` 必須 Novelty ≥ 75
- 🔒 內容：NOVELTY + SELLING POINTS 不可刪改
