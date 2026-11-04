---
name: manuscript-review
description: |
  模擬同行審稿與報告指引合規性檢查框架。
  LOAD THIS SKILL WHEN: peer review、同行審查、reviewer、審稿、reporting guidelines、CONSORT、STROBE、PRISMA、CARE、critique、檢查稿件、稿件問題
  CAPABILITIES: 純指令技能，搭配 read_draft MCP tool 讀取草稿內容。LLM 用醫學知識做審查，比 regex 更準確。
---

# 稿件審查與報告指引技能

LLM 語意理解 > regex 關鍵字匹配。資料用 `read_draft` MCP tool，審查邏輯由 LLM + domain knowledge。

觸發：審查草稿、reviewer、CONSORT、STROBE、PRISMA、CARE、投稿前檢查

## 搭配 MCP Tools

| 工具               | 用途                            |
| ------------------ | ------------------------------- |
| `read_draft`       | **必用** — 讀草稿               |
| `list_drafts`      | 列出可審查的草稿                |
| `count_words`      | 字數統計                        |
| `check_formatting` | 期刊格式量化檢查 + 跨文件一致性 |

---

## Framework 1: Peer Review

用 `read_draft` 取得內容 → 按 4 面向審查 → 輸出結構化報告

### 審查面向

**1. Structure**：必要章節齊全、Abstract 結構化、邏輯順序（Major if 缺少/亂序）

**2. Methods**：
| 項目 | Major/Minor |
|------|-------------|
| Ethics/IRB statement | Major |
| Statistical methods | Major |
| Sample size justification | Minor |
| Primary outcome definition | Minor |
| Inclusion/exclusion criteria | Minor |

**3. Statistics**：
| 項目 | Major/Minor |
|------|-------------|
| Confidence intervals | Major |
| P-value reporting (精確值) | Minor |
| Multiple comparisons correction | Minor |
| Effect size | Minor |

**4. Writing**：
| 項目 | Major/Minor |
|------|-------------|
| Limitations section | Major |
| Causal language in observational | Major |
| Word count / Reference density | Minor |

### 判定

Major ≥3 → 🔴 Major revision required | 1-2 → 🟡 Major revision | 0 → ✅ Minor/Accept

---

## Framework 2: Reporting Guideline Compliance

`read_draft` → 自動偵測/指定 guideline → 逐項檢查 → 合規報告

### Auto-Detection

| 草稿特徵                            | 指引    |
| ----------------------------------- | ------- |
| randomized, RCT, blinded, placebo   | CONSORT |
| systematic review, meta-analysis    | PRISMA  |
| case report, case presentation      | CARE    |
| observational, cohort, case-control | STROBE  |

### CONSORT (RCT, 21 items)

Title(1), Abstract(2), Intro(3-4: background, objectives), Methods(5-13: design, eligibility, interventions, outcomes, sample size, randomization, allocation concealment, blinding, statistics), Results(14-19: flow, recruitment, baseline, N analysed, outcomes+CI, harms), Discussion(20: interpretation+limitations), Other(21: registration)

### STROBE (Observational, 16 items)

Title(1), Intro(2-3), Methods(4-11: design, setting, participants, variables, measurement, bias, sample size, statistics), Results(12-14: participants, descriptive, outcome), Discussion(15: interpretation), Other(16: funding)

### PRISMA (SR, 17 items)

Title(1), Abstract(2), Intro(3), Methods(4-11: protocol, eligibility, sources, strategy, selection, extraction, RoB, synthesis), Results(12-15: flow, characteristics, results, heterogeneity), Discussion(16), Other(17: registration)

### CARE (Case Report, 13 items)

Title(1), Abstract(2), Intro(3), Patient(4-7: demographics, complaints, history, exam), Clinical(8-10: diagnosis, intervention, follow-up), Discussion(11-12: strengths/limits, rationale), Patient(13: consent)

### 判定

≥80% → 🟢 Good | 60-80% → 🟡 Needs attention | <60% → 🔴 Significant gaps

---

## 使用原則

1. 語意理解，非關鍵字匹配（「倫理委員會核准」= ethics approval）
2. Major = 可能被 reject，Minor = 改善建議
3. 給具體修復建議
4. 多檔案支持（Introduction、Methods 可能在不同檔案）
