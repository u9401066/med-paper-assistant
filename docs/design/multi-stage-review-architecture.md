# Multi-Stage Review Architecture 設計文件

> **狀態**: ✅ CONFIRMED — 所有討論事項已確認，進入實作階段
> **日期**: 2026-02-25
> **影響**: auto-paper SKILL.md, write-paper.prompt.md, 新增 prompt + agent mode

---

## 0. 設計決定摘要

| #      | 議題                      | 決定                                                           | 影響                    |
| ------ | ------------------------- | -------------------------------------------------------------- | ----------------------- |
| **D1** | Hook A 粒度               | Section 級觸發，B7 做 paragraph 級 brief 比對                  | Hook A 不變             |
| **D2** | manuscript-plan.yaml 彈性 | Agent 可修改，需 audit trail，不可刪 `protected: true`         | Phase 5 邏輯            |
| **D3** | Agent Mode                | VS Code 已支援，直接實作                                       | P7 升級 🟡              |
| **D4** | journal-profile.yaml      | 有預設值，Agent 參照但盡量不變更，用戶可改需有紀錄             | 加 changelog            |
| **D5** | C7 擴展                   | 引用數量 + 圖表數量 + 交叉引用 **全併 C7**                     | C7 → 數量與交叉引用合規 |
| **D6** | caption_requirements      | B7 順帶檢查 asset_plan 的 caption_requirements                 | B7 範圍含圖說           |
| **D7** | Review Report 結構化      | YAML front matter + 每個 issue 結構化 + Hook D 可演化 Reviewer | Phase 7 + D 擴展        |

---

## 1. 問題陳述

### 1.1 現有架構的三個缺口

| #      | 缺口                                | 現狀                                                    | 影響                           |
| ------ | ----------------------------------- | ------------------------------------------------------- | ------------------------------ |
| **G1** | Phase 4 產出粒度太粗                | 大綱只有 section 級，沒有段落級的內容指令               | Agent 缺乏「每段該寫什麼」指引 |
| **G2** | journal-profile.yaml 沒有程式化接口 | Agent 靠 `read_file` 解析，Hook 閾值寫死在 SKILL.md     | 換期刊要手動改很多地方         |
| **G3** | Phase 7 Review 產出不結構化         | Review 意見直接修正，無 Review Report + Author Response | 無法追溯「為什麼改」           |

### 1.2 用戶需求

1. **精細操作到每段**：指定每段的論點、必引文獻、字數預算
2. **journal-profile 驅動**：所有 Hook 閾值從 YAML 讀取，不硬編碼
3. **write→review→response 多輪循環**：模擬真實的投稿—審稿—回覆流程（3 rounds）
4. **獨立觸發審計**：不用跑完整 pipeline 也能單獨做 Phase 6+7
5. **Reviewer 自我演化**：Review 結果回饋到 Hook D，改進 Reviewer 指令

---

## 2. 設計方案

### 2.1 四層觸發機制

```
┌──────────────────────────────────────────────────────────────────┐
│  Prompt (.prompt.md)          → 「何時」= 流程編排 + Gate       │
│    └─ Skill (SKILL.md)        → 「如何」= 執行細節 + Loop 邏輯  │
│        └─ Hook (in Skill)     → 「品質」= pass/fail 閘門        │
│    └─ Agent Mode (.agent.md)  → 「角色」= 工具限制 + 唯讀/可寫  │
└──────────────────────────────────────────────────────────────────┘
```

| 層         | 新增/修改                       | 解決的缺口                               |
| ---------- | ------------------------------- | ---------------------------------------- |
| Prompt     | 新增 `mdpaper.audit.prompt.md`  | 獨立觸發 Phase 6+7（G3）                 |
| Skill      | 修改 Phase 4 產出 Section Brief | 段落級精細控制（G1）                     |
| Hook       | B7 新增 + C7 擴展 + D7 新增     | journal-profile 驅動 + 圖表 + 演化（G2） |
| Agent Mode | 新增 `paper-reviewer.agent.md`  | 唯讀審稿模式（G3 補強）                  |

---

### 2.2 Section Brief 機制（解決 G1）

#### 2.2.1 Phase 4 產出物：manuscript-plan.yaml

**現狀**：Phase 4 產出粗粒度大綱（section → topic + refs）
**改為**：Phase 4 產出 `manuscript-plan.yaml`（存在 `projects/{slug}/` 下）

