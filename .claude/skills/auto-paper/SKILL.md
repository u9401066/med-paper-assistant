---
name: auto-paper
description: |
  全自動論文撰寫 + 閉環自我改進系統。
  LOAD THIS SKILL WHEN: 全自動寫論文、auto write、自動撰寫、幫我寫完整篇、autopilot、從頭到尾、一鍵寫論文
  CAPABILITIES: 編排所有研究 Skills + 3 層 Audit Hooks + Meta-Learning 自我改進
---

# 全自動論文撰寫 + 閉環自我改進

## 🔄 閉環架構

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLOSED LOOP SYSTEM                            │
│                                                                  │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐           │
│  │ INSTRUCTION│────→│   SKILL    │────→│  WRITING   │           │
│  │ (AGENTS.md │     │(auto-paper │     │ (drafts/)  │           │
│  │  copilot-  │     │ SKILL.md)  │     │            │           │
│  │  instruct) │     │            │     │            │           │
│  └─────▲──────┘     └─────▲──────┘     └─────┬──────┘           │
│        │                  │                   │                  │
│        │            ┌─────┴───────────────────┘                  │
│        │            │                                            │
│        │      ┌─────▼──────┐                                     │
│        └──────│   HOOKS    │                                     │
│               │ (3-layer   │                                     │
│               │  auditors) │                                     │
│               └────────────┘                                     │
│                                                                  │
│  Hook 不只檢查論文，還檢查 Skill 和 Instruction 本身             │
│  發現問題 → 更新論文 / 更新 SKILL / 更新 Hook 自身 → 閉環       │
└─────────────────────────────────────────────────────────────────┘
```

**核心設計理念**（CONSTITUTION §22）：

> **可審計、可拆解、可重組** — 論文講究的是再現性與方法學，不是文字用詞藝術。

| 原則 | 意義 | 實現方式 |
|------|------|----------|
| **可審計** | 從任何一句話追溯到決策和證據 | `.audit/` 執行紀錄 |
| **可拆解** | Phase 獨立執行，Hook 獨立觸發 | 輸入/輸出都是檔案 |
| **可重組** | Phase 順序可調，Hook 可增減 | 編排器模式 |

**四個審計維度**：

| 維度 | 檢查什麼 | 更新什麼 |
|------|----------|----------|
| **Paper Hooks** | 論文品質（引用、字數、Anti-AI） | `patch_draft` 修正論文 |
| **Methodology Hooks** | 方法學可再現性、統計匹配 | 補充方法學細節 |
| **Compliance Hooks** | Agent 是否遵循 Skill 流程 | `.memory/` 記錄偏差 |
| **Meta Hooks** | Skill、Hook、Instruction 是否需改進 | 更新 SKILL/Hook/AGENTS |

---

## 📋 執行審計軌跡（Audit Trail）

> **CONSTITUTION §20**：Pipeline 每步都產出結構化審計紀錄。

每次 Pipeline 執行，在 `projects/{slug}/.audit/` 產出：

```
.audit/
├── pipeline-run-{timestamp}.md    ← 完整執行紀錄
├── search-strategy.md             ← 搜尋策略和結果
├── reference-selection.md         ← 文獻篩選決策
├── concept-validation.md          ← Novelty 驗證過程
├── hook-effectiveness.md          ← Hook 觸發統計
└── quality-scorecard.md           ← 品質計分卡
```

### pipeline-run 格式：

```markdown
# Pipeline Execution: {project_name}
- Started: {timestamp}
- Completed: {timestamp}
- Total phases: 9
- Human intervention points: {count}

## Phase Summary
| Phase | Status | Duration | Inputs | Outputs | Issues |
|-------|--------|----------|--------|---------|--------|
| 1 | ✅ | - | user_topic | project created | - |
| 2 | ✅ | - | search queries ×5 | 18 refs saved | expanded 1x |
| ... | ... | ... | ... | ... | ... |

