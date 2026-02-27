---
name: draft-writing
description: |
  論文草稿的撰寫、讀取、引用管理。
  LOAD THIS SKILL WHEN: 寫草稿、draft、撰寫、Introduction、Methods、Results、Discussion、引用、citation、字數、patch、編輯草稿
  CAPABILITIES: write_draft, draft_section, read_draft, list_drafts, insert_citation, sync_references, count_words, get_available_citations, patch_draft
---

# 草稿撰寫技能

觸發：寫草稿、draft、section、引用、citation、字數、patch、寫作順序

## 前置條件

1. `get_current_project()` 確認專案
2. concept.md 存在且 🔒 區塊非空（寫 concept.md 本身除外）

---

## MCP Tools

### 撰寫

| 工具                  | 說明                                              |
| --------------------- | ------------------------------------------------- |
| `write_draft`         | 建立/覆寫草稿（`filename`, `content`, `project`） |
| `draft_section`       | 根據 notes 產出 section（`topic`, `notes`）       |
| `read_draft`          | 讀取草稿                                          |
| `list_drafts`         | 列出所有草稿                                      |
| `check_writing_order` | ⭐ 檢查寫作順序與進度（advisory, 不阻止）         |

### 引用（⚠️ 修改引用必須用 `patch_draft`，禁止 `replace_string_in_file`）

| 工具                      | 說明                                              |
| ------------------------- | ------------------------------------------------- |
| `get_available_citations` | ⚠️ 編輯前必呼叫！列出可用 `[[citation_key]]`      |
| `patch_draft`             | 部分編輯草稿，自動驗證 wikilinks                  |
| `insert_citation`         | 定點插入引用（`filename`, `target_text`, `pmid`） |
| `sync_references`         | 掃描 [[wikilinks]] 生成 References                |
| `count_words`             | 計算字數                                          |

**patch_draft vs replace_string_in_file**：patch_draft 驗證引用、自動修復格式、拒絕不存在的引用。

---

## 自動快照（CONSTITUTION §22 Auditable）

所有草稿寫入路徑（`write_draft`、`patch_draft`、`insert_citation`、`create_draft`）在覆寫前**自動建立快照**，儲存於 `drafts/.snapshots/`。

- 最多保留 20 個快照/檔案，自動清理
- 不依賴 git 或 agent 合作，純粹在寫入路徑中觸發
- 使用 `DraftSnapshotManager`（`infrastructure/persistence/`）

---

## 寫作順序（Advisory）

| Paper Type        | 順序                                                                  |
| ----------------- | --------------------------------------------------------------------- |
| original-research | Methods → Results → Introduction → Discussion → Conclusion → Abstract |
| systematic-review | Methods → Results → Discussion → Introduction → Conclusion → Abstract |
| case-report       | Case Presentation → Discussion → Introduction → Conclusion → Abstract |
| review-article    | Introduction → Body → Conclusion → Abstract                           |

前置：Results 需 Methods、Discussion 需 Results+Intro、Conclusion 需 Discussion、Abstract 需全部。
`check_writing_order()` 產生警告，不阻止。警告出現時詢問用戶是否繼續。

---

## Flow A: 撰寫新 Section

1. `check_writing_order()` → 確認前置
2. `validate_for_section(section)` → ✅/❌
3. `read_draft("concept.md")` → 提取 🔒 NOVELTY + 🔒 SELLING POINTS
4. 參考下方 Section 指南撰寫
5. `count_words()`
6. `approve_section(section, action)` → 用戶審閱 approve/revise（Phase 5 時 MANDATORY）

## Flow B: Citation-Aware 編輯

1. `get_available_citations()` → 取得可用 citation keys
2. `patch_draft(filename, old_text, new_text)` → 自動驗證 wikilinks
3. `sync_references(filename)` → 生成 References

---

## 🔒 受保護內容

- Introduction 開頭/結尾必須呼應 🔒 NOVELTY
- Discussion 必須逐條強調 🔒 SELLING POINTS
- 不可刪除或弱化 🔒 區塊。修改前必須詢問用戶

---

## Section 寫作指南

