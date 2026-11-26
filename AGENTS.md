# AGENTS.md - Multi-Agent 指引（Copilot / Claude Code / Codex / Antigravity）

> 操作前必查 `.copilot-mode.json` 確認當前模式。本檔須維持 **≤ 24,000 bytes** 以確保 Antigravity 不截斷規則。

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
CGU 整合：`cgu_frame` / `cgu_diverge(action=anti_typical)` + `cgu_judge`（找弱點）、`cgu_diverge(action=collide)`（碰撞論點）、`cgu_diverge` + `cgu_ideas`（廣泛發想）。CGU 不替 agent 思考，生成/判斷步驟回傳 `work_order` 由 agent 自己的模型完成後回交。

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

| 元件                   | 位置                                     | 狀態 | 說明                                                                                     |
| ---------------------- | ---------------------------------------- | ---- | ---------------------------------------------------------------------------------------- |
| DomainConstraintEngine | `persistence/domain_constraint_engine/`  | ✅   | Sand Spreader — 13 種正式產出、110 個基礎約束、JSON 演化、驗證 anti-AI / 字數 / 必要章節 |
| ToolInvocationStore    | `persistence/tool_invocation_store.py`   | ✅   | 遙測持久化至 `.audit/tool-telemetry.yaml`，自動 via tool_logging.py                      |
| PendingEvolutionStore  | `persistence/pending_evolution_store.py` | ✅   | 跨對話演化項目持久化至 `.audit/pending-evolutions.yaml`                                  |
| guidance.py            | `tools/_shared/guidance.py`              | ✅   | `build_guidance_hint` + `build_startup_guidance`（啟動時檢查 pending evolutions）        |
| tool_health.py         | `tools/review/tool_health.py`            | ✅   | `diagnose_tool_health` + `_flush_health_alerts` 寫入 PendingEvolutionStore               |
| CheckpointManager      | `persistence/checkpoint_manager/`        | ✅   | Pipeline 狀態持久化 + 回退 + 暫停/恢復 + Section Approval                                |
| ReviewHooksEngine      | `persistence/review_hooks/`              | ✅   | R1-R6 審查品質 Hook — Phase 7 HARD GATE，整合 submit_review_round()                      |

禁止自動修改：CONSTITUTION 原則、🔒 保護內容規則、save_reference_mcp 優先規則。

### Pipeline 彈性機制（NEW）

| 功能          | MCP Tool                                     | Hard Gate?         | 說明                                                                                  |
| ------------- | -------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------- |
| Phase 回退    | `request_section_rewrite(sections, reason)`  | Yes — 僅 Phase 7   | Autopilot: Agent 自主決定回退。手動: 詢問用戶。regression_count > 2 強制詢問          |
| 暫停 Pipeline | `pause_pipeline(reason)`                     | No                 | 用戶隨時暫停，記錄 draft hash                                                         |
| 恢復 Pipeline | `resume_pipeline()`                          | No                 | 偵測用戶編輯，建議重新驗證                                                            |
| Section 審閱  | `approve_section(section, action, feedback)` | Yes — Phase 5 gate | Autopilot（預設）: Agent 自我審閱後自動 approve。手動: 逐 section 用戶 approve/revise |

### Hook 架構（79 checks — 56 Code-Enforced / 23 Agent-Driven）

Copilot Hooks（寫作時即時修正，`auto-paper/SKILL.md` 入口 + `auto-paper/references/hooks-*.md` 詳細規格）↔ Pre-Commit Hooks（git commit 前把關，`git-precommit/SKILL.md`）。

**Code-Enforced**（`run_writing_hooks` / `run_review_hooks` / `run_meta_learning` 具確定性程式碼邏輯）：

