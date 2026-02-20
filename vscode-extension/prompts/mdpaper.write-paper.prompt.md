---
description: "write-paper - 完整論文撰寫（全自動 + 閉環審計）"
---

# 完整論文撰寫流程

**核心 Skill**：`.claude/skills/auto-paper/SKILL.md`（9-Phase 閉環系統）

## 執行方式

載入並遵循 `auto-paper/SKILL.md` 的 9-Phase Pipeline。

| Phase      | Skill                    | 外部 MCP                | Gate              |
| ---------- | ------------------------ | ----------------------- | ----------------- |
| 1 專案設置 | project-management       | -                       | 專案 + paper_type |
| 2 文獻搜尋 | literature-review        | pubmed-search, zotero🔸 | ≥10 篇            |
| 3 概念發展 | concept-development      | cgu🔸                   | score ≥ 75        |
| 4 大綱規劃 | draft-writing            | -                       | 🗣️ 用戶確認       |
| 5 章節撰寫 | draft-writing + Hook A/B | drawio🔸, cgu🔸         | 通過              |
| 6 全稿審計 | Hook C                   | -                       | 0 critical        |
| 7 引用同步 | reference-management     | -                       | 0 broken          |
| 8 匯出     | word-export              | -                       | 已匯出            |
| 9 回顧改進 | Hook D                   | -                       | SKILL 更新        |

🔸 = 條件觸發（見 auto-paper SKILL.md Cross-Tool Orchestration Map）

**人工介入**：僅 Phase 4 大綱確認。Concept < 60 兩次仍低、Hook 3 輪仍失敗時暫停。

**中斷恢復**：`sync_workspace_state()` → `.memory/activeContext.md` → 下次 `get_workspace_state()`。
