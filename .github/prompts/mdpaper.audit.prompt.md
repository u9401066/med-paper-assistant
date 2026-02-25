---
description: "audit - 獨立審計 + 自主審稿（Phase 6+7）"
---

# 獨立審計流程

**核心 Skill**：`.claude/skills/auto-paper/SKILL.md`（Phase 6 + Phase 7）

## 適用情境

- 草稿已完成（至少 Introduction + Methods + Results + Discussion）
- 想跳過 Phase 0-5 直接做品質審計
- 想單獨跑 Phase 7 Review Loop 檢查已有稿件

## 前置條件

1. 專案已存在（`get_current_project()`）
2. `manuscript-plan.yaml` 已存在（Hook B7/C7 需要）
3. 草稿檔案已在 `projects/{slug}/drafts/` 下

## 執行流程

### Step 1: 環境確認

```
get_current_project() → 確認專案
list_drafts() → 確認草稿檔案
```

### Step 2: Phase 6 — CROSS-SECTION CASCADING AUDIT

執行 Hook C1-C8（含 C7 數量與交叉引用合規），遵循 SKILL.md Phase 6 完整流程。

- C1-C8 全稿掃描
- Cascading Fix 最多 3 rounds
- C8 時間一致性 Pass
- 產出 quality-scorecard.md

**Gate**: 0 CRITICAL issues

### Step 3: Phase 7 — AUTONOMOUS REVIEW

執行結構化 Review Loop（最多 3 rounds），產出：

- `review-report-{round}.md`（YAML front matter）
- `author-response-{round}.md`（Completeness Check）

**Gate**: quality ≥ threshold

### Step 4: 產出報告

- `.audit/quality-scorecard.md`（量化分數）
- `.audit/review-report-*.md` + `.audit/author-response-*.md`
- 更新 `.memory/progress.md`

## 注意

- 此流程不修改 manuscript-plan.yaml
- 若審計發現需大幅重寫，建議回到 `/mdpaper.write-paper` Phase 5
