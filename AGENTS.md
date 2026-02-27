# AGENTS.md - VS Code Copilot Agent 指引

> 操作前必查 `.copilot-mode.json` 確認當前模式。

---

## 核心價值：逐步多輪演進

> **寫論文是人類高度專業化、多年累積、多輪訓練的結果，而且是在科學方法下可重現的思考與整合步驟。Agent + MCP 框架應該有能力實現類似的逐步多輪演進。**（CONSTITUTION §25-26）

三層架構實現此價值：

| 層級                             | 機制                                                                                          | 觸發       | 實作狀態                                           |
| -------------------------------- | --------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------- |
| **L1** Event-Driven Hooks        | 56 個品質檢查（14 Code-Enforced / 42 Agent-Driven）                                           | Agent 操作 | ✅ 部分                                            |
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

禁止自動修改：CONSTITUTION 原則、🔒 保護內容規則、save_reference_mcp 優先規則。

### Pipeline 彈性機制（NEW）

| 功能          | MCP Tool                                     | Hard Gate?         | 說明                                                                                  |
| ------------- | -------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------- |
| Phase 回退    | `request_section_rewrite(sections, reason)`  | Yes — 僅 Phase 7   | Autopilot: Agent 自主決定回退。手動: 詢問用戶。regression_count > 2 強制詢問          |
| 暫停 Pipeline | `pause_pipeline(reason)`                     | No                 | 用戶隨時暫停，記錄 draft hash                                                         |
| 恢復 Pipeline | `resume_pipeline()`                          | No                 | 偵測用戶編輯，建議重新驗證                                                            |
| Section 審閱  | `approve_section(section, action, feedback)` | Yes — Phase 5 gate | Autopilot（預設）: Agent 自我審閱後自動 approve。手動: 逐 section 用戶 approve/revise |

### Hook 架構（56 checks — 14 Code-Enforced / 42 Agent-Driven）

Copilot Hooks（寫作時即時修正，`auto-paper/SKILL.md`）↔ Pre-Commit Hooks（git commit 前把關，`git-precommit/SKILL.md`）。

**Code-Enforced**（`run_writing_hooks` / `run_meta_learning` 有確定性程式碼邏輯）：

| Hook                | 引擎                                            | 位置                                |
| ------------------- | ----------------------------------------------- | ----------------------------------- |
| A5 語言一致性       | WritingHooksEngine.check_language_consistency   | persistence/writing_hooks.py        |
| A6 段落重複         | WritingHooksEngine.check_overlap                | persistence/writing_hooks.py        |
| B8 統計對齊         | WritingHooksEngine.check_data_claim_alignment   | persistence/writing_hooks.py        |
| C9 補充材料交叉引用 | WritingHooksEngine.check_supplementary_crossref | persistence/writing_hooks.py        |
| D1-D9 Meta-Learning | MetaLearningEngine.analyze()                    | persistence/meta_learning_engine.py |
| F1-F4 數據產出物    | WritingHooksEngine.validate_data_artifacts      | persistence/writing_hooks.py        |

**Agent-Driven**（僅靠 Agent 遵循 SKILL.md 指示，無 Code 強制）：

| 類型                   | 檢查內容                                                                | MCP Tools                                                |
| ---------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------- |
| **A1-A4** post-write   | 字數、引用密度、Anti-AI、Wikilink                                       | `count_words`, `patch_draft`, `validate_wikilinks`       |
| **B1-B7** post-section | 概念一致、🔒保護、方法學、寫作順序、Section Brief                       | `read_draft`, `patch_draft`, `check_writing_order`       |
| **C1-C8** post-ms      | 全稿一致性、投稿清單、數量與交叉引用、時間一致性                        | `check_formatting`, `scan_draft_citations`, `read_draft` |
| **E1-E5** EQUATOR      | 報告指引自動偵測、checklist 逐條驗證、合規報告                          | `read_draft`, `patch_draft`                              |
| **P1-P8** pre-commit   | 引用、Anti-AI、概念、字數、🔒、.memory、文獻、方法學                    | `scan_draft_citations`, `read_draft`, `count_words`      |
| **G1-G8** general      | Memory、README、CHANGELOG、ROADMAP、架構、專案一致性、VSX、文檔更新提醒 | `read_file`, `grep_search`, `list_dir`                   |

### Python 環境

uv 優先。`pyproject.toml` + `uv.lock`。禁止全域安裝。詳見 `.github/bylaws/python-environment.md`。

### Workspace State

狀態檔：`.mdpaper-state.json`

| 時機                               | 動作                                       |
| ---------------------------------- | ------------------------------------------ |
| 新對話 / 用戶說「繼續」            | `get_workspace_state()`                    |
| 開始重要任務 / 完成階段 / 對話結束 | `sync_workspace_state(doing, next_action)` |
| 恢復成功後                         | `clear_recovery_state()`                   |

### Artifact-Centric Architecture（部分上線）

`EMPTY → EXPLORATION → PROJECT`。設計文件：`docs/design/artifact-centric-architecture.md`

已上線：`start_exploration` `convert_exploration_to_project`（`get_exploration_status` 已合併至 `get_current_project(include_files=true)`）
未實作：`list_staged_artifacts` `tag_artifact` `link_artifact_to_project`

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
| literature-review      | 文獻回顧、找論文、PubMed             |
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

| 外部 MCP      | Phase                 | 觸發                  |
| ------------- | --------------------- | --------------------- |
| pubmed-search | 2 文獻                | 永遠                  |
| zotero-keeper | 2 文獻                | 用戶有 Zotero         |
| cgu           | 3 概念 / 5 Discussion | novelty < 75 / 論點弱 |
| drawio        | 5 Methods             | 需 flow diagram       |
| data tools    | 5 Results             | 需表格/圖             |

詳見 `.claude/skills/auto-paper/SKILL.md`「Cross-Tool Orchestration Map」。

---

## 跨平台

| 平台        | Python 路徑                | 安裝腳本            |
| ----------- | -------------------------- | ------------------- |
| Windows     | `.venv/Scripts/python.exe` | `scripts/setup.ps1` |
| Linux/macOS | `.venv/bin/python`         | `scripts/setup.sh`  |

## 回應風格

繁體中文 · 清晰步驟 · 引用法規 · uv 優先
