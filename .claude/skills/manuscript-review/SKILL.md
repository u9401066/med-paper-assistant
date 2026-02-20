---
name: manuscript-review
description: |
  模擬同行審稿與報告指引合規性檢查框架。
  LOAD THIS SKILL WHEN: peer review、同行審查、reviewer、審稿、reporting guidelines、CONSORT、STROBE、PRISMA、CARE、critique、檢查稿件、稿件問題
  CAPABILITIES: 純指令技能，搭配 read_draft MCP tool 讀取草稿內容。LLM 用醫學知識做審查，比 regex 更準確。
---

# 稿件審查與報告指引技能

## 設計意圖

> **為什麼這不是 MCP Tool？**
> Peer review 和 reporting guideline 合規性檢查需要「理解」內容，不是關鍵字匹配。
> - Hard-coded regex 檢查「有沒有 IRB」→ 只能找到 "IRB" 關鍵字
> - LLM 審查 → 能理解 "本研究經台北榮民總醫院倫理委員會核准" 也是 ethics approval
>
> 資料存取（讀草稿）用 `read_draft` MCP tool，審查邏輯由 LLM + 此 skill 的 domain knowledge 完成。

---

## 適用情境

| 觸發語 | 操作 |
|--------|------|
| 「幫我審查一下草稿」 | → Peer Review Framework |
| 「像 reviewer 一樣看看」 | → Peer Review Framework |
| 「CONSORT 合規嗎」 | → Reporting Guideline Framework |
| 「缺了什麼 STROBE 項目」 | → Reporting Guideline Framework |
| 「投稿前檢查」 | → 兩個 Framework 都用 |

---

## 搭配 MCP Tools

| 工具 | 用途 |
|------|------|
| `read_draft` | **必用** — 讀取要審查的草稿內容 |
| `list_drafts` | 列出所有草稿選擇要審查的 |
| `count_words` | 字數統計 |
| `check_formatting` | 期刊格式量化檢查（字數/引用數/圖表數 vs 限制）|
| `check_manuscript_consistency` | 跨文件一致性檢查 |
| `get_section_template` | 對照 section 寫作指南 |

---

## Framework 1: Peer Review (模擬同行審查)

### 工作流程

```
Step 1: read_draft(filename) → 取得草稿內容
Step 2: 按以下 4 大面向逐一審查
Step 3: 輸出結構化審查報告
```

### 審查面向

#### 1. Structure (結構)

檢查項目：

| 項目 | 評估方式 | Major/Minor |
|------|----------|-------------|
| 必要章節是否齊全 | 對照 EXPECTED_SECTIONS 清單 | Major (缺少) |
| Abstract 是否結構化 | 有無 Background/Methods/Results/Conclusions | Minor |
| 邏輯順序 | Introduction → Methods → Results → Discussion | Major (亂序) |

**EXPECTED_SECTIONS by journal type:**

| Journal Type | Required Sections |
|-------------|-------------------|
| General | Abstract, Introduction, Methods, Results, Discussion, References |
| Specialty | Same as General |
| High-Impact | + Limitations, Conclusions (獨立章節) |

#### 2. Methods (方法)

| 項目 | 意義 | Major/Minor |
|------|------|-------------|
| Ethics/IRB statement | 倫理審查核准 | **Major** |
| Statistical methods | 統計分析描述 | **Major** |
| Sample size justification | 樣本數依據/power analysis | Minor |
| Primary outcome definition | 主要結果指標明確定義 | Minor |
| Inclusion/exclusion criteria | 納入排除標準 | Minor |

#### 3. Statistics (統計)

| 項目 | 意義 | Major/Minor |
|------|------|-------------|
| P-value reporting | 報告精確 p-value (非只寫 p<0.05) | Minor |
| Confidence intervals | 效果估計值附 95% CI | **Major** |
| Multiple comparisons | 多重比較校正 (Bonferroni/FDR) | Minor |
| Effect size reporting | 臨床意義 vs 統計顯著 | Minor |

#### 4. Writing Quality (寫作品質)

| 項目 | 意義 | Major/Minor |
|------|------|-------------|
| Limitations section | 有獨立的限制段落 | **Major** |
| Causal language in observational | 觀察性研究不應使用因果用語 | **Major** |
| Word count | 符合期刊字數限制 | Minor |
| Reference density | 引用密度適當 | Minor |
| Hedging language | 結論是否過度強力 | Minor |

