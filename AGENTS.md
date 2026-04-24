# AGENTS.md - VS Code Copilot Agent 指引

> 操作前必查 `.copilot-mode.json` 確認當前模式。

---

## 核心價值：逐步多輪演進

> **寫論文是人類高度專業化、多年累積、多輪訓練的結果，而且是在科學方法下可重現的思考與整合步驟。Agent + MCP 框架應該有能力實現類似的逐步多輪演進。**（CONSTITUTION §25-26）

三層架構實現此價值：

| 層級                             | 機制                                                                                          | 觸發       | 實作狀態                                           |
| -------------------------------- | --------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------- |
| **L1** Event-Driven Hooks        | 79 個品質檢查（56 Code-Enforced / 23 Agent-Driven）                                           | Agent 操作 | ✅ 部分                                            |
| **L2** Code-Level Enforcement    | DomainConstraintEngine + ToolInvocationStore + PendingEvolutionStore + guidance + tool_health | 工具呼叫   | ✅ 完整                                            |
| **L3** Autonomous Self-Evolution | MetaLearningEngine (D1-D9) + GitHub Actions CI + PendingEvolution 跨對話                      | 外部排程   | ⚠️ 大部分（缺 git post-commit、EvolutionVerifier） |

每一輪都產出可審計紀錄，每一輪都比前一輪更好。三層缺一不可。

---

## 運行模式

| 模式          | 啟用技能 | Memory Bank | 靜態分析 |
| ------------- | -------- | ----------- | -------- |
| `development` | 全部     | 完整同步    | ✅       |
| `normal`      | 研究技能 | 最小化      | ❌       |
| `research`    | 研究技能 | 僅專案      | ❌       |

切換：修改 `.copilot-mode.json`。觸發語：「開發模式」→ development、「一般/normal」→ normal、「研究/寫論文」→ research。

### 檔案保護（Normal/Research）

**唯讀**：`.claude/` `.github/` `src/` `tests/` `integrations/` `AGENTS.md` `CONSTITUTION.md` `ARCHITECTURE.md` `pyproject.toml`
**可寫**：`projects/` `memory-bank/` `docs/`

用戶要改受保護檔案 → 提示切換開發模式。

---

## 專案規則

### 法規層級

CONSTITUTION.md > `.github/bylaws/*.md` > `.claude/skills/*/SKILL.md`

### 架構

DDD，DAL 獨立。依賴方向：`Presentation → Application → Domain ← Infrastructure`。詳見 `.github/bylaws/ddd-architecture.md`。

### 儲存文獻（MCP-to-MCP）

| 方法                       | 資料來源          | 可篡改？ | 使用時機     |
| -------------------------- | ----------------- | -------- | ------------ |
| `save_reference_mcp(pmid)` | pubmed-search API | ❌       | **永遠優先** |
| `save_reference(article)`  | Agent 傳遞        | ⚠️       | API 不可用時 |

信任層：🔒 VERIFIED（PubMed 原始）→ 🤖 AGENT（`agent_notes`）→ ✏️ USER（人類筆記，AI 不碰）

### Novelty Check

犀利回饋 + 給選項（直接寫？修正？用 CGU？）。禁止：討好式回饋、自動改 NOVELTY、反覆追分。
CGU 整合：`deep_think`（找弱點）、`spark_collision`（碰撞論點）、`generate_ideas`（廣泛發想）。

### 核心設計（CONSTITUTION §22-23, §25-26）

| §22 原則 | 實作                                      |
| -------- | ----------------------------------------- |
| 可審計   | `.audit/` + quality-scorecard（0-10）     |
| 可拆解   | Phase 獨立、Hook 可插拔、輸入/輸出是檔案  |
| 可重組   | checkpoint.json、Pipeline 任意 Phase 繼續 |

| §23 自我改進                    | 限制             |
| ------------------------------- | ---------------- |
| L1 Skill — 更新 Lessons Learned | 自動             |
| L2 Hook — 調整閾值              | ±20%             |
| L3 Instruction — 事實性內容     | 記錄 decisionLog |

| §25-26 核心哲學                           | 要點                               |
| ----------------------------------------- | ---------------------------------- |
| 逐步多輪演進                              | 類比人類學術訓練的螺旋式進步       |
| 三層演進架構（L1 Hook / L2 Code / L3 CI） | 三層缺一不可                       |
| 演進的紀律                                | 要有證據、可回溯、有邊界、服務人類 |

### L2 Code-Level Enforcement 元件

