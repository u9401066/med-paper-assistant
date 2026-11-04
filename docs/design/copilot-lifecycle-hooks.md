# VS Code Copilot Lifecycle Hooks — 設計文件

> 版本：v1.0 | 2025-03  
> 對應 VS Code Copilot Hooks (Preview, v1.109.3+)

## 概述

MedPaper Assistant 透過 VS Code Copilot 的 8 個生命週期斷點 (Lifecycle Hook Events)，在 Agent 對話過程中注入品質檢查、模式保護、記憶同步。這些 hooks 與我們既有的 76-check 架構（A/B/C/D/E/F/G/P/R 系列）協同運作。

### 核心設計原則

1. **Python In-Process**：所有 hook 邏輯以純 stdlib Python 實作（`scripts/hooks/copilot/mdpaper_hooks/`），透過 stdin/stdout JSON 通訊；不依賴 bash 或 jq，也不為 hook 邏輯啟動子行程
2. **Non-Blocking Default**：大多數 hook 僅注入 `additionalContext`，不阻斷 Agent
3. **State Sharing**：hooks 間透過 `.github/hooks/_state/` 目錄下的 JSON 檔案通訊
4. **Audit Trail**：所有工具呼叫記錄至 `_state/session_audit.jsonl`

---

## 8 Event Lifecycle 對應表

| #   | VS Code Event        | 我們的 Hook      | 實作模組（`mdpaper_hooks/`） | POSIX shim            | 功能                                        |
| --- | -------------------- | ---------------- | ---------------------------- | --------------------- | ------------------------------------------- |
| 1   | **SessionStart**     | session-init     | `session_init.py`            | `session-init.sh`     | 讀取模式、恢復狀態、檢查 pending evolutions |
| 2   | **UserPromptSubmit** | prompt-analyzer  | `prompt_analyzer.py`         | `prompt-analyzer.sh`  | 偵測用戶意圖、注入工作流引導                |
| 3   | **PreToolUse**       | pre-tool-guard   | `pre_tool_guard.py`          | `pre-tool-guard.sh`   | 模式保護、危險指令攔截、save_reference 規則 |
| 4   | **PostToolUse**      | post-tool-check  | `post_tool_check.py`         | `post-tool-check.sh`  | Writing hooks 觸發、引用提醒、審計記錄      |
| 5   | **PreCompact**       | pre-compact-save | `pre_compact_save.py`        | `pre-compact-save.sh` | Context 壓縮前的記憶保存                    |
| 6   | **SubagentStart**    | subagent-init    | `subagent_init.py`           | `subagent-init.sh`    | 注入專案/模式上下文至 subagent              |
| 7   | **SubagentStop**     | _(不實作)_       | —                            | —                     | 不需要攔截 subagent 結束                    |
| 8   | **Stop**             | session-stop     | `session_stop.py`            | `session-stop.sh`     | 記憶同步提醒、審計結算、清理暫存            |

`mode-guard`（`.github/hooks/mode-guard.json`）是補強的 PreToolUse 層：`hook_dispatch.py mode-guard` 於同一行程內呼叫 `scripts/copilot_hook_guard.py`（唯一實作；`mode-guard.sh` 僅為其 fail-open 啟動器）。

### Python 實作與執行路徑

```
Copilot (Windows) ── powershell 鍵 ──▶ pythonw.exe hook_dispatch.py <name>; exit 0
Copilot / Claude Code (POSIX) ── bash 鍵 ──▶ <name>.sh ──exec──▶ python hook_dispatch.py <name>
                                                        │
                                  hook_dispatch.dispatch(name, stdin bytes)
                                                        │
                    mdpaper_hooks.run_hook(name, payload, REPO_ROOT)  /  copilot_hook_guard.run_hook
```

