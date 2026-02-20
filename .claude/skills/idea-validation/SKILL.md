---
name: idea-validation
description: |
  研究假說驗證與可行性評估框架。
  LOAD THIS SKILL WHEN: hypothesis、假說、PICO、feasibility、可行性、testable、可驗證、研究計畫評估、check feasibility
  CAPABILITIES: 純指令技能，不需要專屬 MCP tool。利用 LLM 推理能力 + 現有 tools (list_saved_references, search_local_references) 完成分析。
---

# 研究假說驗證與可行性評估技能

純指令技能。LLM 醫學知識 + `compare_with_literature`, `list_saved_references`, `search_local_references`, `validate_concept`。

觸發：hypothesis、假說、PICO、feasibility、可行性、testable、研究計畫評估

---

## Framework 1: Hypothesis Validation

### Step 1: PICO 分析
| Component | 偵測重點 |
|-----------|----------|
| **P**opulation | patients, subjects, ICU, surgical... |
| **I**ntervention | treatment, therapy, drug, procedure... |
| **C**omparison | versus, vs, placebo, standard, control... |
| **O**utcome | mortality, survival, recovery, score, rate... |

### Step 2: Testability
1. **Directional** — higher/lower/better/worse/reduce? ✅ vs 只有描述性 ❌
2. **Comparison** — significantly/compared/than? ✅ vs 缺基準 ❌
3. **Type** — Null (no difference) vs Alternative (有方向)
4. **Specificity** — <10 words 太模糊, 10-50 適當, >50 過複雜

### Step 3: Study Type Recommendation
| 假說特徵 | 建議設計 |
|----------|----------|
| effect/efficacy/treatment | RCT or Cohort |
| risk factor/association | Cohort or Case-Control |
| prevalence/frequency | Cross-Sectional |

---

## Framework 2: Feasibility Assessment

### Sample Size Quick Check
| 類型 | 注意 |
|------|------|
| N ≤ 10 | Case report/series |
| N < 30 RCT | Pilot or crossover |
| N ≥ 100 | 大多設計合理 |

### Timeline by Study Type
| 類型 | IRB | 主要工作 | 分析寫作 |
|------|-----|----------|----------|
| RCT | 2 mo | 招募+收案 ÷3 | ÷4 |
| Retrospective | 1 mo | 資料萃取 2 mo | ÷2 |
| SR | 1 mo (protocol) | 搜尋+篩選 ÷3 | ÷3 |

### Feasibility Checklist (17 items, 5 categories)

| Category | Critical Items | High Items |
|----------|---------------|------------|
| Data & Sample | 資料可及、樣本可達 | 納排標準 |
| Ethics | IRB plan、informed consent | privacy |
| Resources | — | funding, timeline, team, equipment |
| Methodology | primary outcome | stat plan, validated tools, confounders |
| Publication | — | target journal, reporting guideline, novelty |

**All Critical items must be ✅ before proceeding.**

---

## 使用原則
1. PICO 分析用語意理解，非關鍵字匹配
2. 可行性評估寧可保守
3. 文獻比較用 `compare_with_literature` MCP tool