> 以下每條指南都有對應的 Code-Enforced Hook（B9-B16），`run_writing_hooks` 會自動檢查。

### Introduction (400-600 words)

**結構（Funnel Model — Hook B12 自動偵測）：**

1. **Broad Context** (1-2 段)：臨床問題的重要性與盛行率，用具體數字（發生率、死亡率）
2. **Evidence Base** (1-2 段)：目前文獻的發現，必須有 `[[wikilinks]]` 引用
3. **Knowledge Gap** (1 段)：先前研究的不足之處→ 對應 🔒 NOVELTY
4. **Study Objective** (最後一段)：「This study aimed to...」或「We sought to...」

**時態（Hook B9）：**

- 已確立的事實 → **現在式**（「Diabetes is characterized by...」）
- 先前研究的結果 → **過去式**（「Smith et al. reported that...」）

**禁止事項：**

- 🚫 "In recent years..." / "With the rapid development of..."
- 🚫 每段開頭用 "Furthermore" / "Moreover" / "Additionally"
- 🚫 在 Introduction 透露自己的 Results（Hook B12 CRITICAL）
- 🚫 過多 hedging：「may potentially suggest...」（Hook B15）

**Checklist（Agent 自行確認）：**

- [ ] 第一段有具體流行病學數字
- [ ] 有 ≥3 個引用支持 Evidence Base
- [ ] Knowledge Gap 用轉折語（however, nevertheless, yet）
- [ ] 最後一段明確陳述研究目的

---

### Methods (800-1200 words)

**結構：**

1. **Study Design & Setting**：研究類型、單/多中心、時間範圍
2. **Participants**：納入/排除標準、年齡、母群體
3. **Intervention / Exposure**：介入描述或暴露定義
4. **Outcomes**：Primary + Secondary endpoints，明確定義
5. **Statistical Analysis**：分析方法、軟體版本、顯著性標準

**時態（Hook B9 CRITICAL）：**

- 所有描述必須用**過去式**（「We enrolled...」「Data were collected...」）
- 🚫 禁止用現在式描述已完成的方法步驟

**倫理聲明（Hook B14 CRITICAL）：**

- ✅ 必須包含 IRB / Ethics committee approval + 核准編號
- ✅ 必須包含 Informed consent statement（或 waiver 說明）
- ✅ 如為介入研究：必須包含 Trial registration number (e.g., NCT12345678)

**統計報告規範（Hook B8 / B16）：**

- 必須在 Methods 中預先列出 Results 中所有用到的統計方法
- Events 應能對應到 Methods 中的 Outcomes 定義

**Checklist：**

- [ ] 研究設計一開始就聲明
- [ ] 納入排除標準明確列出
- [ ] 統計方法對應所有結果變量
- [ ] 倫理聲明 + Informed consent 存在
- [ ] 如 RCT：有 randomization 和 allocation concealment 描述

---

### Results (600-1000 words)

**結構：**

1. **Participant Flow**：篩選→納入→分析的人數（搭配 CONSORT 流程圖）
2. **Baseline Characteristics**：Table 1 描述，組間比較
3. **Primary Outcome**：主要結果 + 效果量 + 95% CI + p-value
4. **Secondary Outcomes**：次要結果分組報告
5. **Adverse Events / Safety**：如適用

**時態（Hook B9 CRITICAL）：**

- 所有結果描述必須用**過去式**（「was observed」「were significantly higher」）

**客觀性（Hook B11 CRITICAL — 最常見 Reviewer 意見）：**

- ✅ Results 只報告觀察到的資料和統計結果
- 🚫 禁止解讀性語言：「suggesting that」「indicating」「demonstrating that」
- 🚫 禁止主觀形容：「interestingly」「surprisingly」「remarkably」
- 🚫 禁止推測：「may be due to」「possibly reflects」「we believe」
- → 解讀屬於 Discussion

**統計報告（Hook B16）：**

- ✅ 報告精確 p-value（p = 0.032），不只用 p < 0.05
- 🚫 禁止 「p = 0.000」→ 應寫 p < 0.001
- ✅ 效果量（OR, HR, RR, MD, Cohen's d）必須伴隨 p-value
- ✅ 所有效果量應附帶 95% CI