- **單一實作**：`*.sh` 僅為 8 行 shim（優先 `.venv/bin/python`，其次 `.venv/Scripts/python.exe`、`python3`、`python`；找不到直譯器時輸出 `{"continue": true}` 並 exit 0）。
- **無視窗**：Windows 使用 `pythonw.exe`，hook 邏輯在行程內執行，不會彈出 console 或把焦點搶給編輯器。唯一的子行程是 pre-tool-guard 的唯讀 `git diff`（`CREATE_NO_WINDOW`，共用 `GIT_BUDGET_SECONDS = 4` 秒預算）。
- **Fail-open 安全網**：`dispatch()` 捕捉所有例外，將錯誤追加至 `.github/hooks/_state/hook_errors.jsonl`（超過 256 KB 即重置），並輸出中性的 `{"continue": true}`；永不輸出 traceback，永遠 exit 0。
- **無 bash 後備**：shim 會回呼 dispatcher，因此保留 bash fallback 會造成遞迴，已移除（不提供 `MDPAPER_HOOKS_USE_BASH`）。
- **共用模組**：`common.py`（stdin 解析、輸出 helper、audit）、`workspace.py`（`.copilot-mode.json`、`.mdpaper-state.json`、`project.json` workflow_mode、`.audit/pending-evolutions.yaml` 讀取）。每個模組 ≤400 行、每個函式 ≤50 行（由 `tests/test_copilot_lifecycle_hooks_py.py` 檢查）。

---

## Hook 鏈路圖

> 圖中的 `*.sh` 名稱為對應 hook 的名稱／POSIX shim；實際邏輯位於 `mdpaper_hooks/<name>.py`。