## Hook Audit
| Hook | Triggers | Pass | Fail→Fix | Fail→Skip |
|------|----------|------|----------|-----------|
| A1 word_count | 4 | 3 | 1 | 0 |
| A2 citations | 4 | 2 | 2 | 0 |
| B5 methodology | 1 | 0 | 1 | 0 |
| ... | ... | ... | ... | ... |

## Decision Log
| Decision | Alternatives | Reason | Evidence |
|----------|-------------|--------|----------|
| 選擇 STROBE checklist | CONSORT, CARE | 觀察性研究 | concept.md study_design |
| 移除 ref_123 | 保留 | RCR < 0.5, 非核心 | citation_metrics |
```

### quality-scorecard 格式：

```markdown
# Quality Scorecard

## 方法學分數（Methodology Score）
| 項目 | 分數(0-10) | 備註 |
|------|-----------|------|
| 研究設計描述 | ? | 待 Hook B5 評分 |
| 統計方法匹配 | ? | 待 Hook B5 評分 |
| 變項定義明確 | ? | 待 Hook B5 評分 |
| 樣本量合理性 | ? | 待 Hook B5 評分 |
| 結局指標預定義 | ? | 待 Hook B5 評分 |
| EQUATOR 合規 | ? | 待 Hook B5 評分 |

## 文字品質分數（Writing Score）
| 項目 | 分數 | 備註 |
|------|------|------|
| Anti-AI 乾淨度 | Hook A3 結果 | |
| 引用密度 | Hook A2 結果 | |
| 概念一致性 | Hook B1 結果 | |
| 全稿一致性 | Hook C1 結果 | |
```

---

## 🔄 Pipeline Recovery（斷點恢復）

> **CONSTITUTION §22**：Pipeline 可從任何 Phase 恢復（Checkpoint 機制）。

每個 Phase 完成後，狀態寫入 `.audit/checkpoint.json`：

```json
{
  "project": "my-study",
  "last_completed_phase": 5,
  "last_completed_section": "Methods",
  "timestamp": "2026-02-20T10:30:00",
  "phase_outputs": {
    "1": { "project_slug": "my-study", "paper_type": "original-research" },
    "2": { "refs_saved": 18, "search_queries": ["q1", "q2", "q3"] },
    "3": { "concept_score": 82, "validation_rounds": 1 },
    "4": { "outline_approved": true },
    "5": { "sections_done": ["Methods"], "sections_pending": ["Results", "Introduction", "Discussion"] }
  }
}
```

**恢復邏輯**：
```
Agent 偵測到 .audit/checkpoint.json 存在：
1. 讀取 last_completed_phase
2. 詢問用戶：「上次在 Phase {N}（{section}）中斷，要從 Phase {N+1} 繼續嗎？」
3. 用戶確認 → 跳過已完成的 Phase
4. 用戶說重來 → 清除 checkpoint，從頭開始
```

---

## 🔔 雙重 Hook 系統

本系統使用**兩種 Hook**，分別在不同時機觸發，共同確保品質：

```
┌──────────────────────────────────────────────────────────────────┐
│                      DUAL HOOK SYSTEM                            │
│                                                                  │
│  ┌─── Copilot Hooks (寫作時) ───┐  ┌─── Pre-Commit Hooks ────┐  │
│  │ A: post-write    → 即時修正  │  │ P1: citation-integrity  │  │
│  │ B: post-section  → 概念一致  │  │ P2: anti-ai-scan        │  │
│  │ C: post-manuscript→ 全稿審計 │  │ P3: concept-alignment   │  │
│  │ D: meta-learning → 自我改進  │  │ P4: word-count          │  │
│  │                              │  │ P5: protected-content   │  │
│  │ 定義：本 SKILL (auto-paper)  │  │ P6: memory-sync         │  │
│  │ 時機：Phase 5-9 自動觸發     │  │ P7: reference-integrity │  │
│  │ 對象：每次寫作操作           │  │ P8: methodology-valid.  │  │
│  └──────────────────────────────┘  │ 定義：git-precommit     │  │
│                                    │ 時機：git commit 前      │  │
│                                    │ 對象：已變更的論文檔案   │  │
│                                    └─────────────────────────┘  │
│                                                                  │
│  💡 Copilot Hooks = 即時品質控制（邊寫邊查）                      │
│  💡 Pre-Commit Hooks = 最終品質把關（提交前總檢查）               │
│  💡 兩者互補：Copilot 處理細節，Pre-Commit 處理全局               │
└──────────────────────────────────────────────────────────────────┘
```

**👉 Pre-Commit Hooks 的完整定義見**：`.claude/skills/git-precommit/SKILL.md`

---

## 🚀 9-Phase Pipeline

### Phase 1: PROJECT SETUP ⚙️
**Skill**: `project-management`

```
1. get_current_project() → 有專案？切換：建立
2. create_project(name, paper_type) 或 switch_project(slug)
3. setup_project_interactive() → 設定 paper type
```

**Gate**: ✅ 專案存在且 paper_type 已設定

---

### Phase 2: LITERATURE SEARCH 🔍
**Skill**: `literature-review`, `parallel-search`

```
1. generate_search_queries(topic, strategy="comprehensive")
2. 並行 search_literature() × 3-5 組
3. merge_search_results()
4. get_citation_metrics(sort_by="relative_citation_ratio")
5. 選前 15-20 篇 → save_reference_mcp(pmid, agent_notes)
```

**Gate**: ✅ ≥10 篇文獻已儲存

**自動決策邏輯**：
- 結果 <20 → `expand_search_queries` 再搜
- 結果 >500 → 加 MeSH 限縮
- RCR 排序取 top papers

---

### Phase 3: CONCEPT DEVELOPMENT 📐
**Skill**: `concept-development`

```
1. 分析 saved references → 識別 Gap
2. 撰寫 concept.md（含 🔒 NOVELTY + 🔒 SELLING POINTS）
3. write_draft(filename="concept.md", content=..., skip_validation=True)
4. validate_concept(project=...)
5. IF score < 75:
   ├── 自動修正 1 次（只改最關鍵的 1 點）
   ├── 再驗證
   └── IF 仍 < 75 → 🔴 STOP，回報用戶