```yaml
# manuscript-plan.yaml — Phase 4 產出物
# Agent 根據 concept.md + saved references + journal-profile.yaml 自動生成
# 用戶在 Phase 4 Gate 確認（唯一人工介入點）

metadata:
  generated_at: "2026-02-25T10:00:00"
  based_on:
    concept: "concept.md"
    journal_profile: "journal-profile.yaml"
    reference_count: 18
  changelog: [] # Agent/用戶修改記錄

writing_order:
  - "Methods"
  - "Results"
  - "Introduction"
  - "Discussion"
  - "Conclusions"
  - "Abstract"

sections:
  Introduction:
    word_budget: 800
    paragraphs:
      - id: "intro-p1"
        function: "context-setting"
        topic: "Difficult airway 的臨床重要性與發生率"
        key_claims:
          - "Difficult airway 發生率 1-18%"
          - "預測失敗的後果嚴重"
        must_cite:
          - "[[Kheterpal_2009_19293700]]"
          - "[[Cook_2011_21106601]]"
        word_target: 150
      - id: "intro-p2"
        function: "gap-identification"
        topic: "現有預測方法的局限性"
        key_claims:
          - "Mallampati 等單一指標敏感度低"
          - "多變量模型預測力仍有限"
        must_cite:
          - "[[Lundstrom_2011_21873370]]"
        word_target: 200
      - id: "intro-p3"
        function: "novelty-statement"
        topic: "AI/ML 預測模型的潛力 + 本文研究目的"
        key_claims:
          - "ML 可整合多維度特徵"
          - "本研究填補 [specific gap]"
        must_cite:
          - "[[Connor_2019_31955642]]"
        protected: true # 🔒 Hook B2 保護
        word_target: 150

  Methods:
    word_budget: 1500
    paragraphs:
      - id: "methods-p1"
        function: "study-design"
        topic: "研究設計、場域、時間範圍"
        key_claims:
          - "回溯性觀察研究 / 前瞻性隊列"
          - "IRB 核准 + 知情同意"
        must_cite: []
        word_target: 200
        checklist_items: # 對應 B5 方法學
          - "研究設計描述"
          - "倫理聲明"
          - "收集期間"

  Discussion:
    word_budget: 1500
    paragraphs:
      - id: "disc-p1"
        function: "summary"
        topic: "主要發現摘要"
        word_target: 200
      - id: "disc-p2"
        function: "selling-point-1" # 🔒 SELLING POINT
        topic: "賣點一：ML 預測優於傳統"
        protected: true
        word_target: 300
      - id: "disc-p5"
        function: "limitations"
        topic: "研究限制"
        word_target: 200

asset_plan:
  - id: "figure-1"
    section: "Results"
    after_paragraph: "results-p2"
    type: "plot"
    source: "auto" # auto | user-provided | script
    description: "ROC curves comparing ML models vs Mallampati"
    tool: "create_plot"
    tool_args:
      plot_type: "roc_curve"
      data_file: "model_predictions.csv"
    caption: |
      Figure 1. Receiver operating characteristic (ROC) curves
      comparing machine learning models with Mallampati classification
      for difficult airway prediction.
    caption_requirements:
      - "統計數據 (AUC/p-value)"
      - "95% CI"
      - "組間比較說明"

  - id: "figure-2"
    section: "Methods"
    after_paragraph: "methods-p4"
    type: "flow_diagram"
    source: "auto"
    tool: "drawio"
    caption: |
      Figure 2. Flow diagram of patient selection.
    caption_requirements:
      - "每個階段的 N 值"
      - "排除原因與人數"

  - id: "table-1"
    section: "Results"
    after_paragraph: "results-p1"
    type: "table_one"
    source: "auto"
    tool: "generate_table_one"
    caption: |
      Table 1. Baseline characteristics of patients with and without
      difficult airway. Values are presented as mean ± SD or n (%).
    caption_requirements:
      - "數值呈現方式說明"
      - "統計檢定方法"
      - "顯著性標示說明"

submission_checklist:
  - item: "cover_letter"
    status: "pending"
  - item: "author_contributions"
    status: "pending"
```

#### 2.2.2 Plan 修改規則（D2 + D4）