```
┌──────────────────────────────────────────────────────────────────────┐
│                     VS Code Copilot Session                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ① SessionStart                                                      │
│  └─ session-init.sh                                                  │
│     ├─ Read .copilot-mode.json → mode                                │
│     ├─ Read .mdpaper-state.json → recovery context                   │
│     ├─ Check pending-evolutions.yaml → improvement hints             │
│     └─ Write _state/session_context.json → shared state              │
│                                                                      │
│  ↓ (user types a prompt)                                             │
│                                                                      │
│  ② UserPromptSubmit                                                  │
│  └─ prompt-analyzer.sh                                               │
│     ├─ Detect intent: mode-switch / commit / writing / autopilot     │
│     └─ Inject workflow guidance (SKILL.md reminder)                  │
│                                                                      │
│  ↓ (agent decides to use a tool)                                     │
│                                                                      │
│  ③ PreToolUse ←──── GATE (can DENY or ASK) ────┐                    │
│  └─ pre-tool-guard.sh                           │                    │
│     ├─ Mode protection (normal/research → deny  │                    │
│     │   writes to .claude/ src/ tests/ etc.)    │                    │
│     ├─ Destructive cmd blocking (rm -rf, etc.)  │                    │
│     ├─ save_reference → warn use _mcp           │                    │
│     └─ Audit: log tool invocation               │                    │
│                                                  │                    │
│  ↓ (tool executes)                               │                    │
│                                                  │ Feedback           │
│  ④ PostToolUse ──────────────────────────────────┘ Loop               │
│  └─ post-tool-check.sh                                               │
│     ├─ Draft edit → "run run_writing_hooks()"                        │
│     ├─ concept.md edit → "validate_concept() required"               │
│     ├─ git commit → memory sync reminder                             │
│     ├─ save_reference → "get_available_citations()"                  │
│     └─ Audit: log tool completion                                    │
│                                                                      │
│  ↓ (repeat ③→④ for each tool call)                                   │
│                                                                      │
│  ⑤ PreCompact (when context gets too long)                           │
│  └─ pre-compact-save.sh                                              │
│     ├─ Summarize: mode, doing, project, writing section              │
│     └─ Inject: "call sync_workspace_state() before continuing"       │
│                                                                      │
│  ⑥ SubagentStart (when subagent is spawned)                          │
│  └─ subagent-init.sh                                                 │
│     ├─ Inject active project + mode                                  │
│     └─ Agent-specific guidance (reviewer=read-only, etc.)            │
│                                                                      │
│  ⑧ Stop (session ends)                                               │
│  └─ session-stop.sh                                                  │
│     ├─ Reminder: sync memory-bank, workspace state                   │
│     ├─ Write session_end to audit log                                │
│     └─ Clean up transient _state/session_context.json                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 與 76-Check 架構的整合

### PreToolUse × PostToolUse 循環（核心）

這兩個 hook 構成一個 **回饋迴路**，是我們 Code-Enforced 品質系統的入口：

```
PostToolUse (draft edited)
  → injects "run run_writing_hooks(hooks='post-write')"
    → Agent calls run_writing_hooks
      → PreToolUse allows (it's an MCP tool)
        → WritingHooksEngine executes A1-A6, A3b (34 checks)
          → PostToolUse captures result
            → Agent fixes issues if any
```

### Hook 對應 Check 系列

| Lifecycle Hook                 | 觸發的 Check 系列             | 觸發方式                                                         |
| ------------------------------ | ----------------------------- | ---------------------------------------------------------------- |
| PostToolUse (draft edit)       | **A1-A6, A3b** (post-write)   | 注入 additionalContext 提醒 agent 呼叫 `run_writing_hooks`       |
| PostToolUse (section complete) | **B1-B16** (post-section)     | Agent 依 SKILL.md 呼叫 `run_writing_hooks(hooks='post-section')` |
| PostToolUse (manuscript done)  | **C1-C13** (post-manuscript)  | Agent 依 SKILL.md 呼叫                                           |
| PreToolUse (git commit)        | **P1-P8, G1-G9** (pre-commit) | Agent 載入 git-precommit SKILL.md 執行                           |
| Stop                           | **Memory sync**               | 注入提醒更新 memory-bank/                                        |
| SubagentStart (reviewer)       | **E1-E5** (EQUATOR)           | 注入上下文至 reviewer subagent                                   |

### 非 Lifecycle 的 Checks（由 SKILL.md 指導）

| Check 系列                 | 觸發時機        | 機制                                                               |
| -------------------------- | --------------- | ------------------------------------------------------------------ |
| **D1-D9** (Meta-Learning)  | Phase 10        | Agent 依 auto-paper SKILL.md 呼叫 `run_meta_learning`              |
| **F1-F4** (Data Artifacts) | post-manuscript | Agent 依 SKILL.md 呼叫 `validate_data_artifacts`                   |
| **R1-R6** (Review Hooks)   | Phase 7 submit  | Agent 依 SKILL.md 呼叫 `submit_review_round` → `ReviewHooksEngine` |

---

## State File 通訊

```
.github/hooks/_state/
├── session_context.json    # SessionStart 寫入，其他 hook 讀取
│   └─ { mode, doing, next_action, active_project, writing_session, ... }
└── session_audit.jsonl     # 所有 hook 追加寫入
    └─ { timestamp, event, tool, ... }  (一行一筆 JSON)
```

**生命週期**：

- `session_context.json`：SessionStart 建立 → PreToolUse/SubagentStart 讀取 → Stop 刪除
- `session_audit.jsonl`：全程追加 → Stop 寫入結算 → 保留供審計

---

## Hook I/O 規格

### 共通輸入（stdin JSON）

所有 hooks 都會收到：

```json
{
  "tool_name": "...",       // PreToolUse, PostToolUse
  "tool_input": {...},      // PreToolUse
  "tool_result": "...",     // PostToolUse
  "userMessage": "...",     // UserPromptSubmit
  "agentName": "..."        // SubagentStart
}
```

### 輸出格式

| Hook        | 可用輸出欄位                          | 說明               |
| ----------- | ------------------------------------- | ------------------ |
| PreToolUse  | `permissionDecision` (allow/deny/ask) | 控制工具是否執行   |
| PreToolUse  | `permissionDecisionReason`            | 向 Agent 解釋原因  |
| PreToolUse  | `updatedInput`                        | 修改工具輸入參數   |
| PreToolUse  | `additionalContext`                   | 注入上下文         |
| PostToolUse | `decision` (block)                    | 阻斷結果傳回 Agent |
| PostToolUse | `additionalContext`                   | 注入上下文         |
| 其他        | `additionalContext`                   | 注入上下文         |

---

## 配置檔案

**位置**：`.github/hooks/mdpaper-lifecycle.json`

```json
{
  "version": 1,
  "hooks": {
    "SessionStart": [{ "type": "command", "command": "...", "timeoutSec": 15 }],
    "UserPromptSubmit": [
      { "type": "command", "command": "...", "timeoutSec": 10 }
    ],
    "PreToolUse": [{ "type": "command", "command": "...", "timeoutSec": 10 }],
    "PostToolUse": [{ "type": "command", "command": "...", "timeoutSec": 15 }],
    "PreCompact": [{ "type": "command", "command": "...", "timeoutSec": 15 }],
    "SubagentStart": [
      { "type": "command", "command": "...", "timeoutSec": 10 }
    ],
    "Stop": [{ "type": "command", "command": "...", "timeoutSec": 15 }]
  }
}
```

每個項目同時帶有 `bash`（POSIX shim）、`powershell`（`pythonw.exe hook_dispatch.py <name>; exit 0`）、`command` 與 `windows` 鍵，確保 Windows 上不會經由 WSL `bash.exe` 或檔案關聯開啟編輯器。

**Timeout 設計**：

- 10s：輕量 hook（prompt-analyzer, pre-tool-guard, subagent-init）
- 15s：中重量 hook（session-init, post-tool-check, pre-compact-save, session-stop）
- pre-tool-guard 的 `git diff` 共用 `GIT_BUDGET_SECONDS`（4s），必須小於 PreToolUse timeout 並保留 dispatcher 啟動餘裕（由 `tests/test_hook_dispatch.py` 驗證）

---

## 與 pubmed-search-mcp 的 Hooks 比較

| 特性   | pubmed-search-mcp                                  | mdpaper (本專案)                                         |
| ------ | -------------------------------------------------- | -------------------------------------------------------- |
| 範圍   | 單一 MCP 服務的 pipeline 控管                      | 整個 workspace 生命週期                                  |
| Events | 5 (session, prompt, preTool, postTool, sessionEnd) | 7 (+ PreCompact, SubagentStart)                          |
| 策略   | Pipeline 強制、結果評估                            | 模式保護、品質 Hook 觸發、記憶管理                       |
| State  | workflow tracker + session context                 | session context + audit trail                            |
| 跨平台 | sh + ps1                                           | Python dispatcher（Windows `pythonw`）+ POSIX `.sh` shim |

---

## 安全考量

1. **PreToolUse deny** 是硬閘——Agent 無法繞過被 deny 的工具呼叫
2. **Fail-open dispatcher**：hook 腳本錯誤（例外、壞掉的 stdin）不得影響 Agent 運行——dispatcher 永遠 exit 0，錯誤寫入 `_state/hook_errors.jsonl` 並輸出中性結果；只有明確的 PreToolUse deny/ask 決策會回傳 `permissionDecision`
3. **Mode protection** 確保研究人員不會意外修改框架核心代碼
4. **Destructive command pattern** 使用白名單式檢查（只攔截已知危險模式）
5. **State 目錄** 不含敏感資料，僅有模式和工具名稱
6. **.gitignore** 應排除 `_state/` 目錄（暫存資料）

---

## 依賴

- **Python 3.12+**（repo `.venv`）— hook 邏輯僅用 stdlib；`.audit/pending-evolutions.yaml` 以內建行掃描器讀取，不需 PyYAML。
- **git** — 僅 pre-tool-guard 用於唯讀 `git diff`（偵測跨平台敏感檔案變更）；缺少 git 時視為無變更。
- **不再需要 jq 或 bash**：先前的 shell 版在未安裝 jq 時整組 hook 等同 no-op；Python 版在所有環境都實際生效。

---

## 未來擴展

- [x] **Windows 支援**：以 `pythonw.exe hook_dispatch.py` 取代 `.sh`／`.ps1`，單一 Python 實作
- [ ] **SubagentStop**：如需監控 subagent 輸出品質
- [ ] **PreToolUse updatedInput**：自動修正工具參數（如自動補全 project slug）
- [ ] **PostToolUse decision: block**：攔截低品質工具輸出（目前未使用）
- [ ] **Multi-hook 串聯**：同一事件可配置多個 hook 依序執行
