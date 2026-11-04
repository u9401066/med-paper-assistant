---
name: auto-paper
description: |
  全自動論文撰寫 + 閉環自我改進系統。
  LOAD THIS SKILL WHEN: 全自動寫論文、auto write、自動撰寫、幫我寫完整篇、autopilot、從頭到尾、一鍵寫論文
  CAPABILITIES: 編排所有研究 Skills + 3 層 Audit Hooks + Meta-Learning 自我改進
---

# 全自動論文撰寫 + 閉環自我改進

## 閉環架構

Instructions (AGENTS.md) → Skill (auto-paper) → Writing (drafts/) → Hooks (audit) → 回頭更新 Skill/Instructions

核心理念（CONSTITUTION §22）：可審計、可拆解、可重組。詳見 AGENTS.md。

四個審計維度：

| 維度        | 檢查                   | 更新對象                                |
| ----------- | ---------------------- | --------------------------------------- |
| Paper       | 引用、字數、Anti-AI    | `draft_action(action="patch")` 修正論文 |
| Methodology | 方法學可再現性         | 補充方法學細節                          |
| Compliance  | Agent 是否遵循流程     | `.memory/` 記錄偏差                     |
| Meta        | Skill/Hook/Instruction | 更新 SKILL/Hook/AGENTS                  |

---

## 執行審計軌跡（Audit Trail）

每次執行在 `projects/{slug}/.audit/` 產出：

| 檔案                     | 內容                                              |
| ------------------------ | ------------------------------------------------- |
| `pipeline-run-{ts}.md`   | Phase 摘要 + Hook 統計 + Decision Log             |
| `search-strategy.md`     | 搜尋策略和結果                                    |
| `reference-selection.md` | 文獻篩選決策                                      |
| `concept-validation.md`  | Novelty 驗證過程                                  |
| `hook-effectiveness.md`  | Hook 觸發率/通過率/誤報率                         |
| `quality-scorecard.md`   | 方法學 + 文字品質（0-10 分）                      |
| `checkpoint.json`        | 斷點恢復：`last_completed_phase`, `phase_outputs` |

恢復邏輯：偵測 checkpoint.json → 詢問從 Phase N+1 繼續或重來。

> 各 Phase 完成時 `.audit/` 產物的生成規格與 Checkpoint 恢復機制 → [references/audit-trail-and-checkpoints.md](references/audit-trail-and-checkpoints.md)

---

## 雙重 Hook 系統

Copilot Hooks（A-D，寫作時即時修正）定義於 `references/`：A/B → [references/hooks-a-b-post-write-section.md](references/hooks-a-b-post-write-section.md)、C → [references/hooks-c-post-manuscript.md](references/hooks-c-post-manuscript.md)、D → [references/hooks-d-meta-learning.md](references/hooks-d-meta-learning.md)；Hook E（EQUATOR）→ [references/phase-7-equator-hook-e.md](references/phase-7-equator-hook-e.md)。
Pre-Commit Hooks（P1-P8 + G1-G7）定義於 `git-precommit/SKILL.md`。
兩者互補：Copilot 處理細節，Pre-Commit 處理全局。

---

## 🚧 Hard Gate Enforcement（Code-Level，不可跳過）

> SKILL.md 是 soft constraint（Agent 可能忽略）。以下 MCP Tools 是 **code-enforced hard limits**。

### 必要 MCP Tool 呼叫