| 操作                   | Agent                         | 用戶      |
| ---------------------- | ----------------------------- | --------- |
| 新增段落               | ✅ 需 audit trail + 完整 spec | ✅ 自由   |
| 修改 key_claims        | ✅ 需記錄原因                 | ✅ 自由   |
| 刪除 `protected: true` | ❌ 禁止                       | ✅ 需確認 |
| 修改 word_target       | ✅ 需記錄原因                 | ✅ 自由   |

修改追加到 `metadata.changelog`：

```yaml
changelog:
  - timestamp: "2026-02-25T12:30:00"
    agent: true
    change: "新增 methods-p5 (subgroup analysis)"
    reason: "Reviewer R2 建議加入 subgroup 分析"
```

#### 2.2.3 Phase 5 使用 Section Brief

```
FOR section IN writing_order:
  brief = manuscript_plan.sections[section]

  FOR paragraph IN brief.paragraphs:
    ── 準備 → 撰寫 → 下一段 ──

  ── Hook A (per-section, D1 決定) ──
  A1: 字數 vs section.word_budget
  A2: 引用密度（含 Figure/Table 引用）
  A3: Anti-AI
  A4: Wikilink 格式

  ── Hook B (per-section) ──
  B1-B6: 現有檢查
  B7: Section Brief 合規（paragraph 級比對 + caption_requirements）
```

---

### 2.3 Journal-Profile 驅動 Hook 閾值（解決 G2）

#### 2.3.1 閾值來源對照表

| Hook    | 檢查項    | 改為來源                                                              |
| ------- | --------- | --------------------------------------------------------------------- |
| A1      | 字數      | `paper.sections[name].word_limit` ± `pipeline.tolerance.word_percent` |
| A2      | 引用密度  | `pipeline.writing.citation_density.*`                                 |
| A3      | Anti-AI   | `pipeline.writing.anti_ai_strictness`                                 |
| C7      | 數量合規  | `assets.*_max` + `word_limits.*`                                      |
| B5      | 方法學    | `reporting_guidelines.checklist`                                      |
| Phase 7 | 閾值/輪數 | `pipeline.autonomous_review.*`                                        |

#### 2.3.2 journal-profile.yaml 新增欄位

```yaml
pipeline:
  tolerance:
    word_percent: 20
    citation_density_strict: true
  section_brief:
    enabled: true
    paragraph_level: true
    enforce_must_cite: true
  changelog: []
```

#### 2.3.3 Fallback

```
IF journal-profile.yaml 存在 → 用 YAML 值
IF 不存在 → 用 SKILL.md 預設值（向後相容）
IF 欄位缺失 → 用 template 預設值
```

#### 2.3.4 保護規則（D4）

- Agent **只讀** journal-profile.yaml，用於計算/比對
- 用戶可自行修改，但需有 changelog 紀錄
- Agent 僅允許建議修改 pipeline 參數（如 `hook_a_max_rounds`），需用戶確認

---

### 2.4 Hook B7: Section Brief 合規（新增）

**觸發**：每個 section 寫完後，B1-B6 之後

| 子項 | 檢查內容                                     |
| ---- | -------------------------------------------- |
| B7a  | 每段 `key_claims` 是否在文中涵蓋             |
| B7b  | 每段 `must_cite` 是否出現                    |
| B7c  | 段落順序/數量 vs plan（advisory）            |
| B7d  | 該 section 的 `asset_plan` 項目是否已插入    |
| B7e  | 已插入圖表的 `caption_requirements` 是否滿足 |

**失敗行為**：

- 遺漏 key_claim → `patch_draft` 加入論點
- 遺漏 must_cite → `patch_draft` 加入引用
- 遺漏 asset → WARNING + 提示插入圖表
- caption 不完整 → `patch_draft` 補充圖說
- 順序偏離 → WARNING（advisory）

---

### 2.5 Hook C7 擴展：數量與交叉引用合規（D5）

**原 C7**：只查圖表數量
**擴展後**：三合一數量 + 交叉引用

| 子項 | 檢查內容                       | MCP Tool                     |
| ---- | ------------------------------ | ---------------------------- |
| C7a  | 圖表總數 ≤ 上限                | `list_assets`                |
| C7b  | 引用總數合理範圍               | `scan_draft_citations`       |
| C7c  | 總字數 vs journal-profile      | `count_words`                |
| C7d  | 圖表交叉引用（orphan/phantom） | `list_assets` + `read_draft` |
| C7e  | Wikilink 引用一致性            | `validate_wikilinks`         |

