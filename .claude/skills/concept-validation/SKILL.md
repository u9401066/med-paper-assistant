---
name: concept-validation
description: |
  概念驗證：確保 concept.md 達到可寫作標準。
  LOAD THIS SKILL WHEN: 驗證、validate、可以開始寫了嗎、novelty 夠嗎、check concept
  CAPABILITIES: validate_concept, validate_concept_quick, validate_for_section
---

# Concept Validation Skill

## 核心規則
1. 寫任何草稿前**必須**通過 `validate_concept()`（除 concept.md 本身）
2. Novelty Score ≥ 75（3 輪皆須達標）才算通過
3. 失敗時**犀利回饋 + 給選項**（直接寫？修正？用 CGU？）→ **禁止討好式回饋或自動改 NOVELTY**

---

## 工具

| Tool | 用途 | 何時用 |
|------|------|--------|
| `validate_concept` | 完整 3 輪驗證 + novelty 計分 | 首次驗證、修改 concept 後 |
| `validate_concept_quick` | 結構性快速檢查（不評分） | 草稿階段快速確認 |
| `validate_for_section` | 針對特定 section 驗證 | 寫 Introduction/Methods 前 |

---

## Novelty 評分標準

| 分數 | 意義 | 行動 |
|------|------|------|
| 90-100 | 高度創新，強賣點 | ✅ 直接寫 |
| 75-89 | 足夠創新 | ✅ 可寫，建議微調 |
| 60-74 | 創新不足 | ⚠️ 需修改 concept |
| <60 | 缺乏創新 | ❌ 必須重構或用 CGU |

---

## 各 Paper Type 驗證重點

| Paper Type | 必要元素 | 驗證重點 |
|------------|----------|----------|
| original-research | Hypothesis, NOVELTY, Methods, SELLING POINTS | 假說可測、方法可行 |
| case-report | Case presentation, NOVELTY, Learning points | 罕見性或新見解 |
| review-article | Scope, NOVELTY, Framework | 新觀點或新整合 |
| meta-analysis | PICO, Search strategy, NOVELTY | 差異化分析角度 |
| technical-note | Innovation, NOVELTY, Clinical impact | 技術新穎性 |
| letter-to-editor | Key argument, NOVELTY | 觀點獨特性 |
| brief-communication | Key finding, NOVELTY | 發現重要性 |

---

## concept.md 必要結構

```
# Research Concept
## Background（為什麼重要）
## 🔒 NOVELTY STATEMENT（創新點，不可刪弱）
## Research Question / Hypothesis
## Methods Overview
## 🔒 KEY SELLING POINTS（賣點，Discussion 必強調）
## Target Journal（選填）
```

### 🔒 保護內容規則
- `🔒 NOVELTY STATEMENT`：不可弱化或刪除，全稿須體現
- `🔒 KEY SELLING POINTS`：Discussion 必須強調所有賣點
- 違反 → Hook P5 阻止 commit

---

## 驗證工作流

1. 確認 `concept.md` 存在：`read_draft("concept.md")`
2. 結構檢查：所有必要 section 存在
3. 執行驗證：`validate_concept()`（3 輪）
4. 結果處理：
   - ≥75 全部通過 → 通知可開始寫作
   - 任一輪 <75 → 報告弱點 + 提供三選項
   - 缺必要 section → 報告缺失

### 失敗處理選項
| 選項 | 說明 |
|------|------|
| 直接寫 | 接受風險，跳過（需用戶明確同意） |
| 修正 concept | 根據回饋修改 `concept.md` 後重新驗證 |
| 用 CGU 強化 | `mcp_cgu_deep_think`（找弱點）→ `spark_collision`（碰撞論點）→ 修改後重新驗證 |

---

## 與其他 Skill 整合

| 流程 | 前置 Skill | 後續 Skill |
|------|-----------|-----------|
| concept → validation → draft | concept-development | draft-writing |
| auto-paper Phase 4 | concept-development (Phase 3) | draft-writing (Phase 5) |
| Hook B1 (post-section) | — | 比對 concept vs draft |
| Hook P3 (pre-commit) | — | 確認 NOVELTY/SELLING POINTS |