| 時機                      | MCP Tool                                                               | 說明                                                                                                             |
| ------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| 每個 Phase 完成後         | `pipeline_action(action="validate_phase", phase=...)`                  | 返回 PASS/FAIL + 缺少的 artifact，FAIL 則禁止進入下一 Phase                                                      |
| Phase 7 每輪開始          | `pipeline_action(action="start_review")`                               | 啟動 AutonomousAuditLoop 狀態機，返回 round context                                                              |
| Phase 7 每輪結束          | `pipeline_action(action="submit_review", scores=...)`                  | 提交分數，返回 verdict (CONTINUE/QUALITY_MET/MAX_ROUNDS/REWRITE_NEEDED)                                          |
| Phase 7 需要大幅重寫      | `pipeline_action(action="rewrite_section", sections=..., reason=...)`  | 回退到 Phase 5 重寫指定 section，最多 2 次回退                                                                   |
| Phase 5 每 section 完成後 | `pipeline_action(action="approve_section", section=..., decision=...)` | Autopilot: Agent 自我審閱後自動 approve。手動: 用戶審閱 → approve 或 revise。Phase 5 gate 要求全部 approved      |
| 用戶要求暫停時            | `pipeline_action(action="pause", reason=...)`                          | 暫停 pipeline，記錄 draft hash 以偵測用戶編輯                                                                    |
| 暫停後恢復                | `pipeline_action(action="resume")`                                     | 恢復 pipeline，偵測用戶修改並建議重新驗證                                                                        |
| Pipeline 中途任意時刻     | `pipeline_action(action="heartbeat")`                                  | 返回全 Phase 狀態 + 剩餘工作項，Agent 無法自稱 "done"                                                            |
| Agent 需要一次總檢查時    | `pipeline_action(action="doctor")`                                     | 返回 11-phase readiness、外部 MCP 宣告/command 可用性、最近 gate cache                                           |
| Phase 5 每次 Hook 評估後  | `record_hook_event(hook_id, event_type)`                               | 記錄 A/B/C/E Hook 的 trigger/pass/fix/false_positive，Phase 6 gate 會驗證有實際記錄                              |
| Phase 6 之前（審計階段）  | `run_quality_checks(action="quality_audit", scores=...)`               | 設定 ≥4 維度品質分數 + 產生 scorecard/hook-effectiveness 報告，Phase 6 gate 驗證分數數據                         |
| Phase 10 之前（自我改進） | `run_quality_checks(action="meta_learning")`                           | 執行 D1-D9 分析 + 寫入 meta-learning-audit.yaml / meta-learning-feedback.yaml，Phase 10 gate 驗證 analysis_steps |

### 強制執行規則

1. **Phase 轉換**：Agent MUST call `pipeline_action(action="validate_phase", phase=N)` 且收到 PASS，才能開始 Phase N+1
2. **Phase 7 Review Loop**：Agent MUST call `pipeline_action(action="start_review")` 開始、`pipeline_action(action="submit_review", scores=...)` 結束。不可跳過輪次
3. **Pipeline 完成**：Agent MUST call `pipeline_action(action="heartbeat")` 確認 completion = 100% 才能宣稱完成
4. **所有 gate 結果自動記錄**到 `.audit/gate-validations.jsonl`，可供 Phase 10 D-Hook 分析
5. **專案結構驗證**：`validate_project_structure()` 可獨立於 pipeline 呼叫，用於檢查新/既存專案結構完整性
6. **Phase > 1 自動前提檢查**：`pipeline_action(action="validate_phase", phase=...)` 在 Phase > 1 時會自動檢查前置 Phase 的關鍵 artifacts（WARNING 級別）
7. **審計數據強制**：Phase 6 gate 不只檢查報告檔案存在，還驗證 quality-scorecard.yaml（≥4 維度、avg > 0）和 hook-effectiveness.yaml（≥1 hook 有事件記錄）
8. **自我改進數據強制**：Phase 10 gate 驗證 meta-learning-audit.yaml 有完整分析記錄（analysis_steps D1-D9、adjustments_count、lessons_count、suggestions_count 與 count/list 一致性），並產出 meta-learning-feedback.yaml 供下一輪 Agent 直接接續

### 🛡️ Anti-Compaction 恢復協議

Context compaction 會導致 Agent 遺失 pipeline 進度與寫作狀態。以下防線自動保護：

**第一層：Pipeline 狀態自動寫入**

- 所有 gate tools（`pipeline_action(action="validate_phase")`, `pipeline_action(action="heartbeat")`, `pipeline_action(action="start_review")`, `pipeline_action(action="submit_review")`）
  完成後自動寫入 `projects/{slug}/.mdpaper-state.json` 的 `pipeline_state` 欄位
- 不需要 Agent 額外操作

**第二層：寫作進度自動寫入（✍️ Writing Session Checkpoint）**

- `draft_action(action="write")` 和 `draft_action(action="patch")` 成功後，自動寫入 `writing_session` 欄位
- 記錄：當前 section、檔名、操作類型、字數、所有已存在 section 列表
- 不需要 Agent 額外操作

**第三層：Agent 主動詳細檢查點**

- 使用 `workspace_state_action(action="checkpoint", section=..., plan=..., notes=..., references_in_use=...)` 儲存推理狀態
- **建議時機**：每個段落開始前、切換 section 前、引用大量文獻時
- 儲存：寫作大綱、風格決策、正在使用的引用 key、Agent 的思考筆記
- 此工具呼叫輕量，不影響寫作流程