| 元件                   | 位置                                      | 狀態 | 說明                                                                              |
| ---------------------- | ----------------------------------------- | ---- | --------------------------------------------------------------------------------- |
| DomainConstraintEngine | `persistence/domain_constraint_engine.py` | ✅   | Sand Spreader — 3 紙類 26 個約束、JSON 演化、驗證 anti-AI / 字數 / 必要章節       |
| ToolInvocationStore    | `persistence/tool_invocation_store.py`    | ✅   | 遙測持久化至 `.audit/tool-telemetry.yaml`，自動 via tool_logging.py               |
| PendingEvolutionStore  | `persistence/pending_evolution_store.py`  | ✅   | 跨對話演化項目持久化至 `.audit/pending-evolutions.yaml`                           |
| guidance.py            | `tools/_shared/guidance.py`               | ✅   | `build_guidance_hint` + `build_startup_guidance`（啟動時檢查 pending evolutions） |
| tool_health.py         | `tools/review/tool_health.py`             | ✅   | `diagnose_tool_health` + `_flush_health_alerts` 寫入 PendingEvolutionStore        |
| CheckpointManager      | `persistence/checkpoint_manager.py`       | ✅   | Pipeline 狀態持久化 + 回退 + 暫停/恢復 + Section Approval                         |
| ReviewHooksEngine      | `persistence/review_hooks.py`             | ✅   | R1-R6 審查品質 Hook — Phase 7 HARD GATE，整合 submit_review_round()               |

禁止自動修改：CONSTITUTION 原則、🔒 保護內容規則、save_reference_mcp 優先規則。

### Pipeline 彈性機制（NEW）

| 功能          | MCP Tool                                     | Hard Gate?         | 說明                                                                                  |
| ------------- | -------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------- |
| Phase 回退    | `request_section_rewrite(sections, reason)`  | Yes — 僅 Phase 7   | Autopilot: Agent 自主決定回退。手動: 詢問用戶。regression_count > 2 強制詢問          |
| 暫停 Pipeline | `pause_pipeline(reason)`                     | No                 | 用戶隨時暫停，記錄 draft hash                                                         |
| 恢復 Pipeline | `resume_pipeline()`                          | No                 | 偵測用戶編輯，建議重新驗證                                                            |
| Section 審閱  | `approve_section(section, action, feedback)` | Yes — Phase 5 gate | Autopilot（預設）: Agent 自我審閱後自動 approve。手動: 逐 section 用戶 approve/revise |

### Hook 架構（79 checks — 56 Code-Enforced / 23 Agent-Driven）

Copilot Hooks（寫作時即時修正，`auto-paper/SKILL.md`）↔ Pre-Commit Hooks（git commit 前把關，`git-precommit/SKILL.md`）。

**Code-Enforced**（`run_writing_hooks` / `run_review_hooks` / `run_meta_learning` 有確定性程式碼邏輯）：

