# Hook E: EQUATOR Reporting Guidelines Compliance（Phase 7 Stage A 附加）

> auto-paper 的 reference 檔（progressive disclosure）；入口與 hard gate 見 [../SKILL.md](../SKILL.md)。
> **Read this when**: checking reporting-guideline compliance (CONSORT / STROBE / PRISMA / CARE …) during a Phase 7 round or producing `equator-compliance-*.md`.
> 相關：[phase-7-review-loop.md](phase-7-review-loop.md)、[hooks-d-meta-learning.md](hooks-d-meta-learning.md)

---

#### Hook E: EQUATOR Reporting Guidelines Compliance（Phase 7 Stage A 附加）🆕

Phase 7 的每輪 Review 中，額外執行 **EQUATOR 報告指引合規檢查**。這是系統的核心賣點之一：AI 能**逐條、不遺漏**地執行人類 reviewer 經常忽略的 checklist 項目。

**觸發**：Phase 7 每輪 Review 的 Stage A（與 4 角色審查並行）

##### E1: 自動偵測適用指引

```
1. 讀取 journal-profile.yaml → reporting_guidelines.checklist
2. IF checklist 已指定 → 使用指定指引
3. IF checklist 為空 → 依據 paper.type + Methods 內容自動偵測：

   paper.type × 內容特徵 → 適用指引：
   ┌─────────────────────────┬───────────────────────────────────┐
   │ Paper Type / 特徵       │ 主要指引          │ AI 擴展指引   │
   ├─────────────────────────┼───────────────────────────────────┤
   │ RCT                     │ CONSORT 2010      │ CONSORT-AI    │
   │ RCT + AI intervention   │ CONSORT-AI        │ SPIRIT-AI     │
   │ Observational cohort    │ STROBE            │ RECORD        │
   │ Observational + routine │ RECORD            │ STROBE        │
   │ Systematic review       │ PRISMA 2020       │ PRISMA-S      │
   │ Meta-analysis           │ PRISMA 2020       │ MOOSE         │
   │ MA of observational     │ MOOSE             │ PRISMA 2020   │
   │ Diagnostic accuracy     │ STARD 2015        │ STARD-AI      │
   │ Diagnostic + AI         │ STARD-AI          │ CLAIM         │
   │ Prediction model        │ TRIPOD 2015       │ PROBAST       │
   │ Prediction + AI/ML      │ TRIPOD+AI         │ MI-CLAIM      │
   │ AI clinical decision    │ DECIDE-AI         │ TRIPOD+AI     │
   │ AI clinical trial       │ SPIRIT-AI         │ CONSORT-AI    │
   │ Medical imaging AI      │ CLAIM             │ STARD-AI      │
   │ Case report             │ CARE 2013         │ —             │
   │ Qualitative research    │ SRQR / COREQ      │ —             │
   │ Quality improvement     │ SQUIRE 2.0        │ —             │
   │ Economic evaluation     │ CHEERS 2022       │ —             │
   │ Animal research         │ ARRIVE 2.0        │ —             │
   │ Protocol (trial)        │ SPIRIT 2013       │ SPIRIT-AI     │
   │ Protocol (SR)           │ PRISMA-P 2015     │ —             │
   │ Software/Methods paper  │ —                 │ see Note      │
   └─────────────────────────┴───────────────────────────────────┘

   Note: Software/Methods papers 無專屬 EQUATOR 指引，
         但若涉及 AI/ML → 適用 TRIPOD+AI 相關項目（選擇性）
```

##### E2: Checklist 逐條驗證

```
FOR guideline IN detected_guidelines:
  checklist = load_checklist(guideline)  # 內建 checklist 資料庫

  FOR item IN checklist.items:
    # 定位：該項目應出現在哪個 section
    target_section = item.expected_section  # e.g. "Methods", "Results"
    content = draft_action(action="read", filename=target_section)

    # 三級判定
    IF item clearly addressed in content:
      → ✅ REPORTED (記錄: section + paragraph + 摘要)
    ELIF item partially addressed:
      → ⚠️ PARTIAL (記錄: 缺什麼、建議補充)
    ELSE:
      → ❌ NOT REPORTED (記錄: 建議加入的位置和內容)

  # 合規率計算
  compliance_rate = REPORTED / total_applicable_items
  partial_rate = PARTIAL / total_applicable_items

  # 閾值判定（依 item 重要性分級）
  IF any ESSENTIAL item is NOT REPORTED → MAJOR issue
  IF compliance_rate < 80% → WARNING
  IF compliance_rate ≥ 80% AND all ESSENTIAL reported → PASS
```

##### E3: EQUATOR 指引內建資料庫

