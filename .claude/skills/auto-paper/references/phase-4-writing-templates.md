# Phase 4 advisory: SUB-SECTION WRITING TEMPLATES

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: about to write or review a manuscript section, placing figures/tables, or recording `citation_decisions.json`.
> 相關：[phase-5-section-writing.md](phase-5-section-writing.md)、[hooks-c-post-manuscript.md](hooks-c-post-manuscript.md)

---

### Phase 4 advisory task: SUB-SECTION WRITING TEMPLATES（段落級寫作指引）

**目的**：補充 Phase 4 `manuscript-plan.yaml` 的段落級先驗知識。Agent 在 Phase 5 撰寫每段時**必須對照**以下模板，確保結構完整、邏輯連貫。

#### Introduction 段落模板（Funnel Structure）

| 段落 | 功能            | 內容要求                                 | 引用要求                 | Hook 檢查                |
| ---- | --------------- | ---------------------------------------- | ------------------------ | ------------------------ |
| P1   | Broad Context   | 研究領域的重要性、流行病學資料、臨床意義 | ≥2 引用（流行病學/指引） | B12（context markers）   |
| P2   | Evidence Review | 既有文獻的主要發現、方法、結論           | ≥3 引用（核心文獻）      | A2（citation density）   |
| P3   | Knowledge Gap   | 現有文獻的不足、矛盾、未解問題           | ≥1 引用（指出 gap 來源） | B12（gap markers）       |
| P4   | Study Objective | 本研究的目的、假說（若適用）             | 0-1 引用                 | B12（objective markers） |

**Anti-patterns**（自動 FLAG）：

- P1 直接跳到研究目的（缺 context/gap）
- P2 只列名字不描述內容（name-dropping）
- P3 缺乏具體 gap statement（如 "however, ... remains unclear"）
- P4 超過 2 句（過度冗長的目的聲明）

#### Methods 段落模板（Reproducibility Structure）

| 段落 | 功能                  | 內容要求                          | 引用要求                    | Hook 檢查                  |
| ---- | --------------------- | --------------------------------- | --------------------------- | -------------------------- |
| M1   | Study Design          | 研究類型、期間、機構、IRB 核准    | ≥1（設計依據）              | B14（ethical statements）  |
| M2   | Participants          | 納入/排除標準、樣本大小計算       | ≥1（criteria 依據）         | B9（past tense）           |
| M3   | Intervention/Exposure | 介入措施的詳細描述、對照組定義    | ≥1（intervention protocol） | B5（方法學 checklist）     |
| M4   | Outcome Measures      | 主要/次要結果指標、測量方式、定義 | ≥2（validated instruments） | C11（Methods 引用）        |
| M5   | Statistical Analysis  | 統計方法、軟體版本、顯著水準      | ≥1（統計方法引用）          | B8（data-claim alignment） |

**Anti-patterns**：

- M1 缺 IRB/倫理核准 → B14 CRITICAL
- M2 無樣本大小依據 → WARNING
- M5 統計方法與 Results 不一致 → B8 CRITICAL

#### Results 段落模板（Data-First Structure）

| 段落 | 功能                      | 內容要求                        | 引用要求        | Hook 檢查                    |
| ---- | ------------------------- | ------------------------------- | --------------- | ---------------------------- |
| R1   | Study Flow / Demographics | 篩選流程、基本特徵（→ Table 1） | 0（純數據）     | C13（圖表引用）              |
| R2   | Primary Outcome           | 主要結果、統計檢驗、效果量 + CI | 0（純數據）     | B11（客觀性）、B16（效果量） |
| R3   | Secondary Outcomes        | 次要結果、亞群分析              | 0-1（方法引用） | B8（統計對齊）               |
| R4   | Subgroup / Sensitivity    | 子群分析、敏感度分析（若適用）  | 0（純數據）     | C13（圖表引用）              |

**Anti-patterns**：

- R1-R4 含有 interpretive language（"suggesting", "indicating"）→ B11 WARNING
- Results 無任何圖表引用 → C13 WARNING
- 效果量缺 CI → B16 WARNING

#### Discussion 段落模板（Interpretation Structure）

| 段落  | 功能                      | 內容要求                            | 引用要求       | Hook 檢查                   |
| ----- | ------------------------- | ----------------------------------- | -------------- | --------------------------- |
| D1    | Main Findings             | 總結主要發現（不重複 Results 數字） | 0-1            | B13（main finding markers） |
| D2-D3 | Literature Comparison     | 與既有文獻的一致/矛盾之處           | ≥3（比較文獻） | C11（Discussion 引用分布）  |
| D4    | Mechanisms / Implications | 可能機制解釋、臨床/實務意義         | ≥1（機制文獻） | B13（implications markers） |
| D5    | Limitations               | 研究限制（設計、偏差、外推性）      | 0-2            | B13（CRITICAL if missing）  |
| D6    | Conclusion / Future       | 總結 + 未來研究方向                 | 0-1            | B15（hedging 適當用量）     |

**Anti-patterns**：

- D1 重複 Results 的統計數字 → WARNING
- D2-D3 無引用（未與文獻比較）→ C11 CRITICAL
- D5 缺席 → B13 CRITICAL
- 全文 hedging 過度（> 6/1000 words）→ B15 CRITICAL

#### Abstract 段落模板（Structured Abstract）

| 段落 | 功能        | 字數目標     | 內容要求                                    |
| ---- | ----------- | ------------ | ------------------------------------------- |
| A1   | Background  | 40-60 words  | 背景 + gap（1-2 句）                        |
| A2   | Methods     | 60-80 words  | 設計、樣本、主要測量                        |
| A3   | Results     | 80-120 words | 主要結果 + 統計數字                         |
| A4   | Conclusions | 30-50 words  | 臨床意義（1-2 句，避免 overgeneralization） |

**注意**：Abstract 字數受 journal-profile.yaml 嚴格限制。

#### 圖表插入規範（與 C13 Hook 整合）

| 規則         | 說明                                          | Hook |
| ------------ | --------------------------------------------- | ---- |
| 順序引用     | Figure 1 必須在 Figure 2 之前首次出現         | C13  |
| Caption 完整 | ≥10 words，含 axes/variables/abbreviations    | C13  |
| Results 必有 | Results 有數據 claim → 必須引用至少 1 個圖/表 | C13  |
| Orphan 檢測  | Manifest 有但文中未引用 → WARNING             | C7d  |
| Phantom 檢測 | 文中引用但 Manifest 無 → CRITICAL             | C7d  |
| 數量限制     | 不超過 journal-profile 設定的 max             | C7a  |

#### Citation Decision Record 規範（與 C12 Hook 整合）

每篇引用的文獻必須在 `citation_decisions.json` 中留下決策紀錄：

```json
{
  "smith2023_12345678": {
    "justification": "Largest RCT comparing X vs Y in same population, supports our primary outcome finding",
    "cited_sections": ["Introduction", "Discussion"],
    "relevance_score": 9,
    "decision_date": "2025-01-15",
    "decided_by": "agent"
  },
  "jones2022_87654321": {
    "justification": "Validated the measurement instrument used in our study (M4 outcome measures)",
    "cited_sections": ["Methods"],
    "relevance_score": 8,
    "decision_date": "2025-01-15",
    "decided_by": "agent"
  }
}
```

**工作流程**：

1. Phase 2 → `save_reference_analysis()` 建立 `usage_sections`
2. Phase 5 → 每次 `insert_citation()` 時，同步更新 `citation_decisions.json`
3. Phase 6 → C12 Hook 驗證：每篇引用都有 justification + cited_sections 與實際吻合