| Hook                    | 引擎                                                 | 位置                                           |
| ----------------------- | ---------------------------------------------------- | ---------------------------------------------- |
| A1 字數合規             | WritingHooksEngine.check_word_count_compliance       | persistence/writing_hooks/\_post_write.py      |
| A2 引用密度             | WritingHooksEngine.check_citation_density            | persistence/writing_hooks/\_post_write.py      |
| A3 Anti-AI 偵測         | WritingHooksEngine.check_anti_ai_patterns            | persistence/writing_hooks/\_post_write.py      |
| A3b AI 結構信號         | WritingHooksEngine.check_ai_writing_signals          | persistence/writing_hooks/\_post_write.py      |
| A3c 語體一致性          | WritingHooksEngine.check_voice_consistency           | persistence/writing_hooks/\_post_write.py      |
| A4 Wikilink 格式        | WritingHooksEngine.check_wikilink_format             | persistence/writing_hooks/\_post_write.py      |
| A5 語言一致性           | WritingHooksEngine.check_language_consistency        | persistence/writing_hooks/\_post_write.py      |
| A6 段落重複             | WritingHooksEngine.check_overlap                     | persistence/writing_hooks/\_post_write.py      |
| A7 文獻數量充足性       | WritingHooksEngine.check_reference_sufficiency       | persistence/writing_hooks/\_engine.py          |
| B2 🔒保護內容           | WritingHooksEngine.\_run_b2_protected_content        | persistence/writing_hooks/\_engine.py          |
| B8 統計對齊             | WritingHooksEngine.check_data_claim_alignment        | persistence/writing_hooks/\_section_quality.py |
| B9 時態一致性           | WritingHooksEngine.check_section_tense               | persistence/writing_hooks/\_section_quality.py |
| B10 段落品質            | WritingHooksEngine.check_paragraph_quality           | persistence/writing_hooks/\_section_quality.py |
| B11 Results 客觀性      | WritingHooksEngine.check_results_interpretation      | persistence/writing_hooks/\_section_quality.py |
| B12 Introduction 結構   | WritingHooksEngine.check_intro_structure             | persistence/writing_hooks/\_section_quality.py |
| B13 Discussion 結構     | WritingHooksEngine.check_discussion_structure        | persistence/writing_hooks/\_section_quality.py |
| B14 倫理聲明            | WritingHooksEngine.check_ethical_statements          | persistence/writing_hooks/\_section_quality.py |
| B15 Hedging 密度        | WritingHooksEngine.check_hedging_density             | persistence/writing_hooks/\_section_quality.py |
| B16 效果量報告          | WritingHooksEngine.check_effect_size_reporting       | persistence/writing_hooks/\_section_quality.py |
| C3 N 值一致性           | WritingHooksEngine.check_n_value_consistency         | persistence/writing_hooks/\_manuscript.py      |
| C4 縮寫首次定義         | WritingHooksEngine.check_abbreviation_first_use      | persistence/writing_hooks/\_manuscript.py      |
| C5 Wikilink 可解析      | WritingHooksEngine.check_wikilink_resolvable         | persistence/writing_hooks/\_manuscript.py      |
| C6 全文字數             | WritingHooksEngine.check_total_word_count            | persistence/writing_hooks/\_manuscript.py      |
| C7a 圖表數量限制        | WritingHooksEngine.check_figure_table_counts         | persistence/writing_hooks/\_manuscript.py      |
| C7b 資產計畫覆蓋        | WritingHooksEngine.check_asset_plan_coverage         | persistence/writing_hooks/\_manuscript.py      |
| C7d 交叉引用檢測        | WritingHooksEngine.check_cross_references            | persistence/writing_hooks/\_manuscript.py      |
| C9 補充材料交叉引用     | WritingHooksEngine.check_supplementary_crossref      | persistence/writing_hooks/\_manuscript.py      |
| C10 文獻全文驗證        | WritingHooksEngine.check_reference_fulltext_status   | persistence/writing_hooks/\_manuscript.py      |
| C11 引用分布            | WritingHooksEngine.check_citation_distribution       | persistence/writing_hooks/\_manuscript.py      |
| C12 引用決策審計        | WritingHooksEngine.check_citation_relevance_audit    | persistence/writing_hooks/\_manuscript.py      |
| C13 圖表品質            | WritingHooksEngine.check_figure_table_quality        | persistence/writing_hooks/\_manuscript.py      |
| C14 Claim-Evidence 對齊 | WritingHooksEngine.check_claim_evidence_alignment    | persistence/writing_hooks/\_manuscript.py      |
| C2 投稿清單             | WritingHooksEngine.check_submission_checklist        | persistence/writing_hooks/\_manuscript.py      |
| D1-D9 Meta-Learning     | MetaLearningEngine.analyze()                         | persistence/meta_learning_engine.py            |
| F 數據產出物            | WritingHooksEngine.validate_data_artifacts           | persistence/writing_hooks/\_data_artifacts.py  |
| G9 Git 狀態             | WritingHooksEngine.check_git_status                  | persistence/writing_hooks/\_git.py             |
| P1 引用完整性           | WritingHooksEngine (delegates to C5)                 | persistence/writing_hooks/\_precommit.py       |
| P2 Anti-AI 掃描         | WritingHooksEngine (delegates to A3+A3b+A3c)         | persistence/writing_hooks/\_precommit.py       |
| P4 字數門檻             | WritingHooksEngine (delegates to A1, 50% threshold)  | persistence/writing_hooks/\_precommit.py       |
| P5 保護內容             | WritingHooksEngine.check_protected_content           | persistence/writing_hooks/\_precommit.py       |
| P6 記憶同步             | WritingHooksEngine.check_memory_sync                 | persistence/writing_hooks/\_precommit.py       |
| P7 文獻完整性           | WritingHooksEngine.check_reference_integrity         | persistence/writing_hooks/\_precommit.py       |
| R1 審查報告深度         | ReviewHooksEngine.check_review_report_depth          | persistence/review_hooks.py                    |
| R2 作者回應完整性       | ReviewHooksEngine.check_author_response_completeness | persistence/review_hooks.py                    |
| R3 EQUATOR 合規門檻     | ReviewHooksEngine.check_equator_compliance           | persistence/review_hooks.py                    |
| R4 審查-修正追蹤性      | ReviewHooksEngine.check_review_fix_traceability      | persistence/review_hooks.py                    |
| R5 審後 Anti-AI 門檻    | ReviewHooksEngine.check_post_review_anti_ai          | persistence/review_hooks.py                    |
| R6 引用預算門檻         | ReviewHooksEngine.check_citation_budget              | persistence/review_hooks.py                    |