| 指引             | 全稱                                             | 適用範圍              | 項目數    | 來源                        |
| ---------------- | ------------------------------------------------ | --------------------- | --------- | --------------------------- |
| **CONSORT 2010** | Consolidated Standards of Reporting Trials       | RCT                   | 25 項     | equator-network.org         |
| **CONSORT-AI**   | CONSORT Extension for AI                         | AI 介入的 RCT         | 14 擴展項 | Lancet Digital Health 2020  |
| **STROBE**       | Strengthening Reporting of Observational Studies | 觀察性研究            | 22 項     | equator-network.org         |
| **PRISMA 2020**  | Preferred Reporting Items for SR and MA          | 系統性回顧            | 27 項     | BMJ 2021                    |
| **PRISMA-S**     | PRISMA Search Extension                          | 搜尋策略報告          | 16 項     | Systematic Reviews 2021     |
| **PRISMA-P**     | PRISMA for Protocols                             | SR 計畫書             | 17 項     | BMJ 2015                    |
| **MOOSE**        | Meta-analysis of Observational Studies           | 觀察性研究 MA         | 35 項     | JAMA 2000                   |
| **STARD 2015**   | Standards for Reporting Diagnostic Accuracy      | 診斷準確度            | 30 項     | BMJ 2015                    |
| **STARD-AI**     | STARD for AI Diagnostic                          | AI 診斷研究           | 擴展項    | Nature Medicine 2021        |
| **TRIPOD 2015**  | Transparent Reporting of Prediction Models       | 預測模型              | 22 項     | BMJ 2015                    |
| **TRIPOD+AI**    | TRIPOD for AI/ML Prediction                      | AI/ML 預測模型        | 27+擴展   | BMJ 2024                    |
| **PROBAST**      | Prediction Model Risk of Bias Assessment         | 預測模型偏差          | 20 項     | Annals Int Med 2019         |
| **DECIDE-AI**    | AI Decision Support Early Evaluation             | AI 決策支援           | 17 項     | Nature Medicine 2022        |
| **SPIRIT 2013**  | Standard Protocol Items for Trials               | 試驗計畫書            | 33 項     | equator-network.org         |
| **SPIRIT-AI**    | SPIRIT Extension for AI                          | AI 試驗計畫書         | 15 擴展項 | Nature Medicine 2020        |
| **CLAIM**        | Checklist for AI in Medical Imaging              | 醫學影像 AI           | 42 項     | Radiology 2020              |
| **MI-CLAIM**     | Minimum Information about Clinical AI Modeling   | AI 建模最低資訊       | 15 項     | Nature Medicine 2020        |
| **CARE 2013**    | Case Report Guidelines                           | 病例報告              | 13 項     | equator-network.org         |
| **ARRIVE 2.0**   | Animal Research Reporting                        | 動物研究              | 21 項     | PLOS Biology 2020           |
| **SQUIRE 2.0**   | Standards for Quality Improvement                | 品質改善              | 18 項     | BMJ Quality Safety 2015     |
| **SRQR**         | Standards for Reporting Qualitative Research     | 質性研究              | 21 項     | Academic Medicine 2014      |
| **COREQ**        | Consolidated Criteria for Qualitative Research   | 質性（訪談/焦點團體） | 32 項     | Int J Qual Health Care 2007 |
| **CHEERS 2022**  | Consolidated Health Economic Evaluation          | 衛生經濟評估          | 28 項     | BMJ 2022                    |
| **RECORD**       | Reporting of Studies Using Routine Data          | 常規資料研究          | 13+擴展   | PLOS Medicine 2015          |
| **AGREE II**     | Appraisal of Guidelines Research and Evaluation  | 臨床指引              | 23 項     | CMAJ 2010                   |

##### E4: Compliance Report 產出

每輪 Review 產出 `.audit/equator-compliance-{round}.md`：

```markdown
# EQUATOR Compliance Report — Round {round}

## Detected Guidelines: TRIPOD+AI (primary), MI-CLAIM (secondary)

## Detection Basis: paper.type=prediction-model, Methods mentions "deep learning"

### TRIPOD+AI Compliance: 85% (23/27 items)

| #   | Item                                 | Section      | Status          | Notes            |
| --- | ------------------------------------ | ------------ | --------------- | ---------------- |
| 1   | Title identifies as prediction model | Title        | ✅ REPORTED     |                  |
| 2   | Abstract: structured summary         | Abstract     | ✅ REPORTED     |                  |
| 3a  | Background and objectives            | Introduction | ✅ REPORTED     |                  |
| 4a  | Source of data                       | Methods      | ✅ REPORTED     |                  |
| 4b  | Data collection dates                | Methods      | ⚠️ PARTIAL      | Missing end date |
| ... |                                      |              |                 |                  |
| 10d | Handling of missing data             | Methods      | ❌ NOT REPORTED | → Add to Methods |
| 15a | Model performance metrics            | Results      | ✅ REPORTED     |                  |

### MI-CLAIM Compliance: 73% (11/15 items)

...

### Summary

| Guideline | Compliance | ESSENTIAL items | Status                 |
| --------- | ---------- | --------------- | ---------------------- |
| TRIPOD+AI | 85%        | 20/22 ✅        | ⚠️ 2 ESSENTIAL missing |
| MI-CLAIM  | 73%        | 9/10 ✅         | ⚠️ 1 ESSENTIAL missing |

### Action Items (for Author Response)

- [E-M1] TRIPOD+AI Item 10d: Add missing data handling to Methods
- [E-M2] TRIPOD+AI Item 4b: Add data collection end date
- [E-m1] MI-CLAIM Item 12: Add model interpretability discussion
```

##### E5: Integration with Phase 7 Review Loop

```
Phase 7, Stage A（每輪）:
  1. 執行 4 角色 Reviewer 審查 → review-report-{round}.md
  2. 執行 Hook E → equator-compliance-{round}.md
  3. 合併 issues: Review issues + EQUATOR issues → 統一編號
     - Review issues: R1-M1, R2-m1, ...
     - EQUATOR issues: E-M1, E-m1, ... (E = EQUATOR)
  4. Author Response 必須回應兩種 issue

Phase 7, Stage D（品質重評）:
  quality-scorecard 新增維度：
  | 維度 | 評分標準 | 權重 |
  | EQUATOR 合規 | checklist compliance rate + ESSENTIAL 完整度 | 15% |
  → 原有 6 維度權重等比調降，總和仍 = 100%
```