```

**Gate**: ✅ concept score ≥ 75 OR 用戶明確說「繼續」

---

### Phase 4: MANUSCRIPT PLANNING 📋 (關鍵新增)

```
1. 讀取 concept.md + saved references + paper_type
2. 產出段落級大綱：

   outline = {
     "Introduction": [
       { "para": 1, "topic": "Clinical reality of X",
         "words": 150, "refs": ["author2024_123"], "claims": [...] },
       { "para": 2, "topic": "Current evidence on Y", ... },
       ...
     ],
     "Methods": [...],
     "Results": [...],
     "Discussion": [...]
   }

3. 🗣️ 呈現大綱給用戶（Pipeline 中唯一的確認點）
4. 用戶可調整 → 確認 → 儲存到 .memory/
```

**Gate**: ✅ 大綱已確認

**寫作順序**（依 paper type）：

| Paper Type | 建議順序 |
|------------|----------|
| original-research | Methods → Results → Introduction → Discussion → Abstract |
| systematic-review | Methods → Results → Discussion → Introduction → Abstract |
| case-report | Case Presentation → Discussion → Introduction → Abstract |

---

### Phase 5: SECTION WRITING ✍️ (核心 + Audit Loop)
**Skill**: `draft-writing`

```
FOR section IN writing_order:
  1. 讀取 outline[section]
  2. 讀取所有已完成 sections（全局 context）
  3. get_available_citations() → 取得可用引用
  4. draft_section(topic=section, notes=outline_context)
     或 write_draft(filename=..., content=...)

  5. ═══════════════════════════════════════════
     🔔 HOOK A: post-write (見下方 Hook 定義)
     ═══════════════════════════════════════════

  6. IF Hook A 報告 issues:
     ├── patch_draft() 修正（最多 2 rounds）
     └── 重跑 Hook A 確認修正

  7. ═══════════════════════════════════════════
     🔔 HOOK B: post-section (見下方 Hook 定義)
     ═══════════════════════════════════════════

  8. Log 到 .memory/progress.md