**Agent-Driven**（僅靠 Agent 遵循 SKILL.md 指示，無 Code 強制）：

| 類型                   | 檢查內容                                                                | MCP Tools                                                |
| ---------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------- |
| **B1-B7** post-section | 概念一致、方法學、寫作順序、Section Brief                               | `read_draft`, `patch_draft`, `check_writing_order`       |
| **C1, C8** post-ms     | 全稿一致性、時間一致性                                                  | `check_formatting`, `scan_draft_citations`, `read_draft` |
| **E1-E5** EQUATOR      | 報告指引自動偵測、checklist 逐條驗證、合規報告                          | `read_draft`, `patch_draft`                              |
| **P3, P8** commit      | 概念一致、方法學驗證                                                    | `scan_draft_citations`, `read_draft`, `count_words`      |
| **G1-G8** general      | Memory、README、CHANGELOG、ROADMAP、架構、專案一致性、VSX、文檔更新提醒 | `read_file`, `grep_search`, `list_dir`                   |

> **注意**：A1-A4、C3-C7d、P1/P2/P4 雖有 Code-Enforced 實作，但 Agent 也在更高語義層級進行評估。

### Python 環境

uv 優先。`pyproject.toml` + `uv.lock`。禁止全域安裝。詳見 `.github/bylaws/python-environment.md`。

### Workspace State

狀態檔：`.mdpaper-state.json`

| 時機                               | 動作                                                     |
| ---------------------------------- | -------------------------------------------------------- |
| 新對話 / 用戶說「繼續」            | `get_workspace_state()`                                  |
| 開始重要任務 / 完成階段 / 對話結束 | `sync_workspace_state(doing, next_action)`               |
| 恢復成功後                         | `clear_recovery_state()`                                 |
| 寫作中段落切換前                   | `checkpoint_writing_context(section, plan, notes, refs)` |

> **Writing Session Auto-Checkpoint**: `write_draft()` / `patch_draft()` 成功後自動寫入 `writing_session` 至 `.mdpaper-state.json`。不需手動操作。`get_workspace_state()` 恢復時會顯示 ✍️ Writing Session banner。

### Artifact-Centric Architecture（部分上線）

`EMPTY → EXPLORATION → PROJECT`。設計文件：`docs/design/artifact-centric-architecture.md`

已上線：`start_exploration` `convert_exploration_to_project`（`get_exploration_status` 已合併至 `get_current_project(include_files=true)`）
未實作：`list_staged_artifacts` `tag_artifact` `link_artifact_to_project`

### VS Code Copilot Lifecycle Hooks

7 個核心 lifecycle hook 腳本（`.github/hooks/mdpaper-lifecycle.json`）。設計文件：`docs/design/copilot-lifecycle-hooks.md`。

| Event            | 腳本                | 功能                                   |
| ---------------- | ------------------- | -------------------------------------- |
| SessionStart     | session-init.sh     | 載入模式/recovery/pending evolutions   |
| UserPromptSubmit | prompt-analyzer.sh  | 意圖偵測（mode-switch/commit/writing） |
| PreToolUse       | pre-tool-guard.sh   | 模式保護 + 破壞性指令攔截              |
| PostToolUse      | post-tool-check.sh  | Hook 提醒（draft→writing hooks 等）    |
| PreCompact       | pre-compact-save.sh | Context 壓縮前 checkpoint              |
| SubagentStart    | subagent-init.sh    | 注入專案/模式至 subagent               |
| Stop             | session-stop.sh     | 審計 + 清理 + memory sync 提醒         |

腳本位於 `scripts/hooks/copilot/`。依賴 jq（腳本無 jq 時 graceful degradation）。

另有補強型 `PreToolUse` runtime guard：`.github/hooks/mode-guard.json` 會在工具執行前呼叫 `scripts/copilot_hook_guard.py`，補上 Python / `apply_patch` / Windows PowerShell 路徑解析，專門攔截受保護路徑修改與破壞性 terminal 指令。它是 lifecycle hooks 的補充層，不取代 `mdpaper-lifecycle.json`。