```
orphan = manifest - draft_refs → WARNING（有圖沒引用）
phantom = draft_refs - manifest → CRITICAL（有引用沒圖）
```

> **NOTE**: C6（總字數）功能與 C7c 部分重疊。實作時決定是否 deprecated C6 或保留做快速檢查。

---

### 2.6 結構化 Review Loop（解決 G3）

#### 2.6.1 循環架構（3 rounds）

```
Phase 7 入口：Phase 6 通過（0 CRITICAL）

FOR round = 1 TO 3:

  ── Stage A: Review Report（YAML front matter） ──
  FOR perspective IN reviewer_perspectives:
    Agent 以角色全文審稿 → 結構化意見

  產出 review-report-{round}.md:
  ┌─────────────────────────────────────────────────┐
  │ ---                                             │
  │ round: 1                                        │
  │ date: "2026-02-25"                              │
  │ reviewers:                                      │
  │   - role: "Methodology Expert"                  │
  │     issues_major: 2                             │
  │     issues_minor: 1                             │
  │   - role: "Domain Specialist"                   │
  │     issues_major: 1                             │
  │     issues_minor: 3                             │
  │ total:                                          │
  │   major: 3                                      │
  │   minor: 5                                      │
  │   optional: 2                                   │
  │ ---                                             │
  │                                                 │
  │ # Review Report — Round 1                       │
  │                                                 │
  │ ## Reviewer 1: Methodology Expert               │
  │ ### MAJOR                                       │
  │ - id: R1-M1                                     │
  │   section: Methods                              │
  │   paragraph: methods-p3                         │
  │   category: methodology                         │
  │   issue: 缺少 sample size justification         │
  │   suggestion: 加入 power analysis               │
  │                                                 │
  │ ### MINOR                                       │
  │ - id: R1-m1                                     │
  │   ...                                           │
  └─────────────────────────────────────────────────┘

  ── Stage B: Author Response（全 issue 須回應） ──
  產出 author-response-{round}.md:
  ┌─────────────────────────────────────────────────┐
  │ ---                                             │
  │ round: 1                                        │
  │ response_to: "review-report-1.md"               │
  │ actions:                                        │
  │   accepted: 6                                   │
  │   accepted_modified: 2                          │
  │   declined: 2                                   │
  │ ---                                             │
  │                                                 │
  │ # Author Response — Round 1                     │
  │                                                 │
  │ ### R1-M1: Sample size justification            │
  │ - **Action**: ACCEPT                            │
  │ - **Response**: Added power analysis...         │
  │ - **Change**: methods-p3 (+45 words)            │
  │ - **Verified**: Hook A re-run ✅               │
  │                                                 │
  │ ## Completeness Check                           │
  │ | Issue ID | Addressed | Action      |          │
  │ | R1-M1    | ✅       | ACCEPT      |          │
  │ | R2-o1    | ✅       | DECLINE     |          │
  │ ALL issues addressed: ✅                        │
  └─────────────────────────────────────────────────┘

  ── Stage C: 執行修正 ──
  FOR each ACCEPTED issue:
    1. 定位 paragraph ID
    2. patch_draft() 修正
    3. re-run Hook A on patched section
    4. 記錄到 author-response

  ── Stage D: 品質重評 ──
  更新 quality-scorecard.md
  IF 總分 ≥ threshold → PASS
  IF round = 3 AND < threshold → 用戶決定
```

#### 2.6.2 Completeness Check

每輪 Author Response 結束時：

```
FOR issue IN review_report.all_issues:
  IF issue.id NOT IN author_response → FAIL
```

**未回應的 issue 必須標記 DECLINE + 理由**，不可忽略。

#### 2.6.3 Review vs Hook 分工

| 面向   | Hook A-C (Phase 5-6)  | Phase 7 Review                  |
| ------ | --------------------- | ------------------------------- |
| 關注點 | 格式/字數/引用/一致性 | 內容品質/邏輯/說服力            |
| 粒度   | pass/fail             | MAJOR/MINOR/OPTIONAL            |
| 修正   | auto patch            | Author Response 決策            |
| 產出   | audit log             | review-report + author-response |
| 停止   | 0 CRITICAL            | quality ≥ threshold             |

---