**第四層：自動恢復**

- `workspace_state_action(action="get")` 讀取 per-project state → `get_recovery_summary()` 產出 banner
- Pipeline banner：current phase, round, gate result, next action, failures
- Writing session banner（✍️）：current section, file, word count, agent context, sections on disk
- 恢復後使用 `draft_action(action="read")` 讀回草稿內容即可繼續

**第五層：Agent 強制規則**

- **對話開始**（或 context compaction 後首次回應）→ MUST call `workspace_state_action(action="get")`
- 如果 pipeline_state.is_active == true → 直接從 recovery summary 指示的 Phase/Round 繼續
- 如果 writing_session.active == true → 用 `draft_action(action="read")` 讀回草稿，繼續寫作
- 禁止從頭重跑已 PASS 的 Phase

---

## 13 Main Gate Checkpoint Pipeline（Phase 0-11 + 6.5；Phase 2.1 為獨立 sub-gate）

Pipeline 定義「何時」→ Skill 定義「如何」→ Hook 定義「品質」→ Review 定義「完成度」。
本檔採 progressive disclosure：先讀本檔的總覽與 hard gate，再依檔尾「Reference 索引」載入對應 Phase 的詳細程序。
**本檔列出的 Code hard gate、安全閥與 MANDATORY 規則不可跳過；各 reference 內的 Phase 區段會就地重複同一條 gate，若有出入以本檔為準。**

### Pipeline 總覽

| Phase | 內容                                                                                   | Skill / 外部 MCP（🔸 = optional）                                           | 詳細程序                                                                                                                                                                                                                                                   |
| ----- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0     | PRE-PLANNING：source materials + journal profile + pipeline config                     | `asset-aware-mcp` 🔸, `fetch_webpage` 🔸                                    | [references/phase-0-pre-planning.md](references/phase-0-pre-planning.md)                                                                                                                                                                                   |
| 1     | PROJECT SETUP                                                                          | `project-management`                                                        | [references/phase-1-2-project-literature.md](references/phase-1-2-project-literature.md)                                                                                                                                                                   |
| 2     | LITERATURE SEARCH（advisory: CRITICAL APPRAISAL）                                      | `literature-review`, `parallel-search`; `pubmed-search`, `zotero-keeper` 🔸 | [references/phase-1-2-project-literature.md](references/phase-1-2-project-literature.md), [references/phase-2-1-fulltext-appraisal.md](references/phase-2-1-fulltext-appraisal.md)                                                                         |
| 2.1   | FULLTEXT INGESTION & ASSET EXTRACTION（獨立 sub-gate）                                 | `literature-review`; `asset-aware-mcp`, `pubmed-search`                     | [references/phase-2-1-fulltext-appraisal.md](references/phase-2-1-fulltext-appraisal.md)                                                                                                                                                                   |
| 3     | CONCEPT DEVELOPMENT                                                                    | `concept-development`; `cgu` 🔸                                             | [references/phase-3-4-concept-planning.md](references/phase-3-4-concept-planning.md)                                                                                                                                                                       |
| 4     | MANUSCRIPT PLANNING（advisory: SUPPLEMENTARY PLANNING、SUB-SECTION WRITING TEMPLATES） | `draft-writing`                                                             | [references/phase-3-4-concept-planning.md](references/phase-3-4-concept-planning.md), [references/phase-4-writing-templates.md](references/phase-4-writing-templates.md)                                                                                   |
| 5     | SECTION WRITING（Hook A/B cascading、section approval、asset sub-pipeline）            | `draft-writing`; `drawio` 🔸, `cgu` 🔸, data tools                          | [references/phase-5-section-writing.md](references/phase-5-section-writing.md), [references/phase-5-asset-generation.md](references/phase-5-asset-generation.md), [references/hooks-a-b-post-write-section.md](references/hooks-a-b-post-write-section.md) |
| 6     | CROSS-SECTION CASCADING AUDIT（Hook C/F）                                              | —                                                                           | [references/phase-6-6.5-audit-evolution.md](references/phase-6-6.5-audit-evolution.md), [references/hooks-c-post-manuscript.md](references/hooks-c-post-manuscript.md)                                                                                     |
| 6.5   | EVOLUTION GATE（baseline snapshot，強制進入 Review）                                   | —                                                                           | [references/phase-6-6.5-audit-evolution.md](references/phase-6-6.5-audit-evolution.md)                                                                                                                                                                     |
| 7     | AUTONOMOUS REVIEW（Multi-Reviewer、Hook E、R1-R6；MANDATORY）                          | autonomous-review + equator; `cgu` 🔸                                       | [references/phase-7-review-loop.md](references/phase-7-review-loop.md), [references/phase-7-equator-hook-e.md](references/phase-7-equator-hook-e.md)                                                                                                       |
| 8     | REFERENCE SYNC                                                                         | `reference-management`                                                      | [references/phase-8-11-delivery.md](references/phase-8-11-delivery.md)                                                                                                                                                                                     |
| 9     | EXPORT（docx + pdf；Code-Enforced CRITICAL；advisory: SUBMISSION READINESS）           | `word-export`, `submission-preparation`                                     | [references/phase-8-11-delivery.md](references/phase-8-11-delivery.md)                                                                                                                                                                                     |
| 10    | RETROSPECTIVE（Hook D meta-learning D1-D9）                                            | —                                                                           | [references/hooks-d-meta-learning.md](references/hooks-d-meta-learning.md), [references/phase-8-11-delivery.md](references/phase-8-11-delivery.md)                                                                                                         |
| 11    | FINAL DELIVERY（Code-Enforced CRITICAL）                                               | —                                                                           | [references/phase-8-11-delivery.md](references/phase-8-11-delivery.md)                                                                                                                                                                                     |