### 嚴重程度判斷

```
Major Issues = Reviewer 可能要求 major revision 或 reject
Minor Issues = Reviewer 會建議改善但不影響接受

Major ≥ 3  → 🔴 Major revision required
Major 1-2  → 🟡 Major revision
Major = 0  → ✅ Minor revision or accept
```

### 輸出結構

```markdown
# 📝 Peer Review Report

**Draft:** {filename}
**Journal Type:** {general/specialty/high-impact}
**Focus:** {comprehensive/methods/statistics/writing}

---

## Major Issues (X items)

### 1. [Category] {issue_title}
- **Problem:** {description}
- **Suggestion:** {specific fix}

## Minor Issues (Y items)

### 1. [Category] {issue_title}
- **Problem:** {description}
- **Suggestion:** {specific fix}

---

**Recommendation:** {✅/🟡/🔴}

💡 Use `check_reporting_guidelines` skill for guideline-specific checks.
```

---

## Framework 2: Reporting Guideline Compliance (報告指引合規)

### 工作流程

```
Step 1: read_draft(filename) → 取得草稿內容（支持多檔案逗號分隔）
Step 2: 自動偵測或由使用者指定適用的 guideline
Step 3: 逐一檢查 checklist 項目
Step 4: 輸出合規報告
```

### Auto-Detection Rules

| 草稿特徵 | 適用指引 |
|----------|----------|
| randomized, RCT, blinded, placebo | **CONSORT** |
| systematic review, meta-analysis, PRISMA | **PRISMA** |
| case report, case presentation | **CARE** |
| 其他（observational, cohort, case-control） | **STROBE** |

---

### 📋 CONSORT Checklist (RCT, 21 items)

| Section | Item | 檢查重點 |
|---------|------|----------|
| Title | 1. Identified as RCT | 標題包含 "randomised/randomized" |
| Abstract | 2. Structured abstract | Background, Methods, Results, Conclusions |
| Introduction | 3. Background & rationale | 科學背景和解釋邏輯 |
| Introduction | 4. Specific objectives/hypotheses | 具體目的或假說 |
| Methods | 5. Trial design | 描述試驗設計 (parallel, crossover, factorial) |
| Methods | 6. Eligibility criteria | 參與者的納入排除標準 |
| Methods | 7. Interventions | 每組介入方式的充分描述 |
| Methods | 8. Outcomes defined | 預先指定的主要和次要結果 |
| Methods | 9. Sample size determination | 樣本數如何決定 |
| Methods | 10. Randomization | Sequence generation 方法 |
| Methods | 11. Allocation concealment | 分配隱匿機制 |
| Methods | 12. Blinding | 誰被盲化 (participants, care providers, outcome assessors) |
| Methods | 13. Statistical methods | 主要和次要結果的統計方法 |
| Results | 14. Participant flow | Flow diagram (enrollment, allocation, follow-up, analysis) |
| Results | 15. Recruitment dates & follow-up | 招募和追蹤的日期 |
| Results | 16. Baseline data | 各組的基線人口學和臨床特徵 |
| Results | 17. Number analysed | 每組分析的人數 (ITT/PP) |
| Results | 18. Outcomes & estimation | 每個結果的效果估計和精確度 (95% CI) |
| Results | 19. Harms | 不良事件 |
| Discussion | 20. Interpretation | 結果的解釋、限制、external validity |
| Other | 21. Registration & protocol | 試驗註冊 (ClinicalTrials.gov) 和 protocol |

---

### 📋 STROBE Checklist (Observational, 16 items)

| Section | Item | 檢查重點 |
|---------|------|----------|
| Title | 1. Study design in title/abstract | 標題或摘要指出研究設計 |
| Introduction | 2. Background/rationale | 科學背景和理由 |
| Introduction | 3. Objectives | 具體目的和假說 |
| Methods | 4. Study design | 研究設計的關鍵元素 |
| Methods | 5. Setting | 地點、日期、招募、追蹤 |
| Methods | 6. Participants | 納入排除標準、來源、方法 |
| Methods | 7. Variables | 結果變項、暴露因子、混淆因子 |
| Methods | 8. Data sources/measurement | 資料來源和每個變項的測量方法 |
| Methods | 9. Bias | 處理潛在偏誤的方法 |
| Methods | 10. Study size | 樣本數如何決定 |
| Methods | 11. Statistical methods | 統計方法和控制混淆的方法 |
| Results | 12. Participants | 每階段的人數和不參與的原因 |
| Results | 13. Descriptive data | 參與者特徵和暴露資訊 |
| Results | 14. Outcome data & main results | 結果和效果估計 |
| Discussion | 15. Interpretation | 結果解釋、限制、generalizability |
| Other | 16. Funding | 資金來源 |