**Checklist：**

- [ ] 有明確的參與者篩選數字
- [ ] Primary outcome 有 effect size + 95% CI + p-value
- [ ] 無解讀性語言（B11 PASS）
- [ ] 全部用過去式
- [ ] 圖表有正文敘述對應

---

### Discussion (1000-1500 words)

**結構（Hook B13 自動偵測）：**

1. **Main Findings** (第 1 段)：重述主要發現（含 🔒 SELLING POINTS）
2. **Literature Comparison** (2-3 段)：與先前研究比較，有 `[[wikilinks]]` ≥3 個
3. **Mechanism / Explanation** (1 段)：可能機制或臨床解釋
4. **Clinical Implications** (1 段)：臨床實踐意義或未來方向
5. **Limitations** (1 段，Hook B13 CRITICAL)：誠實承認研究局限
6. **Conclusion** (最後 1-2 句)：簡潔重述核心發現

**Limitations 段落（必要 — Hook B13 觸發 CRITICAL）：**

- ✅ 必須包含 "limitation" / "weakness" / "shortcoming"
- ✅ 至少提 2-3 個具體限制：研究設計、樣本量、追蹤時間、選擇偏差等
- ✅ 對每個限制解釋為什麼不影響主要結論（或承認可能影響方向）

**Hedging 控制（Hook B15）：**

- Discussion 可以適度使用 hedging（may, might, could）
- 但密度超過 6/1000 字 → CRITICAL（文稿顯得不確定）
- 目標：3/1000 字以下

**禁止事項：**

- 🚫 重複引用 Introduction 已提過的背景知識
- 🚫 在 Discussion 引入新數據（屬於 Results）
- 🚫 過度擴大結論到研究設計無法支持的範圍

**Checklist：**

- [ ] 第一段重述 main findings
- [ ] 有 ≥3 個與先前文獻的比較引用
- [ ] Limitations 段落存在且具體
- [ ] 有 clinical implications 或 future directions
- [ ] 結論簡潔、不超出數據支持範圍

---

### Abstract (250-350 words)

**結構（Structured）：**

1. **Background** (2-3 句)：問題 + gap + 目的
2. **Methods** (3-4 句)：設計、受試者、主要測量
3. **Results** (3-5 句)：主要結果 + 關鍵數字 + p-values
4. **Conclusions** (1-2 句)：核心發現 + 意義

**規則：**

- ✅ Abstract 是獨立的微型論文，不依賴正文即可理解
- ✅ Abstract 中的數字必須與 Results 完全一致
- 🚫 不在 Abstract 中引用文獻
- 🚫 不使用未定義的縮寫（Abstract 中的縮寫要重新定義）

---

## Code-Enforced Writing Hooks 對照表

| Hook | 名稱                 | 觸發時機     | 嚴重度        | 檢查重點                             |
| ---- | -------------------- | ------------ | ------------- | ------------------------------------ |
| B9   | Section Tense        | POST-WRITE   | CRITICAL/WARN | Methods/Results 過去式               |
| B10  | Paragraph Quality    | POST-WRITE   | WARN/INFO     | 段落長度、單句段落                   |
| B11  | Results Objectivity  | POST-SECTION | CRITICAL      | Results 禁止解讀性語言               |
| B12  | Intro Funnel         | POST-SECTION | CRITICAL/WARN | Introduction 漏斗結構 + 禁止透露結果 |
| B13  | Discussion Structure | POST-SECTION | CRITICAL      | Limitations 必須存在                 |
| B14  | Ethical Statements   | POST-SECTION | CRITICAL      | IRB + Consent + Trial Reg            |
| B15  | Hedging Density      | POST-WRITE   | CRITICAL/WARN | may/might/could 密度                 |
| B16  | Effect Size          | POST-SECTION | CRITICAL/WARN | p-value 格式 + 效果量 + CI           |

使用方式：`run_writing_hooks("B9,B11,B13")` 或 `run_writing_hooks("post-section")`

---

## Wikilink 格式

✅ `[[author2024_12345678]]` → 自動修復 `[[12345678]]` → `[[author2024_12345678]]`
