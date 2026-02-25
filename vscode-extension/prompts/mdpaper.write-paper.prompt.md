---
description: "write-paper - 完整論文撰寫（全自動 + 閉環審計）"
---

# 完整論文撰寫流程

**核心 Skill**：`.claude/skills/auto-paper/SKILL.md`（11-Phase 閉環系統，Phase 0-10）

## 執行方式

載入並遵循 `auto-paper/SKILL.md` 的 11-Phase Pipeline。

| Phase       | Skill                         | 外部 MCP                | Gate                          |
| ----------- | ----------------------------- | ----------------------- | ----------------------------- |
| 0 前置規劃  | —                             | -                       | journal-profile.yaml 用戶確認 |
| 1 專案設置  | project-management            | -                       | 專案 + paper_type             |
| 2 文獻搜尋  | literature-review             | pubmed-search, zotero🔸 | ≥10 篇                        |
| 3 概念發展  | concept-development           | cgu🔸                   | score ≥ 75                    |
| 4 大綱規劃  | draft-writing                 | -                       | 🗣️ manuscript-plan.yaml 確認  |
| 5 章節撰寫  | draft-writing + Hook A/B/B7   | drawio🔸, cgu🔸         | 通過                          |
| 6 全稿審計  | Hook C（C7=數量+交叉引用）    | -                       | 0 critical                    |
| 7 自主審稿  | Review→Response loop (×3)     | -                       | quality ≥ threshold           |
| 8 引用同步  | reference-management          | -                       | 0 broken                      |
| 9 匯出      | word-export                   | -                       | 已匯出                        |
| 10 回顧改進 | Hook D（含 D7 Reviewer 演化） | -                       | SKILL 更新                    |

🔸 = 條件觸發（見 auto-paper SKILL.md Cross-Tool Orchestration Map）

**人工介入**：僅 Phase 4 大綱確認。Concept < 60 兩次仍低、Hook 3 輪仍失敗時暫停。

**中斷恢復**：`sync_workspace_state()` → `.memory/activeContext.md` → 下次 `get_workspace_state()`。