```

---

### Phase 6: CROSS-SECTION AUDIT 🔎

```
1. ═══════════════════════════════════════════
   🔔 HOOK C: post-manuscript (見下方 Hook 定義)
   ═══════════════════════════════════════════

2. IF critical issues found:
   ├── 定點 patch_draft 修正
   └── 重跑 Hook C（最多 2 rounds）

3. Log audit results
```

**Gate**: ✅ 0 critical issues（warnings 可接受）

---

### Phase 7: REFERENCE SYNC 📚

```
1. sync_references(filename=manuscript) → 生成 References section
2. 確認所有 [[wikilinks]] 已解析
3. format_references(style=journal_style)
```

**Gate**: ✅ 所有引用已解析，0 個 broken links

---

### Phase 8: EXPORT 📄
**Skill**: `word-export`（或未來 Pandoc）

```
1. list_templates() → 選擇 template
2. start_document_session()
3. FOR section IN sections: insert_section()
4. verify_document(limits_json=journal_limits)
5. save_document(output_filename=...)
```

**Gate**: ✅ Word 檔已匯出

---

### Phase 9: RETROSPECTIVE 🔄 (閉環核心)

```
═══════════════════════════════════════════
🔔 HOOK D: meta-learning (見下方 Hook 定義)
═══════════════════════════════════════════

1. 回顧執行紀錄（.memory/activeContext.md）
2. 分析 Hook 觸發統計
3. 更新 SKILL.md「Lessons Learned」
4. 更新 AGENTS.md（如適用）
5. 更新 .memory/ 完整紀錄
```

---

## 🔔 Copilot Hooks 定義（寫作時觸發）

> **這些是 Copilot Hooks**，在 auto-paper Pipeline 的 Phase 5-9 期間由 Agent 自動執行。
> Pre-Commit Hooks 見 `.claude/skills/git-precommit/SKILL.md`。

### Hook A: post-write（每次寫完立即觸發）

| # | 檢查項 | MCP Tool | 失敗行為 |
|---|--------|----------|----------|
| A1 | 字數在 target ±20% | `mcp_mdpaper_count_words(filename=...)` | `mcp_mdpaper_patch_draft()` 精簡/擴充 |
| A2 | 引用密度達標 | `mcp_mdpaper_get_available_citations()` | `mcp_mdpaper_suggest_citations()` + `mcp_mdpaper_patch_draft()` |
| A3 | 無 Anti-AI 模式 | `mcp_mdpaper_read_draft()` + Agent 掃描 | `mcp_mdpaper_patch_draft()` 改寫 |
| A4 | Wikilink 格式正確 | `mcp_mdpaper_validate_wikilinks()` | 自動修復 |

**A1 執行範例**：
```python
result = mcp_mdpaper_count_words(filename="drafts/introduction.md")
target = outline["Introduction"]["target_words"]  # e.g., 500
if abs(result.words - target) / target > 0.20:
    mcp_mdpaper_patch_draft(
        filename="introduction.md",
        old_text=..., new_text=...  # 精簡或擴充
    )