### Phase Code Hard Gates（逐字保留）

每個 Phase 結束都必須 `pipeline_action(action="validate_phase", phase=N)` 收到 PASS 才能進入下一 Phase。各 Phase 的 code hard gate 如下：

- **Phase 0 PRE-PLANNING**：**Code hard gate**: `journal-profile.yaml` + `.audit/source-materials.yaml` 存在。關鍵欄位是否合理／已由用戶確認是 workflow 判斷，不由 Phase 0 validator 逐欄驗證。
- **Phase 1 PROJECT SETUP**：**Code hard gate**: `drafts/`、`references/`、`data/`、`results/`、`.audit/`、`.memory/` 存在。paper type 對齊是 setup workflow 要求；Phase 2 起另以 `project.json` 作前置條件。
- **Phase 2 LITERATURE SEARCH**：**Code hard gate**: Paper-type-aware 最低文獻數 + 每筆 reference 有穩定 identity 與誠實 trust provenance。搜尋策略／選文紀錄缺失只警告。
- **Phase 2.1 FULLTEXT INGESTION**：**Code hard gate**: `fulltext-ingestion-status.md` 非空；每篇文獻都有可驗證 ingestion evidence 或明確 fallback；`analysis_completed: true` 必須對得上目前 source revision 的 analysis artifact；primary user materials 不得仍為 `pending_asset_aware`。
  **WARNING Gate**: 若 >50% 文獻無全文 → 提醒用戶考慮補充 OA 文獻
- **Phase 3 CONCEPT DEVELOPMENT**：**Code hard gate**: `concept.md` 含 NOVELTY / KEY SELLING POINTS、structured concept review 完整，且 decision 可採用（通常為 `readiness=ready`），或可信 host/UI 依用戶明確決定簽發
  `mdpaper.concept_review_override.v3` Ed25519 receipt。MCP/Agent 只能查詢或撤銷 receipt，
  不得以 `approved_by="human"` 或直接寫 YAML 冒充人類核准。
- **Phase 4 MANUSCRIPT PLANNING**：**Code hard gate**: Phase 3 concept review 仍可採用 + `manuscript-plan.yaml`（或 legacy `drafts/manuscript-plan.md`）存在。圖表數量、coverage、approval reason 是本 workflow 的自審／人工審閱要求；目前 Phase 4 validator 未逐欄重算。
- **Phase 6 CROSS-SECTION AUDIT**：**Workflow exit target**: Hook C/F 已處理至沒有未解決 CRITICAL（warnings 記錄但可接受）。**Code hard gate** 另驗證 quality-scorecard / hook-effectiveness 的有效資料與 data-artifact report；目前 validator 不在 Phase 6 內重跑全部 A/B/C hooks，也不單獨解析 unresolved-critical count。
- **Phase 6.5 EVOLUTION GATE**：**Gate**: baseline snapshot 完成 → `pipeline_action(action="validate_phase", phase=65)` 必須 PASS → 進入 Phase 7
- **Phase 8 REFERENCE SYNC**：**Code hard gate**: Phase 7 已完成 + References section 存在 + citation wikilinks 全部可解析。格式、引用數量／分布是本 workflow 與 C-series/R6 checks，不由 Phase 8 validator 額外重算。
- **Phase 9 EXPORT**：⚠️ **Code-Enforced**: `pipeline_action(action="validate_phase", phase=9)` 對 docx 和 pdf 的檢查為 CRITICAL severity。必須同時產出 docx 和 pdf，否則 Gate 不會通過。
  **Code hard gate**: `pipeline_action(action="validate_phase", phase=9)` — Phase 6–8 前置條件有效，DOCX + PDF 都存在且各自通過 integrity smoke。必要投稿文件清單是下方 submission-readiness advisory task，不是 Phase 9 validator 的額外 hard check。
