---
name: idea-validation
description: |
  研究假說驗證與可行性評估框架。
  LOAD THIS SKILL WHEN: hypothesis、假說、PICO、feasibility、可行性、testable、可驗證、研究計畫評估、check feasibility
  CAPABILITIES: 純指令技能，不需要專屬 MCP tool。利用 LLM 推理能力 + 現有 tools (list_saved_references, search_local_references) 完成分析。
---

# 研究假說驗證與可行性評估技能

## 設計意圖

> **為什麼這不是 MCP Tool？**
> PICO 分析、假說評估、可行性 checklist 是「結構化判斷」，LLM 本身的醫學知識比 regex 更準確。
> Hard-coded regex 做 PICO 分析容易漏判，而 LLM 理解語意能做得更好。

---

## 適用情境

| 觸發語 | 操作 |
|--------|------|
| 「我的假說是否 well-formed？」 | → 使用 Hypothesis Validation Framework |
| 「這個研究可行嗎？」 | → 使用 Feasibility Assessment Framework |
| 「和現有文獻比較有什麼差異」 | → 使用 `compare_with_literature` MCP tool（合法 tool，需要存取 ref DB） |

---

## 可搭配的 MCP Tools

| 工具 | 用途 |
|------|------|
| `compare_with_literature` | 和已存文獻比較研究 idea 的重疊與差距 |
| `list_saved_references` | 檢視已收集文獻 |
| `search_local_references` | 搜尋特定主題的已存文獻 |
| `validate_concept` | 驗證 concept.md 的完整性和新穎性 |
| `validate_for_section` | 針對特定 section 驗證概念 |

---

## Framework 1: Hypothesis Validation (假說驗證)

**目標**：評估研究假說是否結構完整、可驗證

### Step 1: PICO Component Analysis

分析假說是否包含四個核心成分：

| Component | 說明 | 偵測重點 |
|-----------|------|----------|
| **P**opulation | 研究對象 | patients, subjects, adults, children, elderly, ICU, surgical, etc. |
| **I**ntervention | 介入措施 | treatment, therapy, intervention, drug, procedure, administration, etc. |
| **C**omparison | 對照組 | compared, versus, vs, placebo, standard, conventional, control, etc. |
| **O**utcome | 結果指標 | outcome, mortality, survival, recovery, length of stay, score, rate, etc. |

### Step 2: Testability Assessment

評估四個面向：

1. **Directional Prediction** — 是否有方向性預測？
   - ✅ 包含：higher, lower, better, worse, increase, decrease, reduce, improve, differ
   - ❌ 只有描述性（如 "we will study..."）

2. **Comparison Element** — 是否有明確比較？
   - ✅ 包含：significantly, compared, versus, vs, than, relative
   - ❌ 缺少比較基準

3. **Hypothesis Type** — 是 null 還是 alternative？
   - Null: no difference, no association, not associated
   - Alternative: 包含方向性預測（研究常用）

4. **Specificity** — 字數評估
   - < 10 words：太模糊，需要擴充
   - 10-50 words：適當
   - \> 50 words：過度複雜，考慮拆分

### Step 3: Study Type Recommendation

根據假說內容建議研究設計：

| 假說特徵 | 建議設計 |
|----------|----------|
| effect of, efficacy, treatment, intervention | RCT (if feasible) or Cohort |
| risk factor, association, associated with | Cohort or Case-Control |
| prevalence, proportion, frequency | Cross-Sectional |
| 其他 | Cohort (default) |

### 輸出結構

```markdown
# 🔬 Hypothesis Validation

**Hypothesis:** {text}

## 1. PICO Component Analysis
| Component | Status | Detected Elements |
|-----------|--------|-------------------|
| Population | ✅/❌ | {elements} |
| Intervention | ✅/❌ | {elements} |
| Comparison | ✅/❌ | {elements} |
| Outcome | ✅/❌ | {elements} |

**PICO Score:** X/4

## 2. Testability Assessment
- ✅/❌ Directional prediction
- ✅/❌ Comparison element
- ℹ️ Hypothesis type (null/alternative)
- ✅/⚠️ Specificity ({word_count} words)

## 3. Study Type Assessment
**Recommended:** {type}

## 4. Overall Assessment
✅ Well-formed / ⚠️ Partially formed / ❌ Needs revision

**Suggestions:**
- {specific improvements}
```