```

**A2 引用密度標準**：

| Section | 最低密度 |
|---------|----------|
| Introduction | ≥1 citation / 100 words |
| Methods | ≥0（引用方法學文獻即可） |
| Results | ≥0（通常不引用） |
| Discussion | ≥1 citation / 150 words |

**A3 Anti-AI 禁止詞**（`read_draft` 後 Agent 掃描）：
```
❌ "In recent years" → ✅ 具體年份或事件
❌ "It is worth noting" → ✅ 直述
❌ "Furthermore" (段首) → ✅ 邏輯連接詞
❌ "plays a crucial role" → ✅ 具體描述
❌ "has garnered significant attention" → ✅ 數據說話
❌ "a comprehensive understanding" → ✅ 具體內容
❌ "This groundbreaking" → ✅ 客觀描述
```

---

### Hook B: post-section（一個 section 完成後）

| # | 檢查項 | MCP Tool | 失敗行為 |
|---|--------|----------|----------|
| B1 | 與 concept.md 一致 | `mcp_mdpaper_read_draft(filename="concept.md")` + Agent 比對 | 重寫不一致段落 |
| B2 | 🔒 NOVELTY 在 Intro 體現 | `mcp_mdpaper_read_draft()` 檢查關鍵詞 | `mcp_mdpaper_patch_draft()` 加入 |
| B3 | 🔒 SELLING POINTS 在 Discussion | 逐條比對 | `mcp_mdpaper_patch_draft()` 補充 |
| B4 | 與已寫 sections 不矛盾 | `mcp_mdpaper_read_draft()` 交叉比對 | 修正矛盾處 |
| B5 | 方法學可再現性 | Agent 依 paper_type 評估（見下方） | `mcp_mdpaper_patch_draft()` 補細節 |
| B6 | 寫作順序驗證 | `mcp_mdpaper_check_writing_order()` | ⚠️ Advisory 警告（不阻擋）|

**B1 執行範例**：
```python
concept = mcp_mdpaper_read_draft(filename="concept.md")
section = mcp_mdpaper_read_draft(filename="drafts/introduction.md")
# Agent 提取 concept 的 Research Question、NOVELTY、SELLING POINTS
# Agent 在 section 中搜尋對應概念
# 若偏離 → patch_draft 修正
```

#### Hook B5: 方法學驗證（Methodology Validation）

> **CONSTITUTION §21**：Methods 必須可被第三方重現。

**觸發時機**：Methods section 完成後立即執行。

**B5 Checklist（按 paper_type 選擇性啟用）**：

| 檢查項 | Original Research | Case Report | Systematic Review | 評分(0-10) |
|--------|:-:|:-:|:-:|:-:|
| 研究設計明確描述 | ✅ | ✅ | ✅ | Agent 評估 |
| 主要/次要結局預定義 | ✅ | ⬜ | ✅ | Agent 評估 |
| 樣本量/power 計算 | ✅ | ⬜ | ⬜ | Agent 評估 |
| 納入/排除標準明確 | ✅ | ⬜ | ✅ | Agent 評估 |
| 統計方法匹配研究設計 | ✅ | ⬜ | ✅ | Agent 評估 |
| 變項操作型定義 | ✅ | ✅ | ⬜ | Agent 評估 |
| 倫理審查聲明 | ✅ | ✅ | ⬜ | Agent 評估 |
| 資料收集期間描述 | ✅ | ✅ | ✅ | Agent 評估 |
| EQUATOR Checklist 對應 | CONSORT(RCT)/STROBE(觀察性) | CARE | PRISMA | 有/無 |
| Discussion 限制段落 | ✅ | ✅ | ✅ | Agent 評估 |

**B5 執行邏輯**：
```
1. 讀取 concept.md → 確認 paper_type、study_design
2. 選擇對應 checklist（上表）
3. 讀取 Methods + Discussion draft
4. Agent 逐項評估，產出 0-10 分
5. 寫入 .audit/quality-scorecard.md

IF 任何必選項 < 5 分：
  → patch_draft 補充缺失描述
  → 再次評估
  → 2 rounds 後仍 < 5 → 標記為人工介入點

IF EQUATOR checklist 未覆蓋：
  → 產出建議的 checklist 項目供用戶參考
```

#### Hook B6: 寫作順序驗證（Writing Order Validation）

> **CONSTITUTION §22**：Phase 順序可調整，但 Agent 應主動提醒。

**觸發時機**：每個 section 開始撰寫前。

**B6 執行邏輯**：
```
1. mcp_mdpaper_check_writing_order() → 取得當前進度
2. 檢查 target section 的前置條件是否已完成
3. IF 前置 section 未完成：
   → 顯示 ⚠️ Advisory 警告（不阻擋）
   → 告知用戶缺少哪些 section
   → 提供選項：(a) 先完成前置 (b) 忽略繼續