- **Phase 10 RETROSPECTIVE**：**Code hard gate**: `pipeline-run-*.md` 含 D7/D8、hook-effectiveness report、`run_meta_learning` evolution event，以及可互相核對的 v2 audit schema、D1-D9、counts/lists/provenance。Project Memory 缺失只警告。
- **Phase 11 FINAL DELIVERY**：**Code hard gate**: `pipeline_action(action="validate_phase", phase=11)` — DOCX/PDF 再次通過 integrity smoke且 Phase 10 仍通過；目前沒有額外 completion-marker 檔案要求。Git remote/push 不作為硬性條件。

Phase 7 的 hard gate 見下方「Phase 6.5 / 7 強制規則」；Phase 5 的 section approval gate 見上方「必要 MCP Tool 呼叫」表（`approve_section`）。

### Phase 11 CRITICAL / optional provenance 清單（逐字）

⚠️ **Code-Enforced**: `pipeline_action(action="validate_phase", phase=11)` 驗證以下 CRITICAL 項目：

- Phase 9 匯出的 `.docx` + `.pdf` 存在
- Phase 10 retrospective / meta-learning artifacts 完整
- Phase 7 review loop 已完成

以下項目為 **optional provenance / WARNING or INFO**，不得阻擋 final delivery：

- Git repository 是否存在
- 工作目錄是否乾淨
- 最新 commit 是否包含專案檔案
- 是否有 remote/upstream / 是否 push

### Phase 6.5 / 7 強制規則（MANDATORY）

**Phase 6.5: EVOLUTION GATE（強制進入 Review）**

**目的**：建立 revision baseline，確保 Phase 7 Review **永遠執行**（不因 Hook A-C 全過而跳過）。
**觸發**：Phase 6 完成後 **MANDATORY**（無跳過條件）。

**Phase 7: AUTONOMOUS REVIEW（結構化 Review Loop — MANDATORY）**

**目的**：模擬同行審查，產出結構化 Review Report + Author Response，確保每個 issue 都被回應。
**觸發**：**ALWAYS**（Phase 6.5 強制進入，不可跳過）。即使 Hook A-C 全過、quality 已達標，仍必須至少執行 2 rounds（code-enforced `min_rounds=2`）。
**上限**：`pipeline.review_max_rounds`（預設 3）。
**最低輪數**：`min_rounds=2`（**Code-Enforced**：`AutonomousAuditLoop._determine_verdict()` 在 round < min_rounds 時強制返回 CONTINUE，不允許提前結束）。
**Hard Gate**：每輪 MUST call `pipeline_action(action="start_review", min_rounds=2)` 開始 + `pipeline_action(action="submit_review", scores=...)` 結束。Phase 7 固定安全下限為 `min_rounds >= 2`、`quality_threshold >= 7.0`、`max_rounds <= 10`，序列化狀態或專案設定都不能降低。Loop 結束後 `pipeline_action(action="validate_phase", phase=7)` 必須 PASS：除了驗證 rounds、artifact、hash chain、R1-R6 與重算分數，只有 `quality_met` 可在自主模式解鎖 Phase 8。`max_rounds`／`stagnated`／`user_needed` 是升級條件；若人類明確接受低於門檻的結果，可信 host/UI 必須簽發 `mdpaper.review_completion_override.v3` Ed25519 receipt，綁定專案、當前稿件與 loop state。MCP/Agent 只能查詢或撤銷，不能鑄造核准。

Phase 7 每輪必過的 stages（完整流程、Subagent 分工與模板見 [references/phase-7-review-loop.md](references/phase-7-review-loop.md)）：