### 2.7 Hook D7: Review Retrospective（D7 決定）

| Hook   | 名稱                 | 觸發     | 做法                                 |
| ------ | -------------------- | -------- | ------------------------------------ |
| **D7** | Review Retrospective | Phase 10 | 分析 review 產出，演化 Reviewer 指令 |

**流程**：

```
Phase 10 — D7:
  1. 讀取 review-report-*.md + author-response-*.md
  2. 統計：
     - 哪些 reviewer 的 MAJOR issues 最有價值？
     - 哪些 suggestions ACCEPT 率最高？
     - 哪些 issues 反覆出現？
     - 哪些 reviewer 的建議被 DECLINE 最多？
  3. 更新 SKILL.md Phase 7 的 reviewer 描述
  4. 記錄到 Lessons Learned
```

**限制**（CONSTITUTION §23 L2 級）：調整閾值 ±20%，不可改 CONSTITUTION 原則。

---

### 2.8 新增 Prompt：`mdpaper.audit`

獨立觸發 Phase 6+7，不需跑完整 pipeline。

| Prompt                 | 覆蓋 Phase       |
| ---------------------- | ---------------- |
| `/mdpaper.write-paper` | 0-10（全流程）   |
| `/mdpaper.draft`       | 5 only           |
| `/mdpaper.audit` (NEW) | 6+7（審計+審稿） |
| `/mdpaper.clarify`     | 5 only（潤稿）   |

---

### 2.9 新增 Agent Mode：`paper-reviewer`（D3 — 可直接實作）

唯讀模式，只能讀取草稿、不能修改。
Tools: `read_draft`, `list_drafts`, `count_words`, `check_formatting`, `scan_draft_citations`, `list_assets`, `get_available_citations`, `list_saved_references`, `validate_wikilinks`

**工作流**：Paper Reviewer（唯讀 review）→ 確認問題 → 切回 default → 修正

---

## 3. Pipeline Phase 對齊：11-Phase（0-10）

| Phase | 名稱     | Skill                         | Gate                             |
| ----- | -------- | ----------------------------- | -------------------------------- |
| 0     | 前置規劃 | —                             | journal-profile.yaml 用戶確認    |
| 1     | 專案設置 | project-management            | 專案 + paper_type                |
| 2     | 文獻搜尋 | literature-review             | ≥10 篇                           |
| 3     | 概念發展 | concept-development           | novelty ≥ 75                     |
| 4     | 大綱規劃 | draft-writing                 | 🗣️ 用戶確認 manuscript-plan.yaml |
| 5     | 章節撰寫 | draft-writing + Hook A/B/B7   | 通過                             |
| 6     | 全稿審計 | Hook C（C7 含數量+交叉引用）  | 0 critical                       |
| 7     | 自主審稿 | Review→Response loop (×3)     | quality ≥ threshold              |
| 8     | 引用同步 | reference-management          | 0 broken                         |
| 9     | 匯出     | word-export                   | 已匯出                           |
| 10    | 回顧改進 | Hook D（含 D7 Reviewer 演化） | SKILL 更新                       |

---

## 4. Hook 計數：40 → 42

| Category  | 原先 | 變更              | 新計數 |
| --------- | ---- | ----------------- | ------ |
| A         | 1-4  | 不變              | 4      |
| B         | 1-6  | +B7               | **7**  |
| C         | 1-8  | C7 擴展（不加號） | 8      |
| D         | 1-6  | +D7               | **7**  |
| P         | 1-8  | 不變              | 8      |
| G         | 1-8  | 不變              | 8      |
| **Total** | 40   | +2                | **42** |

傳播清單（5 個檔案）：SKILL.md, AGENTS.md, copilot-instructions.md ×2, VSX SKILL.md

---

## 5. 圖片/圖說處理

### 5.1 來源分類

| 情境              | 處理                                           |
| ----------------- | ---------------------------------------------- |
| Pipeline 自動生成 | `create_plot`/`save_diagram` → `insert_figure` |
| 用戶提供          | 放入 `results/figures/` → `insert_figure` 註冊 |
| 外部文獻          | ⚠️ 不可直接使用                                |
| 外部工具          | Agent 產 script → 用戶執行 → 放入              |

### 5.2 圖說品質