4. 記錄到 .audit/ 審計軌跡
```

**寫作順序規則**（per paper_type）：

| Paper Type | 建議順序 |
|------------|----------|
| original-research | Methods → Results → Introduction → Discussion → Conclusion → Abstract |
| systematic-review | Methods → Results → Discussion → Introduction → Conclusion → Abstract |
| case-report | Case Presentation → Discussion → Introduction → Conclusion → Abstract |
| review-article | Introduction → Body → Conclusion → Abstract |

**前置條件表**：

| Target Section | 前置條件 | 原因 |
|----------------|----------|------|
| Results | Methods | Results 描述 Methods 定義的結局指標 |
| Discussion | Results, Introduction | Discussion 討論 Results 並回應 Introduction 的研究問題 |
| Conclusion | Discussion | Conclusion 是 Discussion 的總結 |
| Abstract | 所有主體 section | Abstract 摘錄所有 section 的精華 |

**⚠️ Advisory, Not Blocking**：
- 此 Hook 產生 warning，不阻止寫作（遵循 §22 可重組原則）
- 但審計軌跡會記錄是否跳過了建議順序
- Hook D 可根據跳過率決定是否調整閾值

---

### Hook C: post-manuscript（全稿完成後）

| # | 檢查項 | MCP Tool | 失敗行為 |
|---|--------|----------|----------|
| C1 | 稿件一致性 | `mcp_mdpaper_check_formatting(check_type="consistency")` | 定點 `mcp_mdpaper_patch_draft()` |
| C2 | 投稿清單 | `mcp_mdpaper_check_formatting(check_type="submission")` | 定點修正 |
| C3 | N 值跨 section 一致 | `mcp_mdpaper_read_draft()` × N + Agent 數字比對 | `mcp_mdpaper_patch_draft()` 統一 |
| C4 | 縮寫首次定義 | `mcp_mdpaper_read_draft()` + Agent 全文掃描 | `mcp_mdpaper_patch_draft()` 補定義 |
| C5 | 所有 wikilinks 可解析 | `mcp_mdpaper_scan_draft_citations()` | `mcp_mdpaper_save_reference_mcp()` 補存 |
| C6 | 總字數合規 | `mcp_mdpaper_count_words()` | 精簡超長 section |

---

### Hook D: meta-learning（閉環自我改進）

**⚠️ 此 Hook 是閉環的核心，在 Phase 9 執行。**
**⚠️ Hook D 不只改進 SKILL — 它改進 Hook 自身（CONSTITUTION §23）。**

#### Step D1: 執行回顧 + 效能統計

```
讀取 .memory/activeContext.md
讀取 .audit/pipeline-run-{latest}.md

統計：
- 各 Hook 觸發次數 / 通過次數 / 修正次數
- 哪些 section 修改最多次
- 哪些 audit 項目失敗率最高
- 是否有人工介入點
- B5 方法學各項平均分數

產出 Hook 效能報告：
```

**Hook 效能報告格式**（寫入 `.audit/hook-effectiveness.md`）：

| Hook | 觸發次數 | 通過率 | 修正成功率 | 誤報率 | 趨勢 | 閾值調整建議 |
|------|---------|--------|-----------|--------|------|-------------|
| A1 word_count | 4 | 75% | 100% | 0% | → | 維持 |
| A2 citations | 4 | 50% | 100% | 0% | → | 維持 |
| A3 anti_ai | 4 | 100% | - | - | → | 維持 |
| B5 methodology | 1 | 0% | 100% | 0% | → | 新 Hook，待觀察 |
| P2 anti_ai_scan | 1 | 100% | - | - | → | 維持 |

**效能判斷規則**（CONSTITUTION §23）：
```
IF hook.trigger_rate > 80%:
  → 建議：「Hook 太嚴格，閾值需放寬」
  → 例：「Anti-AI 禁止了 80% 的段落 → 某些詞可能不該禁」

