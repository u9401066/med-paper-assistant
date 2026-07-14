---
description: "write-paper - 完整論文撰寫（全自動 + 閉環審計）"
---

# 完整論文撰寫流程

**核心 Skill**：`.claude/skills/auto-paper/SKILL.md`（13 main gate checkpoints 閉環系統，Phase 0-11 + 6.5；Phase 2.1 為全文素材 sub-gate）

## 執行方式

載入並遵循 `auto-paper/SKILL.md` 的 13 main gate checkpoint Pipeline，並在 Phase 2 後執行 Phase 2.1 全文素材 sub-gate。

| Phase        | Skill                         | 外部 MCP                | Gate                          |
| ------------ | ----------------------------- | ----------------------- | ----------------------------- |
| 0 前置規劃   | —                             | -                       | journal-profile.yaml 用戶確認 |
| 1 專案設置   | project-management            | -                       | 專案 + paper_type             |
| 2 文獻搜尋   | literature-review             | pubmed-search, zotero🔸 | paper-type-aware 最低文獻數   |
| 2.1 全文素材 | literature-review             | asset-aware🔸           | 可追溯 source-material        |
| 3 概念發展   | concept-development           | cgu🔸                   | score ≥ 75                    |
| 4 大綱規劃   | draft-writing                 | -                       | manuscript-plan.yaml 確認     |
| 5 章節撰寫   | draft-writing + Hook A/B/B7   | drawio🔸, cgu🔸         | section approvals             |
| 6 全稿審計   | Hook C（C7=數量+交叉引用）    | -                       | 0 critical                    |
| 6.5 演化閘門 | baseline snapshot             | -                       | evolution-log baseline        |
| 7 自主審稿   | Review→Response loop (×3)     | -                       | quality ≥ threshold           |
| 8 引用同步   | reference-management          | -                       | 0 broken                      |
| 9 匯出       | word-export                   | -                       | docx + pdf                    |
| 10 回顧改進  | Hook D（含 D7 Reviewer 演化） | -                       | meta-learning audit           |
| 11 最終交付  | word-export + audit           | -                       | export smoke + provenance     |

🔸 = 條件觸發（見 auto-paper SKILL.md Cross-Tool Orchestration Map）

**人工介入**：僅 Phase 4 大綱確認。Concept < 60 兩次仍低、Hook 3 輪仍失敗時暫停。

**中斷恢復**：`workspace_state_action(action="sync")` → `.memory/activeContext.md` → 下次 `workspace_state_action(action="get")`。