---

## Framework 2: Feasibility Assessment (可行性評估)

**目標**：系統性評估研究計畫的可執行性

### Sample Size Quick Assessment

| 研究類型 | 常見問題 |
|----------|----------|
| Case Report (N ≤ 10) | N > 10 可能是 case series |
| RCT (N < 30) | 考慮 pilot study 或 crossover design |
| N ≥ 100 | 大多數設計都合理 |
| 其他 | 需要 power analysis 支持 |

### Timeline Estimation by Study Type

#### RCT / Original Research
| Phase | Estimated Months |
|-------|------------------|
| Ethics / IRB approval | 2 |
| Recruitment & enrollment | timeline ÷ 3 (min 3) |
| Data collection | timeline ÷ 3 (min 3) |
| Analysis & writing | timeline ÷ 4 (min 2) |

#### Retrospective Study
| Phase | Estimated Months |
|-------|------------------|
| Ethics / IRB approval | 1 |
| Data extraction | 2 |
| Analysis & writing | timeline ÷ 2 (min 2) |

#### Systematic Review
| Phase | Estimated Months |
|-------|------------------|
| Protocol & registration | 1 |
| Systematic search | 2 |
| Screening & extraction | timeline ÷ 3 (min 2) |
| Analysis & writing | timeline ÷ 3 (min 2) |

### 🧠 Feasibility Checklist (17 items, 5 categories)

#### Data & Sample
| Item | Importance |
|------|------------|
| Data source identified and accessible | Critical |
| Sample size achievable in timeframe | Critical |
| Inclusion/exclusion criteria defined | High |

#### Ethics & Compliance
| Item | Importance |
|------|------------|
| IRB/Ethics approval plan | Critical |
| Informed consent strategy | Critical |
| Data privacy compliance (GDPR/HIPAA) | High |

#### Resources & Timeline
| Item | Importance |
|------|------------|
| Funding secured or not required | High |
| Research team and roles defined | Medium |
| Timeline realistic for study design | High |
| Equipment and software available | Medium |

#### Methodology
| Item | Importance |
|------|------------|
| Statistical analysis plan drafted | High |
| Primary outcome clearly defined | Critical |
| Validated measurement tools identified | High |
| Confounders identified and plan to address | High |

#### Publication
| Item | Importance |
|------|------------|
| Target journal identified | Medium |
| Reporting guideline identified (CONSORT/STROBE/etc) | Medium |
| Novelty vs existing literature confirmed | High |

### 輸出結構

```markdown
# 📋 Feasibility Assessment

**Research Plan:** {description}
**Study Type:** {type}
**Sample Size:** {N}
**Timeline:** {months} months

---

## Sample Size Assessment
{assessment based on study type}

## Timeline Assessment
| Phase | Estimated Months |
|-------|------------------|
{phases based on study type}

**Total minimum:** {sum} months
{⚠️ if timeline < total_min}

## Feasibility Checklist

### Data & Sample
| Item | Importance | Status |
|------|------------|--------|
{items with ☐ Not assessed}

(repeat for all 5 categories)

---
💡 Mark each as ✅ Met, ⚠️ Needs Work, or ❌ Blocker.
All 'Critical' items must be ✅ before proceeding.
```

---

## ⚠️ 使用原則

1. **PICO 分析用語意理解** — 不要只做關鍵字匹配，理解上下文
2. **可行性評估要保守** — 寧可高估時間，不要低估
3. **和文獻比較用 MCP tool** — `compare_with_literature` 需要存取 reference DB，這是合法 tool
4. **所有 Critical 項目必須通過** — 在開始 protocol 前

---

## 相關技能

- `concept-development` — 發展概念（假說驗證的前一步）
- `concept-validation` — 驗證概念新穎性
- `literature-review` — 找相關文獻
- `manuscript-review` — 撰寫後的審查