| 系列       | Checks（56）                                                                                                                    | 引擎與位置                                               |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| **A (9)**  | A1 字數、A2 引用密度、A3 Anti-AI、A3b 結構信號、A3c 語體、A4 Wikilink、A5 語言、A6 重複、A7 文獻充足                            | `WritingHooksEngine` (`writing_hooks/_post_write/`)      |
| **B (10)** | B2 🔒保護、B8 統計對齊、B9 時態、B10 段落品質、B11 Results 客觀、B12 Intro、B13 Discussion、B14 倫理、B15 Hedging、B16 效果量   | `WritingHooksEngine` (`writing_hooks/_section_quality/`) |
| **C (14)** | C2 投稿清單、C3 N 值、C4 縮寫、C5 Wikilink 解析、C6 全文字數、C7a/b/d 圖表計畫交叉引用、C9 補材、C10 全文、C11-C14 引用圖表證據 | `WritingHooksEngine` (`writing_hooks/_manuscript/`)      |
| **D (9)**  | D1–D9 Meta-Learning（Hook 效能、Scorecard、±20% 閾值、SKILL 建議、Audit、Review/EQUATOR 回顧、趨勢）                            | `MetaLearningEngine` (`meta_learning_engine/`)           |
| **F / G**  | F 數據產出物 (`_data_artifacts.py`)、G9 Git 狀態 (`_git.py`)                                                                    | `WritingHooksEngine` (`writing_hooks/`)                  |
| **P (6)**  | P1 引用（→C5）、P2 Anti-AI（→A3/b/c）、P4 字數（→A1 50%）、P5 保護內容、P6 記憶同步、P7 文獻完整性                              | `WritingHooksEngine` (`writing_hooks/_precommit/`)       |
| **R (6)**  | R1 報告深度、R2 回應完整、R3 EQUATOR、R4 修正追蹤、R5 審後 Anti-AI、R6 引用預算（Phase 7 HARD GATE）                            | `ReviewHooksEngine` (`persistence/review_hooks/`)        |

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

腳本位於 `scripts/hooks/copilot/`：hook 邏輯為純 stdlib Python（`mdpaper_hooks/`），由 `hook_dispatch.py <name>` 行程內呼叫（Windows 以 `pythonw.exe` 無視窗執行，任何例外皆 fail-open 並記錄至 `.github/hooks/_state/hook_errors.jsonl`）；`*.sh` 僅為 POSIX shim。不再需要 jq 或 bash。

另有補強型 `PreToolUse` runtime guard：`.github/hooks/mode-guard.json` 透過 fail-open launcher 呼叫 `scripts/copilot_hook_guard.py`，攔截受保護路徑修改與破壞性指令。

### Antigravity 原生整合

- **Plugin 探索**：`.agents/plugins.json` 指向 `plugins/`，自動載入 `plugins/med-paper-assistant/`（含 `mcp_config.json`、`rules/AGENTS.md`、25 skills、9 Antigravity `agents/*.md`）；`.agents/skills.json` 補齊開發期其餘 `.claude/skills/`（排除已打包之研究 skills，無重複）。
- **Lifecycle Hooks**：`.agents/hooks.json` 透過 `scripts/hooks/antigravity_dispatch.py` 橋接 `copilot_hook_guard` 與 `mdpaper_hooks`（fail-open、純 stdlib）。

### 測試與 CI 分層紀律

- **開發期**：只執行與本次變更直接相關的 **targeted tests**；**除非跨層核心重構、pre-push 或發布前驗證，否則不跑全量 test suite**。
- **Pre-commit / Pre-push**（`.pre-commit-config.yaml`）：承擔完整本機品質把關（格式化、lint、mypy、vulture、drift、ratchet、consistency、全量 pytest、full greedy smoke、VSX validate）。
- **CI（`.github/workflows/ci.yml`）**：一般 push / PR **僅跑最關鍵檢查**（`ruff check`、`bandit`、plugin/tool-surface authority、關鍵 `contract|mcp|smoke` 測試、MCP boot、compact smoke、VSX compile/test、docs structure）；全量檢查於每週排程、`workflow_dispatch` 與 `release.yml` 執行。

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

詳見 `.claude/skills/auto-paper/references/cross-tool-orchestration.md`「Cross-Tool Orchestration Map」（入口：`.claude/skills/auto-paper/SKILL.md`）。

---

## 跨平台

| 平台        | Python 路徑                | 安裝腳本            |
| ----------- | -------------------------- | ------------------- |
| Windows     | `.venv/Scripts/python.exe` | `scripts/setup.ps1` |
| Linux/macOS | `.venv/bin/python`         | `scripts/setup.sh`  |

## 回應風格

繁體中文 · 清晰步驟 · 引用法規 · uv 優先
