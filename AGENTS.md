# AGENTS.md - VS Code Copilot Agent 指引

此文件為 VS Code GitHub Copilot 的 Agent Mode 提供專案上下文。

---

## 專案規則

### 法規遵循
你必須遵守以下法規層級：

1. **憲法**：`CONSTITUTION.md` - 最高原則，不可違反
2. **子法**：`.github/bylaws/*.md` - 細則規範
3. **技能**：`.claude/skills/*/SKILL.md` - 操作程序

### 架構原則

- 採用 **DDD (Domain-Driven Design)**
- **DAL (Data Access Layer) 必須獨立**
- 依賴方向：`Presentation → Application → Domain ← Infrastructure`

詳見：`.github/bylaws/ddd-architecture.md`

### MCP-to-MCP 通訊規則

**⚠️ 儲存文獻時必須遵守：**

```
✅ 正確：save_reference_mcp(pmid="12345678", agent_notes="...")
   → Agent 只傳 PMID，mdpaper 直接從 pubmed-search API 取得驗證資料

❌ 錯誤：save_reference(article={從 search 拿到的完整 metadata})
   → Agent 可能修改/幻覺書目資料
```

| 方法 | 資料來源 | Agent 可篡改？ | 使用時機 |
|------|----------|----------------|----------|
| `save_reference_mcp` | pubmed-search HTTP API | ❌ 不可能 | **永遠優先** |
| `save_reference` | Agent 傳遞 | ⚠️ 可能 | API 不可用時 fallback |

**分層信任格式**：
- `🔒 VERIFIED`: PubMed 原始資料（不可修改）
- `🤖 AGENT`: AI 筆記（`agent_notes` 參數）
- `✏️ USER`: 人類筆記（AI 絕不碰觸）

### Python 環境規則

- **優先使用 uv** 管理套件和虛擬環境
- 新專案必須建立 `pyproject.toml` + `uv.lock`
- 禁止全域安裝套件

```bash
# 初始化環境
uv venv
uv sync --all-extras

# 安裝依賴
uv add package-name
uv add --dev pytest ruff
```

詳見：`.github/bylaws/python-environment.md`

### Memory Bank 同步（專案層級）

**⚠️ 強制寫入位置：`memory-bank/`**

每次重要操作必須更新 Memory Bank：

| 操作 | 更新文件 |
|------|---------|
| 完成任務 | `memory-bank/progress.md` (Done) |
| 開始任務 | `memory-bank/progress.md` (Doing), `memory-bank/activeContext.md` |
| 重大決策 | `memory-bank/decisionLog.md` |
| 架構變更 | `memory-bank/architect.md` |

詳見：`.github/bylaws/memory-bank.md`

---

### ⭐ Project Memory 同步（研究專案層級）

**⚠️ 強制更新位置：`projects/{slug}/.memory/`**

每個研究專案有獨立的記憶，記錄 Agent 對這個研究的想法和進度：

```
projects/{slug}/
├── .memory/
│   ├── activeContext.md   ← Agent 的工作記憶
│   └── progress.md         ← 研究進度追蹤
├── concept.md
├── references/
└── drafts/
```

#### 何時讀取？

| 時機 | 問用戶確認 | 說明 |
|------|------------|------|
| 開始工作前 | 不需要 | 了解之前做了什麼、Agent 的想法 |
| 被問「之前...」 | 不需要 | 回顧歷史 |
| 要做重大決定 | 不需要 | 檢查之前的決定 |

#### 何時更新？（強制）

| 時機 | 更新內容 |
|------|----------|
| **每次對話結束時** ✅ | Current Focus, 本次工作摘要 |
| 做出重要決定後 | Recent Decisions |
| 發現關鍵文獻後 | Key References |
| 有想法/建議時 | Memo / Notes |
| 遇到問題時 | Blockers / Questions |

#### activeContext.md 區塊說明