---

### 📋 PRISMA Checklist (Systematic Review, 17 items)

| Section | Item | 檢查重點 |
|---------|------|----------|
| Title | 1. Identify as systematic review | 標題標明 systematic review |
| Abstract | 2. Structured summary | 結構式摘要 |
| Introduction | 3. Rationale & objectives | 理由和具體研究問題 (PICO) |
| Methods | 4. Protocol & registration | Protocol 和註冊 (PROSPERO) |
| Methods | 5. Eligibility criteria | 研究的納入排除標準 |
| Methods | 6. Information sources | 搜尋的資料庫和日期 |
| Methods | 7. Search strategy | 完整的電子搜尋策略 |
| Methods | 8. Study selection | 篩選流程、獨立雙人篩選 |
| Methods | 9. Data extraction | 資料萃取過程 |
| Methods | 10. Risk of bias assessment | 偏誤風險評估方法 |
| Methods | 11. Synthesis methods | 合成方法和異質性評估 |
| Results | 12. Study selection flow | PRISMA flow diagram |
| Results | 13. Study characteristics | 各研究特徵和偏誤評估 |
| Results | 14. Synthesis results | 合成結果和 forest plot |
| Results | 15. Heterogeneity | 異質性評估 (I², Q test) |
| Discussion | 16. Summary & limitations | 證據摘要和限制 |
| Other | 17. Registration number | PROSPERO 或其他註冊號 |

---

### 📋 CARE Checklist (Case Report, 13 items)

| Section | Item | 檢查重點 |
|---------|------|----------|
| Title | 1. Identify as case report | 標題標明 "case report" |
| Abstract | 2. Key information summary | 包含介紹、描述和討論的摘要 |
| Introduction | 3. Background with references | 文獻引用的背景 |
| Patient | 4. Demographics | 病人年齡、性別、種族 |
| Patient | 5. Chief complaints | 主訴和症狀 |
| Patient | 6. Medical history | 相關病史和合併症 |
| Patient | 7. Physical examination | 相關身體檢查發現 |
| Clinical | 8. Diagnostic assessment | 診斷方法、挑戰和推理 |
| Clinical | 9. Intervention | 介入措施的類型和管理 |
| Clinical | 10. Follow-up & outcome | 追蹤和結果 |
| Discussion | 11. Strengths & limitations | 討論優勢和限制 |
| Discussion | 12. Rationale for conclusions | 結論的依據 |
| Patient | 13. Informed consent | 病人同意聲明 |

---

### 輸出結構

```markdown
# 📋 {GUIDELINE_NAME} Checklist

**Files checked:** {filenames}
**Guideline:** {auto-detected or specified}

## Summary
- **Compliance:** X/Y items (Z%)
- ✅ Found: X
- ❌ Not found: Y

## Checklist by Section

### {Section Name}
| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | {description} | ✅/❌ | {where found or what's missing} |

(repeat for all sections)

## ⚠️ Action Items

1. **{Missing Item}** — {suggestion for how to add}
2. ...

---
🟢 Compliance ≥ 80%: Good shape for submission
🟡 Compliance 60-80%: Needs attention
🔴 Compliance < 60%: Significant gaps to address
```

---

## ⚠️ 使用原則

1. **LLM 審查 > regex 匹配** — 理解語意，不要只找關鍵字
2. **永遠先讀草稿** — 用 `read_draft` MCP tool 取得實際內容
3. **Major/Minor 分類要準確** — Major = 可能被 reject，Minor = 改善建議
4. **給具體修復建議** — 不只指出問題，說明怎麼修
5. **與 `check_formatting` 互補** — 本 skill 做質性審查，`check_formatting` tool 做量化檢查
6. **Checklist 項目要看語意** — 例如「informed consent」可能寫成「同意書」「知情同意」
7. **多檔案支持** — 用戶可能 Introduction 和 Methods 在不同檔案

---

## 相關技能

- `draft-writing` — 撰寫/修改草稿（審查前）
- `academic-debate` — 挑戰研究主張的強度
- `concept-development` — 概念發展和驗證
- `word-export` — 投稿前匯出 Word
