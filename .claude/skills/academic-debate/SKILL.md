---
name: academic-debate
description: |
  學術辯論與觀點比較框架。
  LOAD THIS SKILL WHEN: debate、辯論、pro/con、正反方、devil's advocate、挑戰假設、counter-argument、反駁、compare viewpoints、比較觀點、challenge、質疑
  CAPABILITIES: 純指令技能，不需要專屬 MCP tool。利用 LLM 推理能力 + 現有 tools (read_draft, search_local_references) 完成分析。
---

# 學術辯論與觀點比較技能

## 設計意圖

> **為什麼這不是 MCP Tool？**
> 辯論框架、偏誤分析、觀點比較是「結構化思考」，LLM 本身就能做得比 hard-coded 模板更好。
> 這裡提供的是「domain knowledge」讓 LLM 知道如何系統性地構建學術辯論。

---

## 適用情境

| 觸發語 | 操作 |
|--------|------|
| 「幫我辯論 X vs Y」 | → 使用 Debate Framework |
| 「挑戰一下這個觀點」 | → 使用 Devil's Advocate Framework |
| 「比較這幾種方法」 | → 使用 Viewpoint Comparison Framework |
| 「這個 claim 站得住腳嗎」 | → 使用 Devil's Advocate Framework |

---

## 可搭配的 MCP Tools

| 工具 | 用途 |
|------|------|
| `read_draft` | 讀取草稿獲取需要辯論/挑戰的內容 |
| `search_local_references` | 搜尋已存文獻佐證正反方觀點 |
| `list_saved_references` | 列出可用引用 |
| `mcp_cgu_deep_think` | 深度分析弱點 |
| `mcp_cgu_spark_collision` | 碰撞正反觀點產生新洞見 |

---

## Framework 1: Academic Debate (雙方辯論)

**目標**：針對一個研究議題，結構化正反方論點

### 輸出結構

```markdown
# 🔬 Academic Debate: {topic}

**Context:** {研究背景}
**Study Type:** {偵測到的研究類型}

---

## ✅ Position A: {supporting_position}

### Supporting Arguments
（按照證據等級排列，最強的放最前面）

| # | Argument | Evidence Level | Source |
|---|----------|---------------|--------|
| 1 | [具體論點] | [證據等級] | [[citation]] |

## ❌ Position B: {opposing_position}

### Counter-Arguments
（同樣按照證據等級排列）

## ⚖️ Methodological Considerations ({study_type})

根據研究類型列出相關偏誤（見下方偏誤清單）

## 🔄 Synthesis for Discussion Section

### Areas of Agreement
### Key Disagreements
### Clinical Bottom Line
```

---

## Framework 2: Devil's Advocate (魔鬼代言人)

**目標**：系統性挑戰一個研究主張的弱點

### 輸出結構

```markdown
# 😈 Devil's Advocate Analysis

**Claim:** {要挑戰的主張}
**Supporting Evidence:** {現有支持證據}
**Study Type:** {研究類型}

---

## 1. Methodological Challenges ({study_type})
（根據研究類型選擇相關偏誤，見下方偏誤清單）

## 2. Statistical Challenges
- Multiple comparisons / Type I error
- Effect size (clinical significance vs statistical significance)
- Confidence interval width
- Missing data handling (MCAR/MAR/MNAR)
- Power / sample size adequacy

## 3. Generalizability Concerns
- Population: 結果能推廣嗎？
- Setting: 單中心 vs 多中心？
- Timeframe: 短期 → 長期？
- Intervention fidelity: 能被重複嗎？

## 4. Alternative Explanations
- Confounding?
- Reverse causation?
- Temporal trends?
- Hawthorne/placebo effect?

## 5. Likely Reviewer Questions
（基於 Study Type 產出最可能被 reviewer 問的問題）

## 💪 Strengthening Recommendations
1. Address strongest counter-argument in Discussion
2. Add sensitivity/subgroup analyses
3. Acknowledge limitations proactively
4. Cite supportive systematic reviews
5. Frame clinical implications conservatively
```

---

## Framework 3: Viewpoint Comparison (觀點比較)

**目標**：系統性比較多個理論/方法觀點

### 輸出結構

```markdown
# 🔀 Viewpoint Comparison: {topic}

## Summary Comparison

| Criterion | Viewpoint A | Viewpoint B | ... |
|-----------|-------------|-------------|-----|
| Evidence Base | [analysis] | [analysis] | |
| Theoretical Foundation | ... | ... | |
| Clinical Applicability | ... | ... | |
| Patient Safety | ... | ... | |
| Cost-Effectiveness | ... | ... | |
| Current Guidelines | ... | ... | |
| Limitations | ... | ... | |

## Viewpoint 1: {name}
- Core Premise
- Key Proponents
- Best Evidence
- Strengths
- Weaknesses

(repeat for each viewpoint)

## 🔗 Implications for Your Research
### Points of Convergence
### Points of Divergence
### Recommended Position
```

### 預設比較維度

如果用戶沒有指定比較維度，使用以下預設：
1. Evidence Base（證據基礎）
2. Theoretical Foundation（理論基礎）
3. Clinical Applicability（臨床適用性）
4. Patient Safety（病人安全）
5. Cost-Effectiveness（成本效益）
6. Current Guidelines（目前指引）
7. Limitations（限制）

---

## 🧠 Domain Knowledge: Evidence Hierarchy

Agent 在構建辯論時，按此等級排列證據：

1. **Systematic Review / Meta-Analysis** — 最高等級
2. **Randomized Controlled Trial (RCT)**
3. **Cohort Study (Prospective)**
4. **Case-Control Study**
5. **Cross-Sectional Study**
6. **Case Series / Case Report**
7. **Expert Opinion / Editorial** — 最低等級

---

## 🧠 Domain Knowledge: Study-Type-Specific Biases

### RCT
- Selection bias (randomization failure)
- Performance bias (blinding issues)
- Detection bias (outcome assessment)
- Attrition bias (dropouts)
- Reporting bias (selective outcome reporting)

### Cohort Study
- Selection bias (non-random sampling)
- Confounding (unmeasured variables)
- Information bias (measurement error)
- Loss to follow-up
- Healthy worker effect

### Case-Control Study
- Recall bias
- Selection bias (control selection)
- Confounding
- Misclassification bias
- Temporal ambiguity

### Cross-Sectional Study
- Cannot establish temporality
- Prevalence-incidence bias
- Non-response bias
- Information bias
- Confounding

### Retrospective Study
- Information bias (records quality)
- Selection bias (survivorship)
- Confounding
- Missing data
- Temporal bias

---

## 🔍 Study Type Detection

根據文字內容自動偵測研究類型，用以下關鍵字：

| 關鍵字 | 研究類型 |
|--------|----------|
| randomized, RCT, blinded, placebo | RCT |
| cohort, prospective, follow-up, incidence | Cohort |
| case-control, odds ratio, exposure | Case-Control |
| cross-sectional, prevalence, survey | Cross-Sectional |
| retrospective, chart review, medical records | Retrospective |

---

## ⚠️ 使用原則

1. **永遠基於證據** — 不要空泛發言，引用已存文獻
2. **平衡呈現** — 即使一方明顯較強，也要公平呈現另一方
3. **標明研究類型** — 偏誤分析必須對應正確的研究類型
4. **最後給臨床建議** — 辯論的目的是為了 Discussion section 的寫作

---

## 相關技能

- `concept-development` — 分析 concept 弱點
- `draft-writing` — 將辯論結果寫入 Discussion
- `literature-review` — 找更多支持/反對的文獻