| 元素     | 適用             |
| -------- | ---------------- |
| 編號     | 全部（自動）     |
| 描述句   | 全部             |
| 統計數據 | 統計圖           |
| N 值     | 流程圖/表格      |
| 縮寫定義 | 全部（首次展開） |
| 檢定方法 | 表格             |

### 5.3 Hook 整合

B7d: asset_plan 項目已插入 → B7e: caption_requirements 滿足 → C7a: 數量上限 → C7d: 交叉引用 → Phase 7 Editor 審查

---

## 6. 循環示意圖

```
Phase 4: manuscript-plan.yaml
          │
Phase 5: ╔════════════════════════════════════╗
         ║  write paragraphs                  ║
         ║  Hook A (per-section, ≤3 rounds)   ║
         ║  Hook B + B7 (per-section, ≤2 rds) ║
         ╚════════════════════════════════════╝
          │
Phase 6: ╔════════════════════════════════════╗
         ║  Hook C1-C8 (C7=數量+交叉引用)     ║
         ║  Cascading fix ≤3 rounds           ║
         ╚════════════════════════════════════╝
          │ 0 CRITICAL
Phase 7: ╔════════════════════════════════════╗
         ║  Round 1-3:                        ║
         ║  ① Review Report (YAML front)     ║
         ║  ② Author Response (全 issue)     ║
         ║  ③ patch_draft + Hook A re-run    ║
         ║  ④ quality ≥ threshold → PASS     ║
         ╚════════════════════════════════════╝
          │
Phase 8-9: Ref Sync → Export
          │
Phase 10: Hook D + D7 (Reviewer 演化)
```

---

## 7. 檔案變更清單

| #   | 操作 | 檔案                                            | 內容                                         |
| --- | ---- | ----------------------------------------------- | -------------------------------------------- |
| F1  | 修改 | `.claude/skills/auto-paper/SKILL.md`            | Phase 4 + B7 + D7 + C7 擴展 + Phase 7 結構化 |
| F2  | 修改 | `.github/prompts/mdpaper.write-paper.prompt.md` | 11-Phase 對齊                                |
| F3  | 新增 | `.github/prompts/mdpaper.audit.prompt.md`       | 獨立審計 prompt                              |
| F4  | 新增 | `.github/agents/paper-reviewer.agent.md`        | 唯讀審稿 agent mode                          |
| F5  | 修改 | `templates/journal-profile.template.yaml`       | +tolerance +section_brief +changelog         |
| F6  | 修改 | `AGENTS.md`                                     | Hook 40→42, B1-7, D1-7                       |
| F7  | 修改 | `.github/copilot-instructions.md`               | 同上                                         |
| F8  | 修改 | `vscode-extension/copilot-instructions.md`      | 鏡像                                         |
| F9  | 修改 | `vscode-extension/skills/auto-paper/SKILL.md`   | 鏡像 F1                                      |
| F10 | 修改 | `.github/prompts/_capability-index.md`          | +audit prompt                                |
| F11 | 鏡像 | `vscode-extension/prompts/`                     | 鏡像 F2, F3                                  |

---

## 8. 實作優先級

| #     | 項目                           | 檔案         | 依賴  |
| ----- | ------------------------------ | ------------ | ----- |
| 🔴 P1 | Phase 4 → manuscript-plan.yaml | F1           | —     |
| 🔴 P2 | Hook B7 + C7 擴展 + D7 + 傳播  | F1, F6-F8    | P1    |
| 🔴 P3 | write-paper.prompt.md 11-Phase | F2, F11      | P1    |
| 🟡 P4 | Phase 7 結構化 Review/Response | F1           | —     |
| 🟡 P5 | mdpaper.audit prompt + index   | F3, F10, F11 | P4    |
| 🟡 P6 | journal-profile.yaml 新欄位    | F5           | —     |
| 🟡 P7 | paper-reviewer agent mode      | F4           | —     |
| 🟢 P8 | VSX 全面同步                   | F9           | P1-P7 |

---

## 9. 開放問題（實作中決定）

### OQ1: C6 與 C7c 重疊

C7c 新增字數 vs journal-profile，與 C6 總字數功能重疊。
選項：A) C6 deprecated B) C6 保留快速檢查 + C7c 詳細比對

### OQ2: D7 演化範圍

D7 可更新 Reviewer 指令的哪些部分？

- 角色描述、checklist、threshold 建議值
- 限制：CONSTITUTION §23 L2 級（±20%）