- **Completeness Check（每輪必過）**：IF issue.id NOT IN author_response → FAIL（禁止忽略 issue）；→ 未回應的 issue 必須標記 DECLINE + 理由
- **Stage C: 執行修正（MANDATORY — 稿件必須被修改）**：⚠️ HARD ENFORCEMENT: `pipeline_action(action="submit_review", ...)` 會比對稿件 hash。若稿件未修改 → 提交會被 REJECT。
- **Stage C2: 敘事強化（MANDATORY — 即使無結構問題）**：至少 3 段落以 `draft_action(action="patch")` 修正並附改善理由，記錄到 author-response 的 "Narrative Enhancements" section；沒有結構性 issue 時仍 MANDATORY（最低改 3 段落）。
- **Stage C3: Anti-AI 自然度審查（MANDATORY — Code-Enforced Gate）**：`run_quality_checks(action="writing_hooks", hooks="A3,A3B,A3C")` 任何 CRITICAL → 必須 `draft_action(action="patch")` 修正後重跑，直到 PASS；必須全部 PASS 或僅 WARNING（無 CRITICAL）才能進入 Stage D，仍有 CRITICAL 則回到 Step 2 再修，最多 3 輪。
- **Stage D（總分 < quality_threshold 的最後一輪）**：用戶選項之一 — a) 接受當前品質：由可信 host/UI 收集具名 reviewer、rationale 與 accepted risks，簽發 state-bound `mdpaper.review_completion_override.v3` receipt；再呼叫 `pipeline_action(action="approve_review_completion", decision="status")` 驗證。不得由 MCP/Agent 簽發、改寫分數或宣稱 quality_met
- **Stage D2: 回退決策**：⚠️ regression_count > 2 → **安全閥：強制停下詢問用戶**（防止無限循環）

### 自動決策安全閥（必須停下 / 自動繼續）

**必須停下**：Concept < 60（兩次仍低）、Phase 4 大綱 approve、研究方向改變、Phase 6 N 輪 cascading 仍 CRITICAL、Review 連續 2 輪無分數改善、修改 AGENTS.md 核心原則。

**自動繼續**：Hook A/B WARNING → LOG → 下一步。Hook C WARNING → LOG → Phase 7。Review MINOR → batch fix → 下一輪。Asset fallback 成功 → 繼續。

#### Autopilot 模式（預設開啟）

```yaml
pipeline:
  autopilot: true # 預設全自動，用戶可設 false 啟用逐步審閱
  autopilot_pause_at: [] # 用戶可指定暫停點，例如 ["phase4", "phase5_section", "phase7_rewrite"]
```

| autopilot 設定       | 行為                                                                  |
| -------------------- | --------------------------------------------------------------------- |
| `true`（預設）       | Agent 全程自主決策、自我審閱、自我修正，僅在安全閥觸發時詢問用戶      |
| `false`              | 每個 Phase 確認點都詢問用戶（傳統模式）                               |
| `autopilot_pause_at` | 指定特定暫停點（精細控制），例如 Phase 4 確認大綱、Phase 5 逐 section |

安全閥（即使 autopilot=true 也會詢問用戶）：

- concept score < 75 且自動修正 2 次仍未達標
- Phase 6 cascading fix 3 rounds 後仍有 CRITICAL
- Phase 7 達 max_rounds 且品質未達標
- regression_count > 2（防止無限循環）

### 其他不可妥協規則（逐字；細節見對應 reference）

- Phase 0（[references/phase-0-pre-planning.md](references/phase-0-pre-planning.md)）：**Data Anchor Provenance Rule**：`data-artifacts.yaml` 的 `data_anchors` 不得以 `concept.md`、agent summary、inferred/estimated 值作為來源。每個數字/統計 anchor 必須引用 ready/ingested `source_material_id`、`asset_aware_doc_id`、`data_artifact_id`，或可信 data file；若來源素材仍是 `pending_asset_aware`，Hook F4 必須 CRITICAL fail。
- Phase 2.1（[references/phase-2-1-fulltext-appraisal.md](references/phase-2-1-fulltext-appraisal.md)）：**核心原則**: 引用文獻前必須閱讀全文並完成結構化分析。僅依據 abstract/metadata 不足以支撐 Methods/Results/Discussion 的引用。
- Phase 2.1：- ⚠️ 此文獻在寫作時僅能引用其 abstract 中的結論性資訊，不可引用具體方法或數據
- Phase 4（[references/phase-3-4-concept-planning.md](references/phase-3-4-concept-planning.md)）：Agent **禁止**刪除 `protected: true` 段落
- Hook D（[references/hooks-d-meta-learning.md](references/hooks-d-meta-learning.md)）：**需用戶確認**（`auto_apply=False`）：邏輯修正、新增/移除 Hook
- Hook D：**禁止修改**：CONSTITUTION 原則、🔒 規則、save_reference_mcp 優先、Hook D 自身邏輯

