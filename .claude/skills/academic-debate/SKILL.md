---
name: academic-debate
description: |
  學術辯論與觀點比較框架。
  LOAD THIS SKILL WHEN: debate、辯論、pro/con、正反方、devil's advocate、挑戰假設、counter-argument、反駁、compare viewpoints、比較觀點、challenge、質疑
  CAPABILITIES: 純指令技能，不需要專屬 MCP tool。利用 LLM 推理能力 + 現有 tools (read_draft, search_local_references) 完成分析。
---

# 學術辯論與觀點比較技能

純指令技能。LLM 結構化思考 + `read_draft`, `search_local_references`, `mcp_cgu_deep_think`, `mcp_cgu_spark_collision`。

觸發：辯論、pro/con、devil's advocate、挑戰假設、compare viewpoints

---

## Framework 1: Academic Debate（雙方辯論）

針對研究議題結構化正反方論點。按**證據等級**排列：
SR/Meta > RCT > Cohort > Case-Control > Cross-Sectional > Case Series > Expert Opinion

輸出：Position A (supporting) → Position B (opposing) → Methodological Considerations (偏誤) → Synthesis (agreement / disagreement / clinical bottom line)

---

## Framework 2: Devil's Advocate（魔鬼代言人）

系統性挑戰一個研究主張。5 面向：

1. **Methodological** — 研究類型對應偏誤（見下方）
2. **Statistical** — multiple comparisons, effect size, CI width, missing data, power
3. **Generalizability** — population, setting, timeframe, intervention fidelity
4. **Alternative Explanations** — confounding, reverse causation, temporal trends, Hawthorne
5. **Likely Reviewer Questions** — 基於 study type

產出：Strengthening Recommendations（address counter-arguments, add sensitivity analysis, cite SR, frame conservatively）

---

## Framework 3: Viewpoint Comparison（觀點比較）

多個理論/方法系統性比較。預設比較維度：
Evidence Base, Theoretical Foundation, Clinical Applicability, Patient Safety, Cost-Effectiveness, Current Guidelines, Limitations

---

## Study-Type-Specific Biases

| Type            | Key Biases                                                                       |
| --------------- | -------------------------------------------------------------------------------- |
| RCT             | Selection, performance, detection, attrition, reporting                          |
| Cohort          | Selection, confounding, information, loss to follow-up, healthy worker           |
| Case-Control    | Recall, selection (controls), confounding, misclassification, temporal ambiguity |
| Cross-Sectional | No temporality, prevalence-incidence, non-response, information                  |
| Retrospective   | Information (records), survivorship, confounding, missing data                   |

Auto-detect：randomized/RCT=RCT, cohort/prospective=Cohort, case-control/odds=Case-Control, cross-sectional/prevalence=Cross-Sectional, retrospective/chart=Retrospective

---

## 使用原則

1. 基於證據，引用已存文獻
2. 平衡呈現雙方
3. 偏誤分析對應正確研究類型
4. 最終給臨床建議（為 Discussion 服務）