---

## Memory 同步

### Memory Bank（`memory-bank/`）

| 操作          | 更新文件                          |
| ------------- | --------------------------------- |
| 完成/開始任務 | `progress.md`, `activeContext.md` |
| 重大決策      | `decisionLog.md`                  |
| 架構變更      | `architect.md`                    |

詳見：`.github/bylaws/memory-bank.md`

### Project Memory（`projects/{slug}/.memory/`）

**每次對話結束**必更新 `activeContext.md`（Current Focus, Recent Decisions, Key References, Memo）和 `progress.md`。
其他觸發：做出重要決定、發現關鍵文獻、有想法/建議、遇到問題。

### Memory Checkpoint

觸發：對話 >10 輪、修改 >5 檔案、完成重要功能、用戶要離開。
記錄：當前焦點、變更檔案列表、待解決事項、下一步計畫。

### Git 工作流

提交前：Memory Bank 同步 → README → CHANGELOG → ROADMAP。詳見 `.github/bylaws/git-workflow.md`。

---

## Capabilities

索引：`.github/prompts/_capability-index.md`

觸發規則：精確（`/mdpaper.xxx`）→ 意圖匹配 → 情境匹配。
執行時載入對應 `.prompt.md`，按 Phase 順序進行，銜接 Skills。

---

## Skills

位於 `.claude/skills/*/SKILL.md`。流程：識別用戶意圖 → 讀取 SKILL.md → 按工作流程執行 → 決策點詢問用戶。

### 研究技能

| 技能                   | 觸發語                               |
| ---------------------- | ------------------------------------ |
| auto-paper             | 全自動寫論文、autopilot、一鍵寫論文  |
| literature-review      | 文獻回顧、找論文、PubMed、全文閱讀   |
| concept-development    | concept、novelty、驗證失敗           |
| concept-validation     | 驗證、validate、可以開始寫了嗎       |
| parallel-search        | 並行搜尋、多組搜尋、廣泛搜尋         |
| project-management     | 新專案、切換專案、paper type         |
| draft-writing          | 寫草稿、draft、Introduction、Methods |
| reference-management   | 存這篇、save、儲存文獻               |
| word-export            | 匯出 Word、export、docx              |
| academic-debate        | 辯論、debate、devil's advocate       |
| idea-validation        | 假說驗證、feasibility、PICO          |
| manuscript-review      | peer review、CONSORT、STROBE         |
| submission-preparation | 投稿準備、cover letter               |

### 通用技能

| 技能              | 觸發語                  |
| ----------------- | ----------------------- |
| git-precommit     | commit、推送、收工      |
| git-doc-updater   | docs、文檔、sync docs   |
| ddd-architect     | 架構、新功能、structure |
| code-refactor     | 重構、整理、優化        |
| memory-updater    | 記憶、進度、紀錄        |
| memory-checkpoint | 存檔、要離開、怕忘記    |
| readme-updater    | readme、安裝說明        |
| readme-i18n       | i18n、翻譯、多語言      |
| changelog-updater | changelog、發布         |
| roadmap-updater   | roadmap、規劃           |
| code-reviewer     | review、檢查、安全      |
| test-generator    | test、coverage、pytest  |
| project-init      | init、新專案、初始化    |

### 跨 MCP 編排

Pipeline（auto-paper SKILL.md）定義「何時」→ Skill 定義「如何」→ Hook 定義「品質」。

| 外部 MCP      | Phase                 | 觸發                                |
| ------------- | --------------------- | ----------------------------------- |
| pubmed-search | 2 文獻, 2.1 全文      | 永遠                                |
| asset-aware   | 2.1 全文解析          | 有 PDF/OA 可取（否則記錄 metadata） |
| zotero-keeper | 2 文獻                | 用戶有 Zotero                       |
| cgu           | 3 概念 / 5 Discussion | novelty < 75 / 論點弱               |
| drawio        | 5 Methods             | 需 flow diagram                     |
| data tools    | 5 Results             | 需表格/圖                           |

詳見 `.claude/skills/auto-paper/SKILL.md`「Cross-Tool Orchestration Map」。

---

## 跨平台

| 平台        | Python 路徑                | 安裝腳本            |
| ----------- | -------------------------- | ------------------- |
| Windows     | `.venv/Scripts/python.exe` | `scripts/setup.ps1` |
| Linux/macOS | `.venv/bin/python`         | `scripts/setup.sh`  |

## 回應風格

繁體中文 · 清晰步驟 · 引用法規 · uv 優先