IF hook.trigger_rate < 5% (超過 5 次 pipeline 執行)：
  → 建議：「Hook 太鬆或已過時，考慮移除或合併」
  → 例：「P5 protected_content 從未觸發 → Agent 已學會不碰 🔒」

IF hook.false_positive_rate > 30%:
  → 建議：「Hook 判斷標準需修正」
  → 例：「A3 把 'comprehensive' 誤判為 AI 詞 → 移出禁止清單」
```

#### Step D2: 論文層面改進（已在 Phase 5-6 完成）

#### Step D3: Hook 自我改進（Hook 改 Hook）

> **這是 §23 的核心實作：Hook D 不只記錄經驗，還修改 Hook 定義。**

```
基於 D1 的效能報告：

=== 自動調整（不需用戶確認）===

IF Anti-AI 禁止詞產生誤報:
  → 從 Hook A3 / P2 的禁止詞清單移除該詞
  → 記錄：「移除 'comprehensive'，因連續 3 次被標記但實為合理用語」

IF 引用密度閾值不合理:
  → 調整 Hook A2 的密度閾值（±20% 範圍內）
  → 例：「Introduction 引用密度 target 從 2/para 調整為 1.5/para」

IF 字數限制需微調（±10% 範圍）:
  → 調整 Hook A1 目標字數
  → 例：「Discussion 從 1500 調整為 1650（paper_type: original-research）」

IF B5 方法學某項持續 >8 分:
  → 降低該項檢查頻率（從 every-section 降為 post-manuscript）

=== 需要用戶確認 ===

IF 建議新增 Hook 項目:
  → 提出建議：「發現 Results 常出現未定義縮寫，建議新增 Hook A5: abbreviation_check」
  → 用戶確認後，寫入 SKILL.md 的 Hook A 表格

IF 建議移除/合併 Hook:
  → 提出建議：「P5 protected_content 過去 5 次從未觸發，建議移除」
  → 用戶確認後，從 SKILL.md 移除

IF 建議修改 Hook 判斷邏輯（非閾值）:
  → 提出具體方案，由用戶決定

=== 禁止修改 ===
  ❌ 不改 CONSTITUTION 原則
  ❌ 不改 🔒 保護內容規則
  ❌ 不改 save_reference_mcp 優先規則
  ❌ 不改 Hook D 自身的改進邏輯
```

#### Step D4: SKILL 層面改進

```
讀取當前 auto-paper/SKILL.md
比對執行紀錄，識別：

IF 某 Hook 項目觸發 >2 次同類問題:
  → 在 SKILL.md 的 Hook 表格加入新的 pre-check
  → 例：「Discussion 總是超字數」→ 加入 Hook A 的字數 target 調整

IF 某 Phase 被跳過或始終不需要:
  → 在 SKILL.md 標記為 OPTIONAL

IF 發現新的 Anti-AI 模式:
  → 加入 Hook A 的禁止詞清單（D3 自動調整）

IF 引用密度標準不合理:
  → 調整 Hook A 的密度閾值（D3 自動調整）

用 replace_string_in_file 更新 SKILL.md
→ 更新「Lessons Learned」區塊、Hook 表格、Hook 閾值
```

#### Step D5: INSTRUCTION 層面改進

```
讀取 AGENTS.md 和 copilot-instructions.md
比對執行紀錄，識別：

IF auto-paper 觸發語不夠 → 更新 AGENTS.md skill 表格觸發語
IF 流程有重大變更 → 更新 write-paper.prompt.md
IF 發現 Instruction 與 Skill 不一致 → 同步修正

⚠️ Instruction 更新需慎重：
  - 只更新觸發語、Skill 描述等「事實性」內容
  - 不改核心原則（如 MCP-to-MCP、檔案保護規則）
  - 更新後記錄到 memory-bank/decisionLog.md