---

## Skill 依賴

auto-paper → Phase 0(pre-plan) → project-management(P1) → literature-review + parallel-search(P2) → fulltext-ingestion(P2.1) → concept-development(P3) → draft-writing(P4,5) → evolution-gate(P6.5) → autonomous-review+equator(P7) → reference-management(P8) → word-export(P9) → submission-preparation(P9)

---

## Reference 索引（read this when …）

| Reference                                                                                | 內容                                                                                                                                                        | Read this when                                                                                                                                |
| ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| [references/phase-0-pre-planning.md](references/phase-0-pre-planning.md)                 | Phase 0 流程、`journal-profile.yaml` / `source-materials.yaml` 對全 Pipeline 的約束、Data Anchor Provenance Rule                                            | Starting a project, scanning workspace source materials, generating `journal-profile.yaml`, or looking up which `pipeline.*` thresholds apply |
| [references/phase-1-2-project-literature.md](references/phase-1-2-project-literature.md) | Phase 1 專案建立、Phase 2 文獻搜尋與儲存（PubMed-first trust 規則）                                                                                         | Creating the project skeleton, running literature searches, or saving references (`save_reference_mcp`)                                       |
| [references/phase-2-1-fulltext-appraisal.md](references/phase-2-1-fulltext-appraisal.md) | 全文解析 / asset-aware ingestion sub-gate、`fulltext-ingestion-status.md`、critical appraisal matrix                                                        | Ingesting full texts or PDFs with asset-aware-mcp, writing `fulltext-ingestion-status.md`, or building `appraisal-matrix.md`                  |
| [references/phase-3-4-concept-planning.md](references/phase-3-4-concept-planning.md)     | Phase 3 concept / novelty 驗證（CGU）、Phase 4 `manuscript-plan.yaml`、Phase 4 advisory: SUPPLEMENTARY PLANNING                                             | Validating concept novelty (score < 75, CGU escalation), approving the outline, or generating / editing `manuscript-plan.yaml`                |
| [references/phase-4-writing-templates.md](references/phase-4-writing-templates.md)       | Introduction / Methods / Results / Discussion / Abstract 段落模板、圖表插入規範（C13）、Citation Decision Record 規範（C12）                                | About to write or review a manuscript section, placing figures/tables, or recording `citation_decisions.json`                                 |
| [references/phase-5-section-writing.md](references/phase-5-section-writing.md)           | Phase 5 逐 section 寫作迴圈、Hook A/B 觸發點、section approval gate、writing checkpoint                                                                     | Running, resuming or debugging Phase 5 section writing and its per-section Hook A/B loop                                                      |
| [references/phase-5-asset-generation.md](references/phase-5-asset-generation.md)         | Asset Generation Sub-Pipeline（Phase 5 Step 2）、Agent-Initiated Asset Generation（寫作中自主新增圖表）                                                     | Generating tables / figures / diagrams, handling missing asset data, or applying asset-tool fallbacks                                         |
| [references/phase-6-6.5-audit-evolution.md](references/phase-6-6.5-audit-evolution.md)   | Phase 6 三階段全稿審計與 Cascading 回溯規則、Phase 6.5 baseline snapshot 與強制進入 Review                                                                  | Running the whole-manuscript Hook C audit, handling Phase 5 FLAGs, or creating the pre-review baseline                                        |
| [references/phase-7-review-loop.md](references/phase-7-review-loop.md)                   | Multi-Reviewer 設計、Review Loop Stage A–E（含 C/C2/C3 MANDATORY 與 D2 回退決策）、Review 品質維度、Review vs Hook 分工                                     | Running any Phase 7 review round, writing the Author Response, fixing Anti-AI findings, or deciding to roll back to Phase 5                   |
| [references/phase-7-equator-hook-e.md](references/phase-7-equator-hook-e.md)             | E1 自動偵測適用指引、E2 checklist 逐條驗證、E3 EQUATOR 指引資料庫、E4 Compliance Report 格式、E5 與 Review Loop 整合                                        | Checking reporting-guideline compliance (CONSORT / STROBE / PRISMA / CARE …) during a Phase 7 round or producing `equator-compliance-*.md`    |
| [references/phase-8-11-delivery.md](references/phase-8-11-delivery.md)                   | Phase 8 引用同步、Phase 9 匯出（docx + pdf）、Phase 9 advisory: SUBMISSION READINESS、Phase 10 Retrospective、Phase 11 Final Delivery                       | Syncing references, exporting DOCX/PDF, preparing submission artifacts, running the retrospective, or closing the pipeline                    |
| [references/audit-trail-and-checkpoints.md](references/audit-trail-and-checkpoints.md)   | 每個 Phase 完成時 `.audit/` 產物的生成規格（pipeline-run、scorecard、review-round、Evolution Tracing …）與 `checkpoint.json` 恢復機制                       | Writing or verifying `.audit/` artifacts at the end of a phase or review round, or resuming a pipeline from `checkpoint.json`                 |
| [references/hooks-a-b-post-write-section.md](references/hooks-a-b-post-write-section.md) | Hook A（A1-A7，每次寫完即時修正）與 Hook B（B1-B16，section 完成後；含 B5 方法學 checklist、B6、B7 Section Brief、B8 Data-Claim）及其 Cascading Protocol    | Tuning or debugging per-write / per-section hook checks (word count, citations, Anti-AI, 🔒 protected content, tense, effect size …)          |
| [references/hooks-c-post-manuscript.md](references/hooks-c-post-manuscript.md)           | Hook C（C1-C14）全稿檢查、Cascading Protocol、C7 圖表數量與交叉引用、C8 時間一致性、C9 補充材料交叉引用                                                     | Running or debugging whole-manuscript checks (N-value, abbreviations, wikilinks, figure/table counts, cross-references, temporal consistency) |
| [references/hooks-d-meta-learning.md](references/hooks-d-meta-learning.md)               | Hook D（D1-D9）：效能統計、品質維度、Hook 自我改進與傳播程序、SKILL/Instruction 改進、D6 審計軌跡、D7 Review / D8 EQUATOR / D9 Tool Telemetry Retrospective | Running Phase 10 meta-learning, proposing a new hook, or propagating a hook definition across SKILL / AGENTS / copilot-instructions           |
| [references/auto-decisions.md](references/auto-decisions.md)                             | 情境 → 自動行為 → 停下條件對照表；「必須停下」與「自動繼續」清單                                                                                            | Deciding whether the agent may continue autonomously or must stop and ask the user                                                            |
| [references/cross-tool-orchestration.md](references/cross-tool-orchestration.md)         | Phase × 工具矩陣、跨 MCP 傳遞規則、何時跳過外部 MCP                                                                                                         | Deciding which internal / external MCP tool to call in a phase, or whether an optional MCP (zotero, cgu, drawio, asset-aware) can be skipped  |
| [references/closed-loop-checklist.md](references/closed-loop-checklist.md)               | Pipeline 完成前的最終 checklist（Phase 0–11 + audit artifacts + Hook D）                                                                                    | About to claim the pipeline is complete (always pair with `pipeline_action(action="heartbeat")`)                                              |
| [references/lessons-learned.md](references/lessons-learned.md)                           | Hook D / MetaLearningEngine 在 Phase 10 寫入的歷次 run 教訓（原 SKILL.md 末段）                                                                             | Starting a new run (to avoid repeating past mistakes) or when Hook D appends new lessons                                                      |

### 維護規則

- 本檔只保留：frontmatter、閉環架構、Hard Gate / Anti-Compaction、Pipeline 總覽、code hard gate 與 MANDATORY 規則、索引。**新增細節請寫到 `references/`，保持本檔 ≤ 500 行。**
- 每個 reference 一個主題；新增 reference 時同步更新上方索引。
- Hook D（Phase 10）新增 Hook 定義 → `references/hooks-*.md`；新增 Lessons Learned → [references/lessons-learned.md](references/lessons-learned.md)。
- 閉環檢查清單（Pipeline 完成前必過）→ [references/closed-loop-checklist.md](references/closed-loop-checklist.md)；自動決策表 → [references/auto-decisions.md](references/auto-decisions.md)；跨 MCP 編排 → [references/cross-tool-orchestration.md](references/cross-tool-orchestration.md)。