| 區塊 | 內容 |
|------|------|
| **Project Settings** | Paper type, sections（專案建立時設定）|
| **User Preferences** | 用戶的互動風格、語言偏好 |
| **Current Focus** | 目前在做什麼（每次更新）|
| **Recent Decisions** | 重要決定和原因 |
| **Key References** | 關鍵文獻及其重要性 |
| **Blockers / Questions** | 待解決問題 |
| **Memo / Notes** | Agent 對研究的想法和建議 |

> 💡 **名言：「對話結束前，先更新 .memory/！」**
>
> 這樣下次對話就能繼續之前的思路，不會忘記 Agent 對研究的看法。

### Git 工作流

提交前必須執行檢查清單：
1. ✅ Memory Bank 同步（必要）
2. 📖 README 更新（如需要）
3. 📋 CHANGELOG 更新（如需要）
4. 🗺️ ROADMAP 標記（如需要）

詳見：`.github/bylaws/git-workflow.md`

---

## 可用 Skills

位於 `.claude/skills/` 目錄：

### 🔬 研究技能（本專案專屬）

| 技能 | 觸發語 | 說明 |
|------|--------|------|
| **literature-review** | 文獻回顧、找論文、systematic review | 系統性文獻搜尋、篩選、下載、整理 |
| **concept-development** | 發展概念、concept、novelty | 從文獻提煉研究概念，建立 concept.md |
| **parallel-search** | 並行搜尋、批量搜尋、擴展搜尋 | 多組關鍵字並行搜尋，提高覆蓋率 |

### 🛠️ 通用技能

| 技能 | 說明 |
|------|------|
| **git-precommit** | Git 提交前編排器 |
| **ddd-architect** | DDD 架構輔助與檢查 |
| **code-refactor** | 主動重構與模組化 |
| **memory-updater** | Memory Bank 同步 |
| **memory-checkpoint** | 記憶檢查點（Summarize 前外部化）|
| **readme-updater** | README 智能更新 |
| **changelog-updater** | CHANGELOG 自動更新 |
| **roadmap-updater** | ROADMAP 狀態追蹤 |
| **code-reviewer** | 程式碼審查 |
| **test-generator** | 測試生成（Unit/Integration/E2E）|
| **project-init** | 專案初始化 |

### Skill 系統架構

```
工具 (Tool) = 單一能力（搜尋、儲存、分析...）
技能 (Skill) = 完整知識（如何組合工具完成任務）
```

**執行流程**：
1. 識別用戶意圖 → 對應的 Skill
2. 讀取 `.claude/skills/{name}/SKILL.md`
3. 按照 Skill 定義的工作流程執行
4. 在決策點詢問用戶確認

**跨 MCP 協調**：
一個 Skill 可能需要呼叫多個 MCP 的工具（如 mdpaper + drawio），Agent 層級協調即可。

---

## 💸 Memory Checkpoint 規則

為避免對話被 Summarize 壓縮時遺失重要上下文：

### 主動觸發時機
1. 對話超過 **10 輪**
2. 累積修改超過 **5 個檔案**
3. 完成一個 **重要功能/修復**
4. 使用者說要 **離開/等等**

### 執行指令
- 「記憶檢查點」「checkpoint」「存檔」
- 「保存記憶」「sync memory」

### 必須記錄
- 當前工作焦點
- 變更的檔案列表（完整路徑）
- 待解決事項
- 下一步計畫

---

## 跨平台支援

本專案支援 Windows/Linux/macOS：

| 平台 | Python 路徑 | 安裝腳本 |
|------|-------------|----------|
| Windows | `.venv/Scripts/python.exe` | `scripts/setup.ps1` |
| Linux/macOS | `.venv/bin/python` | `scripts/setup.sh` |

---

## 回應風格

- 使用**繁體中文**
- 提供清晰的步驟說明
- 引用相關法規條文
- 執行操作後更新 Memory Bank
