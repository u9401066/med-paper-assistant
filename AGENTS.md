# AGENTS.md - VS Code Copilot Agent 指引

> 操作前必查 `.copilot-mode.json` 確認當前模式。

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

### 核心設計（CONSTITUTION §22-23）

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

禁止自動修改：CONSTITUTION 原則、🔒 保護內容規則、save_reference_mcp 優先規則。

### Hook 架構（56 checks）

Copilot Hooks（寫作時即時修正，`auto-paper/SKILL.md`）↔ Pre-Commit Hooks（git commit 前把關，`git-precommit/SKILL.md`）。

| 類型                  | 檢查內容                                                                       | MCP Tools                                                                     |
| --------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| **A** post-write      | 字數、引用密度、Anti-AI、Wikilink、語言一致性(A5)、段落重複(A6)                | `count_words`, `patch_draft`, `validate_wikilinks`, `run_writing_hooks`       |
| **B** post-section    | 概念一致、🔒保護、方法學(B5)、寫作順序(B6)、Section Brief(B7)、統計對齊(B8)    | `read_draft`, `patch_draft`, `check_writing_order`, `run_writing_hooks`       |
| **C** post-manuscript | 全稿一致性、投稿清單、數量與交叉引用(C7)、時間一致性(C8)、補充材料交叉引用(C9) | `check_formatting`, `scan_draft_citations`, `read_draft`, `run_writing_hooks` |
| **D** meta-learning   | SKILL + Hook 改進 + Review Retro(D7) + EQUATOR Retro(D8)                       | `read_file`, `replace_string_in_file`                                         |
| **E** EQUATOR 合規    | 報告指引自動偵測、checklist 逐條驗證、compliance report                        | `read_draft`, `patch_draft`                                                   |
| **F** data-artifacts  | 溯源追蹤、manifest↔檔案一致、draft↔manifest 交叉引用、統計宣稱驗證           | `validate_data_artifacts`, `list_assets`                                      |
| **P1-P8** pre-commit  | 引用、Anti-AI、概念、字數、🔒、.memory、文獻、方法學                           | `scan_draft_citations`, `read_draft`, `count_words`                           |
| **G1-G8** general     | Memory、README、CHANGELOG、ROADMAP、架構、專案一致性、VSX、文檔更新提醒        | `read_file`, `grep_search`, `list_dir`                                        |

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

已上線：`start_exploration` `get_exploration_status` `convert_exploration_to_project`
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