```

#### Step D6: 記錄 + 審計軌跡

```
更新：
- projects/{slug}/.audit/hook-effectiveness.md — Hook 效能統計
- projects/{slug}/.audit/quality-scorecard.md — 品質計分卡
- projects/{slug}/.memory/progress.md — 完整執行紀錄
- projects/{slug}/.memory/activeContext.md — Agent 觀察
- memory-bank/decisionLog.md — 重大改進決策
- auto-paper/SKILL.md「Lessons Learned」— 累積經驗
```

---

## ⚡ 自動決策邏輯（何時不問用戶）

| 情境 | 自動行為 | 停下來的條件 |
|------|----------|-------------|
| 搜尋結果不足 | 自動擴展搜尋 | 3 輪擴展後仍 <10 篇 |
| Concept score 65-74 | 自動修正 1 次 | 修正後仍 <75 |
| Hook A 字數超標 | 自動 patch_draft 精簡 | 2 rounds 後仍超標 |
| Hook A 引用不足 | 自動 suggest + patch | 無可用引用可補 |
| Hook B 🔒 缺失 | 自動 patch 加入 | 需要改研究方向 |
| Hook B5 方法學 <5 分 | 自動 patch 補細節 | 2 rounds 後仍 <5 |
| Hook C 數字不一致 | 自動修正到最新數字 | 不確定哪個是正確的 |
| Hook D 閾值微調 | 自動調整±20% | 超出±20% 範圍 |
| Hook D 新增/移除 Hook | 提出建議 | 永遠需用戶確認 |
| SKILL 需更新 | 自動更新 Lessons Learned | 要改 Hook 閾值超出自動範圍 |

**🔴 必須停下來問用戶的情況**：
- Concept score < 60（兩次修正後仍低）
- Phase 4 大綱需要 approve
- 任何涉及研究方向改變的決策
- 3 rounds 修正後 Hook 仍失敗
- 要修改 AGENTS.md 核心原則

---

## 📊 執行紀錄格式

Phase 5 期間，每個 section 完成後記錄到 `.memory/activeContext.md`：

```markdown
## Auto-Paper Execution Log

### Section: Introduction
- Status: ✅ Complete
- Rounds: 2 (1 revision for citation density)
- Hook A: word_count ✅ | citations ⚠️→✅ | anti_ai ✅ | wikilinks ✅
- Hook B: concept_align ✅ | novelty ✅ | selling_pts N/A | coherence ✅
- Word count: 458 (target: 400-600)
- Citations: 8

### Section: Methods
- Status: ✅ Complete
- Rounds: 1 (no revision needed)
- ...
```

---

## 🧪 Lessons Learned（自動更新區）

> ⚠️ 此區塊由 Hook D (meta-learning) 自動更新。
> Agent 在 Phase 9 回顧後，將發現記錄在此。
> 格式：`[日期] [專案] 發現內容`

_尚無記錄。首次全自動執行後將自動填入。_

---

## 📋 Skill 依賴關係

```
auto-paper（本 Skill = 編排器）
  ├── project-management     → Phase 1
  ├── literature-review      → Phase 2
  ├── parallel-search        → Phase 2
  ├── concept-development    → Phase 3
  ├── draft-writing          → Phase 4, 5
  ├── reference-management   → Phase 7
  ├── word-export            → Phase 8
  └── submission-preparation → Phase 8 (cover letter 等)
```

---

## 🔗 閉環檢查清單

Pipeline 結束前，確認閉環完整性：

- [ ] 論文所有 section 都通過 Hook A + B
- [ ] 全稿通過 Hook C
- [ ] .memory/ 已更新執行紀錄
- [ ] Hook D meta-learning 已執行
- [ ] SKILL.md Lessons Learned 已更新
- [ ] AGENTS.md 描述與實際流程一致（如不一致則更新）
- [ ] Word 檔已匯出
