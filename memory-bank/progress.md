# Progress

## Milestones
- [x] Project Initialization
- [x] Core Features (PubMed, References, Draft, Analysis, Export)
- [x] Table 1 Generator
- [x] Search Strategy Manager
- [x] MCP Prompts
- [x] Multi-Project Support
- [x] Project Configuration & Memory
- [x] MCP Server Modular Refactoring
- [x] DDD Architecture Refactoring
- [x] Novelty Validation System
- [x] Draw.io MCP Integration
- [x] **Draw.io Agent-Generated XML Support** (2025-11-28)
- [x] **Draw.io Smart Save & User Events** (2025-11-28)
- [x] **Draw.io Load File & Full Feature Test** (2025-11-28)
- [x] **Draw.io Drawing Guidelines Tools** (2025-11-29)
- [x] **Draw.io Incremental Editing System** (2025-12-01)
- [x] **Smart Dev Server Start Script** (2025-12-01)
- [x] **WebSocket Real-time Communication** (2025-12-01)
- [x] **WebSocket Connection Stability Fix** (2025-12-01)
- [x] **Skills System** (2025-12-01)
- [x] **Parallel Search Feature** (2025-12-01)
- [x] **Iterative Search Expansion** (2025-12-01)
- [x] **MedPaper Dashboard** (2025-12-02)
- [x] **pubmed-search-mcp 子模組獨立化** (2025-12-02)
- [x] **工具架構重構** (2025-12-02)
- [x] **推薦擴展文件** (2025-12-02)
- [x] **Dashboard 專案切換增強** (2025-12-03)
- [x] **Foam Integration** (2025-12-03)
- [x] **pubmed-search-mcp 獨立 MCP 伺服器** (2025-12-03)
- [x] **跨平台支援 (Windows/Linux/macOS)** (2025-12-17)
- [x] **Memory Bank 統一化** (2025-12-17)
- [x] **Template 整合 (Bylaws + Skills)** (2025-12-17)
- [ ] **Medical Calculators Integration** (Planned - via medical-calc-mcp)
- [ ] **REST API Mode** (Planned)
- [ ] **Dashboard File Browser with Chonky** (Planned)

## 跨平台支援 + Memory Bank 統一化 (2025-12-17)

### 跨平台架構
從 Linux-only 改版為 Windows/Linux/macOS 支援：

| 檔案 | 變更 |
|------|------|
| `.vscode/mcp.json` | 使用 `platforms` 配置自動切換 Python 路徑 |
| `scripts/setup.ps1` | Windows 安裝腳本（完整重寫） |
| `scripts/setup.sh` | Linux/macOS 安裝腳本（更新 mcp.json 格式） |
| `README.md` | 新增 Windows/Linux/macOS 徽章 |

### Memory Bank 統一化
- 從 `.memory/` 遷移到 `memory-bank/`
- 更新 `.gitignore` 追蹤 `memory-bank/`
- `.github/bylaws/memory-bank.md` 新增「第 0 條」強制寫入位置

### Template 整合
從 `template-is-all-you-need` 整合：
- `.github/bylaws/` - 4 個子法檔案
- `.claude/skills/` - 13 個 Skills 目錄
- `CONSTITUTION.md` - 專案憲法
- `AGENTS.md` - Agent 行為指引
- `.editorconfig` - 編輯器配置

## Foam Integration (2025-12-03)

### 功能說明
整合 Foam VS Code 擴展，提供參考文獻的 Wikilink 管理：

| 功能 | 說明 |
|------|------|
| Citation Key | `author_year_pmid` 格式（如 `tang2023_38049909`）|
| Foam Alias | 自動建立 `tang2023_38049909.md` → 指向 PMID 目錄 |
| Hover Preview | 滑鼠移到 `[[citation_key]]` 顯示摘要 |
| ⭐ Preferred Style | 偏好引用格式標示在最前面 |
| YAML Frontmatter | pmid, type, year, doi, first_author |

### 技術實現
| 檔案 | 修改 |
|------|------|
| `reference_manager.py` | `_generate_citation_key()`, `_create_foam_alias()`, `_get_preferred_citation_style()` |
| `manager.py` | `rebuild_foam_aliases()` 工具, `set_citation_style()` 儲存設定 |
| `project_manager.py` | `update_project_settings(settings=dict)` |
| `.foam.json` | Foam workspace 識別 |
| `.vscode/settings.json` | Foam wikilink 設定 |

### 新增 MCP 工具
| 工具 | 說明 |
|------|------|
| `rebuild_foam_aliases` | 為現有參考文獻重建 Foam aliases |

## pubmed-search-mcp 獨立 MCP (2025-12-03)

### 功能說明
在 `.vscode/mcp.json` 新增 pubmed-search-mcp 作為獨立 MCP 伺服器，
與 mdpaper 並行運作，可直接使用 `mcp_pubmed_*` 工具。

### 設定
```json
"pubmed": {
  "type": "stdio",
  "command": "${workspaceFolder}/integrations/pubmed-search-mcp/.venv/bin/python",
  "args": ["-m", "pubmed_search_mcp"]
}
```

## Dashboard 專案切換增強 (2025-12-03)

### 功能說明
切換專案時自動開啟/關閉文件，避免多專案混淆：

| 選項 | 動作 |
|------|------|
| 🔄 開啟 + 關閉其他 | 關閉所有編輯器 → 開啟新專案文件 |
| 📂 只開啟 | 保留現有編輯器 → 開啟新專案文件 |

### 技術實現
- `vscode://file/path` - 開啟檔案
- `vscode://command:workbench.action.closeAllEditors` - 關閉所有

### 新增 MCP 工具
| 工具 | 說明 |
|------|------|
| `close_other_project_files` | 返回關閉指引 |
| `open_project_files` | 開啟專案文件 |
| `get_project_file_paths` | 取得專案路徑 |

## 推薦擴展 + Dashboard 檔案瀏覽器規劃 (2025-12-02)

### README 更新
新增「推薦的 VS Code 擴展」區塊：
- **Project Manager** - 快速切換專案
- **Foam** - Wikilinks、Backlinks、Graph

### Dashboard 檔案瀏覽器
選用 [Chonky](https://chonky.io/) React 元件（不造輪子！）：

| 特點 | 說明 |
|------|------|
| GitHub Stars | 772 |
| 週下載 | 12,000+ |
| 授權 | MIT |
| TypeScript | ✅ |

**功能:**
- Grid/List 視圖切換
- 拖放檔案
- 鍵盤快捷鍵
- 自訂圖示
- 虛擬化（大量檔案）

**安裝:**
```bash
npm install chonky chonky-icon-fontawesome
```

## Foam 整合規劃 (2025-12-02)

### Problem
MedPaper 目前缺少：
1. **參考文獻關聯視覺化** - 無法看到文獻之間的引用關係
2. **研究筆記連結** - 筆記之間沒有 wikilink 支援
3. **專案檔案瀏覽** - 缺少視覺化的檔案管理介面

### Solution
整合 [Foam](https://github.com/foambubble/foam) VS Code 擴展：

**Foam 提供的功能:**
| 功能 | 說明 |
|------|------|
| `[[wikilinks]]` | 快速連結筆記和參考文獻 |
| Backlinks Panel | 查看誰引用了當前文件 |
| Graph Visualization | 知識圖譜視覺化 |
| Orphan Detection | 找出孤立的筆記 |
| Link Sync on Rename | 重命名時自動更新連結 |

**MedPaper 需要額外開發:**
| 功能 | 說明 |
|------|------|
| Project File Manager | 專案檔案的視覺化瀏覽 |
| Reference Graph | 參考文獻的引用關係圖 |

### Implementation Plan
1. **Phase 1**: 推薦用戶安裝 Foam 擴展
2. **Phase 2**: 儲存參考文獻時自動建立 wikilink 相容格式
3. **Phase 3**: Dashboard 新增檔案瀏覽元件
4. **Phase 4**: 整合 Foam 的 Graph API（如果有）

## pubmed-search-mcp 子模組獨立化 (2025-12-02)

### Problem
PubMed 搜尋功能是通用功能，不應該只能在 med-paper-assistant 中使用。

### Solution
將搜尋功能抽取為獨立的 Git 子模組 `pubmed-search-mcp`：
- 獨立 GitHub repo: https://github.com/u9401066/pubmed-search-mcp
- 可單獨安裝使用
- 也可作為子模組整合

### Changes

| 變更 | 說明 |
|------|------|
| 新增 `integrations/pubmed-search-mcp/` | Git 子模組 |
| 刪除 `infrastructure/external/entrez/*.py` | 本地代碼移除 |
| 刪除 `tools/search/pubmed.py` | 使用子模組的 register_search_tools |
| 修改 `strategy_manager.py` | 重新導出子模組的 StrategyManager |
| 修改 `server.py` | 使用子模組的 LiteratureSearcher |

### 工具架構重構 (2025-12-02)

**從 56 個工具 → 52 個工具：**

| 類別 | 工具數 | 變更 |
|------|--------|------|
| PROJECT | 15 | +diagram 工具 |
| WRITING | 16 | 合併 export |
| SEARCH | 10 | 使用子模組 |
| REFERENCE | 8 | 不變 |
| SKILL | 3 | 不變 |
| ~~ANALYSIS~~ | ~~4~~ | 移除，獨立專案 |
| ~~DIAGRAM~~ | ~~3~~ | 合併到 PROJECT |

## MedPaper Dashboard (2025-12-02)

### Problem
使用純 MCP 工具管理專案有以下問題：
1. **專案切換不直覺** - 只有文字指令，Agent 和用戶都容易混亂
2. **工作階段不明確** - 在處理 concept/draft/formatting 時沒有視覺提示
3. **需要離開 VS Code** - 某些管理功能不適合純對話介面

### Solution
建立 **Next.js Dashboard** 作為專案管理 UI，與 Copilot Chat 並排使用。

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ VS Code                                                                      │
├──────────────────────────────────────┬──────────────────────────────────────┤
│  Simple Browser Tab                  │  GitHub Copilot Chat                 │
│  ────────────────────────            │  ───────────────────                 │
│                                      │                                      │
│  MedPaper Dashboard                  │  🤖 I see you're working on         │
│  (localhost:3002)                    │     ICU Sedation Study, focusing    │
│                                      │     on the Methods section.         │
│  [Projects][Focus][Diagrams]         │                                      │
│                                      │  How can I help?                    │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

### Features

**專案管理:**
- 專案列表（從 `/projects/` 讀取）
- 專案切換（下拉選單 + 點擊卡片）
- 顯示當前專案狀態

**工作焦點 (Focus):**
| Focus | 說明 |
|-------|------|
| `exploration` | 文獻探索階段 |
| `concept` | 發展研究概念 |
| `drafting` | 撰寫草稿（可選章節） |
| `revision` | 全文修訂 |
| `formatting` | 格式化投稿 |

**技術細節:**
- Next.js 16 + TypeScript + Tailwind CSS
- VS Code Simple Browser 相容
- API Routes 讀寫 `project.json`
- Focus 狀態即時同步到 MCP

### File Structure

```
dashboard/
├── src/
│   ├── app/
│   │   ├── page.tsx              # 主頁面
│   │   └── api/projects/         # API 路由
│   ├── components/
│   │   ├── ProjectSelector.tsx   # 專案選擇器
│   │   ├── FocusSelector.tsx     # 焦點選擇器
│   │   ├── ProjectCard.tsx       # 專案卡片
│   │   └── EnvironmentBadge.tsx  # VS Code 偵測
│   ├── hooks/
│   │   ├── useProjects.ts        # 專案狀態管理
│   │   └── useEnvironment.ts     # 環境偵測
│   └── types/
│       └── project.ts            # 類型定義
└── package.json
```

### Usage

```bash
# 啟動 Dashboard
cd dashboard && npm run dev -- -p 3002

# 在 VS Code 中開啟
# Ctrl+Shift+P → Simple Browser: Show → http://localhost:3002
```

### Next Steps

- [ ] Draw.io 嵌入整合
- [ ] WebSocket 即時同步
- [ ] 進度視覺化
- [ ] 協作功能

## Iterative Search Expansion (2025-12-01)

### Problem
並行搜尋雖然高效，但 `generate_search_queries` 只產生 5 組固定查詢。
當結果不足時，需要能夠迭代擴展搜尋。

### Solution

**新增工具:** `expand_search_queries`

**擴展方向:**
| Direction | 說明 | 範例 |
|-----------|------|------|
| `synonyms` | 同義詞擴展 | sedation → conscious sedation, procedural sedation |
| `related_concepts` | 相關概念 | propofol → remimazolam, dexmedetomidine |
| `different_fields` | 不同欄位 | [Title] → [Title/Abstract], [MeSH] |
| `broader_terms` | 更廣泛 | ICU → critical care, intensive care |
| `author_search` | 作者追蹤 | 根據已找到文獻的關鍵作者 |

**迭代工作流程:**
```
Phase 1: generate_search_queries → 並行搜尋 → merge
    ↓ 結果 < 需要數量?
Phase 2: expand_search_queries(direction="synonyms") → 並行搜尋 → merge
    ↓ 還不夠?
Phase 3: expand_search_queries(direction="related_concepts") → ...
```

**技術細節:**
- 追蹤已執行的 query IDs，避免重複
- 新 queries 命名: `exp_{direction}_{n}`
- 自動整合已儲存的搜尋策略

**檔案修改:**
- `src/med_paper_assistant/interfaces/mcp/tools/search/pubmed.py`: 新增 `expand_search_queries()`
- `.github/copilot-instructions.md`: 新增步驟 5 說明迭代擴展
- `.skills/research/parallel_search.md`: 新增「進階：迭代式搜尋擴展」段落

## Skills System & Parallel Search (2025-12-01)

### Overview
建立完整的技能系統，讓 AI Agent 知道如何組合多個工具完成複雜任務。
同時實作並行搜尋功能，利用 Agent 並行呼叫能力加速文獻搜尋。

### Skills System

**核心概念:**
- 工具 (Tool) = 單一能力
- 技能 (Skill) = 完整工作流程知識

**新增檔案:**
```
.skills/
├── README.md                    # 系統說明
├── _template.md                 # Skill 模板
├── ARCHITECTURE.md              # 架構設計
├── INTEGRATION.md               # 整合方案
└── research/
    ├── literature_review.md     # 文獻回顧技能
    ├── concept_development.md   # 概念發展技能
    └── parallel_search.md       # 並行搜尋技能
```

**MCP 工具:**
| 工具 | 功能 |
|------|------|
| `list_skills` | 列出所有可用技能 |
| `load_skill` | 載入特定技能內容 |
| `suggest_skill` | 根據任務描述建議技能 |

### Parallel Search

**新增工具:**
| 工具 | 功能 |
|------|------|
| `generate_search_queries` | 根據主題生成多組搜尋語法（自動整合策略）|
| `merge_search_results` | 合併多個搜尋結果並去重 |

**工作流程:**
```
configure_search_strategy(...)  ← 可選：設定日期、排除詞、文章類型
    ↓ 持久化儲存
generate_search_queries(topic="xxx", use_saved_strategy=True)
    ↓ 返回 5 組 queries（已整合策略）
並行呼叫 search_literature × 5
    ↓ 同時執行
merge_search_results(results=[...])
    ↓ 合併去重
42 篇文獻（含來源分析）
```

**策略整合 (2025-12-01 新增):**
- `configure_search_strategy()` 設定持久化策略
- `generate_search_queries()` 自動讀取並整合策略到查詢
- 支援: date_range, exclusions, article_types
- 無需重複設定，策略自動套用到所有生成的查詢

**測試結果:**
- 主題: "remimazolam ICU sedation"
- 並行執行 5 組搜尋策略
- 找到 56 篇（含重複）
- 去重後 42 篇
- 12 篇被多個策略找到（高相關性指標）

### Copilot Instructions 更新
在 `.github/copilot-instructions.md` 加入:
- Skills 索引表
- 執行流程說明
- 跨 MCP 協調指引
- 並行搜尋模式說明

## WebSocket Connection Stability Fix (2025-12-01)

### Problem
WebSocket 連線不斷斷線重連（每 ~350ms），原因是 React callback 依賴變化導致 `connect` 函數重新執行。

### Symptom
```
[WS] Client connected: client-xxx (total: 1)
[WS] Client disconnected: client-xxx (remaining: 0)
[WS] Client connected: client-yyy (total: 1)
... (重複)
```

### Solution

**1. useWebSocket.ts 修改:**
```typescript
// 使用 ref 儲存 callbacks 避免重連
const callbacksRef = useRef({
  onDiagramUpdate,
  onPendingOperations,
  onConnected,
  onDisconnected,
});

// 更新 callbacks ref
useEffect(() => {
  callbacksRef.current = { ... };
}, [callbacks]);

// handleMessage 使用 ref
const handleMessage = useCallback((event) => {
  callbacksRef.current.onDiagramUpdate?.(payload);
}, []); // 移除依賴
```

**2. diagram-context.tsx 修改:**
```typescript
// 使用 ref 避免循環依賴
const sendOperationResultRef = useRef<typeof sendOperationResult | null>(null);

useEffect(() => {
  sendOperationResultRef.current = sendOperationResult;
}, [sendOperationResult]);
```

### Result
- ✅ WebSocket 連線穩定維持
- ✅ 不再不斷斷線重連
- ✅ Fallback 機制正常運作
- ✅ 畫貓測試成功！

## WebSocket Real-time Communication (2025-12-01)

### Overview
實作 WebSocket 取代 HTTP Polling，提供即時雙向通訊。

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (Draw.io)                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  diagram-context.tsx                                    │ │
│  │  └── useWebSocket hook → ws://localhost:6003           │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↕ WebSocket
┌─────────────────────────────────────────────────────────────┐
│              WebSocket Server (獨立 Node.js)                 │
│              Port 6003 (WS) / 6004 (HTTP API)               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  scripts/ws-server.ts                                   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↕ HTTP (轉發)
┌─────────────────────────────────────────────────────────────┐
│              Next.js API (app/api/mcp/route.ts)             │
│              Port 6002                                       │
└─────────────────────────────────────────────────────────────┘
                              ↕ HTTP
┌─────────────────────────────────────────────────────────────┐
│              MCP Server (Python FastMCP)                     │
└─────────────────────────────────────────────────────────────┘
```

### New Files

| File | Description |
|------|-------------|
| `lib/websocket/types.ts` | 訊息類型定義 |
| `lib/websocket/server.ts` | WebSocket server 模組 |
| `lib/websocket/useWebSocket.ts` | React hook (瀏覽器端) |
| `lib/websocket/index.ts` | 模組匯出 |
| `scripts/ws-server.ts` | 獨立 WebSocket server |
| `test-websocket.py` | 整合測試腳本 |

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `connection_ack` | S→C | 連線確認 |
| `diagram_update` | S→C | 圖表更新推送 |
| `pending_operations` | S→C | 待執行操作 |
| `changes_report` | C→S | 用戶變更報告 |
| `operation_result` | C→S | 操作執行結果 |
| `subscribe` | C→S | 訂閱 tab |
| `ping/pong` | 雙向 | 心跳檢測 |

### npm Scripts

```bash
npm run dev:ws   # 啟動 WebSocket server (6003/6004)
npm run dev      # 啟動 Next.js (6002)
npm run dev:all  # 同時啟動兩者 (需要 concurrently)
```

### Test Results

```bash
$ python test-websocket.py
==================================================
WebSocket 整合測試
==================================================
  ✅ PASS: WS Server Status
  ✅ PASS: Display via Next.js
  ✅ PASS: Apply Operations
  ✅ PASS: Direct WS API

通過: 4/4
```

### Fallback Mechanism

- WebSocket 連線時: 即時通訊
- WebSocket 斷線時: 自動降級到 HTTP Polling (10秒間隔)

## Draw.io Incremental Editing System (2025-12-01)

### Overview
實作差異式編輯系統，減少 XML token 消耗，支援人機協作。

### Architecture

```
┌─────────────────┐     Polling      ┌─────────────────┐
│   MCP Server    │◄────────────────►│   Next.js API   │
│  (diff_tools)   │                  │   (route.ts)    │
└─────────────────┘                  └─────────────────┘
        │                                    │
        │ Operations                         │ Changes
        ▼                                    ▼
┌─────────────────────────────────────────────────────┐
│              Browser (Draw.io Editor)               │
│  ┌──────────────────┐  ┌─────────────────────────┐  │
│  │ DiagramDiffTracker│  │DiagramOperationsHandler│  │
│  └──────────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### New Files

**Frontend (TypeScript):**
| File | Description |
|------|-------------|
| `lib/diagram-diff-tracker.ts` | XML 差異追蹤器 |
| `lib/diagram-operations-handler.ts` | 增量操作處理器 (450+ lines) |
| `scripts/start-dev.sh` | 智能 port 啟動腳本 |

**Backend (Python):**
| File | Description |
|------|-------------|
| `tools/diff_tools.py` | MCP 差異工具 (580+ lines) |

**Documentation:**
| File | Description |
|------|-------------|
| `docs/INCREMENTAL_EDITING_RFC.md` | 設計 RFC |
| `docs/DIFF_COMMUNICATION_DESIGN.md` | 雙向 Diff 通訊設計 |

### MCP Tools (diff_tools.py)
| Tool | Description |
|------|-------------|
| `get_diagram_changes` | 取得用戶變更摘要 |
| `apply_diagram_changes` | 應用增量操作 |
| `get_diagram_elements` | 取得元素列表 (含 ID) |
| `sync_diagram_state` | 同步狀態，設定新基準 |

### Operation Types
```python
OperationType = Literal[
    "add_node",      # 新增節點
    "modify_node",   # 修改節點
    "delete_node",   # 刪除節點
    "add_edge",      # 新增連線
    "modify_edge",   # 修改連線
    "delete_edge",   # 刪除連線
]
```

### API Endpoints (route.ts)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `?action=get_changes` | GET | 取得用戶變更 |
| `?action=check_pending_ops` | GET | 檢查待執行操作 |
| `?action=get_apply_result` | GET | 取得操作結果 |
| `apply_operations` | POST | 發送增量操作 |
| `report_changes` | POST | 回報用戶變更 |
| `operation_result` | POST | 回報操作結果 |
| `set_base_xml` | POST | 設定基準 XML |
| `sync_diff_state` | POST | 同步 diff 狀態 |

### Polling Mechanism
```typescript
// diagram-context.tsx
useEffect(() => {
  // 每 2 秒檢查待執行操作
  const opsInterval = setInterval(checkAndApplyPendingOperations, 2000);
  // 每 3 秒回報變更
  const changesInterval = setInterval(reportChangesToServer, 3000);
  return () => {
    clearInterval(opsInterval);
    clearInterval(changesInterval);
  };
}, []);
```

### Smart Dev Server Script
解決 port 佔用問題：
```bash
# 新增命令
npm run dev:smart

# scripts/start-dev.sh 功能：
# - 自動檢測 port 是否被佔用
# - 自動殺死佔用進程（最多 3 次重試）
# - 支援自訂 port 參數
```

### Test Results
```bash
$ python simple-test.py
測試 Web 連線...
✅ Web 服務正在運行
測試顯示圖表...
結果: {'success': True, 'tabId': 'tab-xxx', 'tabName': 'Test'}
✅ 測試完成
```

### Future Improvements
- [x] WebSocket 替代 Polling（更即時）✅ 已完成
- [ ] 完整場景測試（貓 → 狗屋 → 走路）
- [ ] 衝突解決 UI

## Draw.io Drawing Guidelines Tools (2025-11-29)

### New Features

#### 1. Drawing Guidelines Module
新增 `drawing_guidelines.py` 模組，定義繪圖標準：

**連接線樣式 (推薦正交轉角線):**
```python
EDGE_STYLES = {
    "orthogonal": "edgeStyle=orthogonalEdgeStyle;rounded=1;...",  # ⭐⭐⭐
    "straight": "edgeStyle=none;",
    "curved": "edgeStyle=orthogonalEdgeStyle;curved=1;",
    "entityRelation": "edgeStyle=entityRelationEdgeStyle;",
}
```

**標準顏色規範:**
| 顏色 | fillColor | strokeColor | 用途 |
|------|-----------|-------------|------|
| 藍色 | #dae8fc | #6c8ebf | 處理步驟 |
| 綠色 | #d5e8d4 | #82b366 | 開始/成功 |
| 黃色 | #fff2cc | #d6b656 | 決策 |
| 紅色 | #f8cecc | #b85450 | 結束/錯誤 |

**佈局規範:**
- 水平間距: 60px
- 垂直間距: 40px
- 畫布邊距: 40px

#### 2. MCP Tools
| 工具 | 描述 |
|------|------|
| `get_drawing_guidelines` | 取得繪圖最佳實踐 |
| `get_style_string` | 生成 Draw.io style 字串 |
| `list_available_styles` | 列出所有可用樣式 |

### Test Results
```
=== Test 1: General Guidelines === ✅
=== Test 2: Edge Style String === ✅  
→ style="edgeStyle=orthogonalEdgeStyle;rounded=1;...endArrow=classic;"
=== Test 3: Shape Style String === ✅
→ style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
```

### Files Created
| File | Description |
|------|-------------|
| `drawing_guidelines.py` | 繪圖標準定義（350+ 行） |
| `tools/guideline_tools.py` | MCP 工具實作 |

### Files Changed
| File | Changes |
|------|---------|
| `tools/__init__.py` | 註冊 guideline_tools |
| `README.md` | 新增繪圖指南文檔 |

## Draw.io Load File & Full Feature Test (2025-11-28)

### New Features

#### 1. Load File Tool
```python
load_file_impl(file_path: str, tab_name: Optional[str] = None)
```
- 載入現有 .drawio 檔案到瀏覽器編輯器
- 自動使用檔名作為分頁名稱
- 支援完整 Draw.io XML 格式

#### 2. Debug Logging System
前端錯誤可回報到後端終端機，方便除錯：
```typescript
// 前端
fetch('/api/mcp', { body: { action: 'debug_log', message: '...' } });

// 後端 (route.ts)
console.log(`[BROWSER DEBUG] ${message}`);
```

### Test Results
| Test | Description | Status |
|------|-------------|--------|
| Simple diagram | "Test" box | ✅ |
| Baseball field | Full field with bases, lines, outfield | ✅ |
| User save | Ctrl+S triggers user_save event | ✅ |
| Load file | load_file loads .drawio | ✅ |
| Tab switching | Multiple tabs work | ✅ |

### Files Changed
| File | Changes |
|------|---------|
| `tab_tools.py` | Added `load_file_impl` |
| `diagram-context.tsx` | Added debug logging |
| `route.ts` | Added `debug_log` action |
| `page.tsx` | Improved handleSave logging |

## Draw.io Smart Save & User Events (2025-11-28)

### New Features

#### 1. Smart Save Workflow
```
save_tab() 無路徑 → 回傳提示 → Agent 詢問/自動判斷 → save_tab(path)
```

#### 2. User Event Query (Pull Model)
```
瀏覽器操作 → 事件隊列 → Agent 需要時呼叫 get_user_events()
```
- 隱私保護：不自動發送給 AI
- 節省 Token：按需拉取

#### 3. Browser Save Button
- Ctrl+S 觸發檔案下載
- 檔名格式：`diagram-2025-11-28T10-30-00.drawio`
- 防抖動：2 秒內不重複

### MCP-to-MCP Collaboration (TODO)
```
用戶「存到專案」
    ↓
Agent → MDPaper MCP (取專案路徑)
    ↓
Agent → Draw.io MCP (save_tab)
```

### Files Changed
| File | Changes |
|------|---------|
| `tab_tools.py` | `save_tab` 可選路徑 |
| `web_tools.py` | 新增 `get_user_events` |
| `web_client.py` | 新增事件查詢 API |
| `api/mcp/route.ts` | 新增 `user_save`, `events` |
| `page.tsx` | `onSave` + 檔案下載 |

## Draw.io Agent-Generated XML (2025-11-28)

### Problem
原本 `create_diagram` 工具只產生硬編碼模板（開始→處理→結束），無法根據描述生成複雜圖表。

### Solution
讓 Agent (Copilot) 自己生成 Draw.io XML，MCP 工具只負責驗證和發送到瀏覽器。

### Changes
```
mcp-server/src/drawio_mcp_server/
├── tools/diagram_tools.py   # 新增 xml 參數和格式說明
├── web_client.py            # 修正 port 檢測和 lazy start
└── server.py                # 移除預先啟動避免阻塞
```

### New Workflow
```
用戶請求 → Agent 生成 XML → create_diagram(xml=...) → 驗證 → 瀏覽器顯示
```

### Key Features
| Feature | Description |
|---------|-------------|
| **xml 參數** | Agent 可直接傳入 Draw.io XML |
| **格式說明** | 參數描述包含完整 XML 格式文檔 |
| **智能 Port 檢測** | 使用 socket 檢查 port 狀態 |
| **Lazy Start** | Web 服務首次使用時才啟動 |
| **避免重複開啟** | 提示 Agent 不要重複呼叫 open_browser |

### Test Results
- ✅ 畫一隻馬：成功生成卡通馬圖
- ✅ 研究路線圖：成功生成 6 階段詳細流程圖

## Draw.io MCP Integration (2025-11-28)

### Overview
Integrated Draw.io diagram creation/editing as a submodule with its own MCP server:

```
integrations/next-ai-draw-io/           # Git submodule
├── app/                                # Next.js 15 frontend
│   ├── api/mcp/route.ts               # MCP communication API
│   └── api/tabs/route.ts              # Tab management API
└── mcp-server/                         # Python MCP server
    └── src/drawio_mcp_server/
        ├── __main__.py                # Entry point
        ├── server.py                  # FastMCP server (10 tools)
        ├── config.py                  # Configuration management
        ├── web_client.py              # HTTP client for Next.js
        ├── diagram_generator.py       # XML generation
        ├── validator.py               # XML validation
        ├── templates.py               # Diagram templates
        └── tools/                     # Modular tool definitions
            ├── diagram_tools.py       # create/edit/read
            ├── template_tools.py      # templates & export
            ├── tab_tools.py           # tab management
            └── web_tools.py           # web service control
```

### Key Features
| Feature | Description |
|---------|-------------|
| **10 MCP Tools** | Create, edit, read, export diagrams |
| **Auto Web Start** | MCP auto-starts Next.js server |
| **Multi-Tab** | Multiple diagrams in tabs |
| **XML Validation** | Validates Draw.io XML before sending |
| **9 Diagram Types** | flowchart, aws, gcp, azure, mindmap, sequence, er, network, custom |

### MCP RuntimeWarning Fix
Fixed Python module import warnings for both MCP servers:

```python
# Before: python -m package.server (causes RuntimeWarning)
# After:  python -m package (uses __main__.py)
```

Updated:
- `med_paper_assistant.interfaces.mcp/__main__.py` - New entry point
- `med_paper_assistant.interfaces.mcp/__init__.py` - Lazy imports
- `.vscode/mcp.json` - Updated args to use package module

## Novelty Validation System (2025-11-27)

### Overview
Implemented comprehensive concept validation with multi-round novelty scoring:

```
domain/services/
└── novelty_scorer.py      # Scoring criteria, dimensions, LLM prompts

infrastructure/services/
└── concept_validator.py   # Validation service with caching
```

### Key Features
| Feature | Description |
|---------|-------------|
| **3-Round Scoring** | Multiple independent evaluations for reliability |
| **75+ Threshold** | All rounds must pass to proceed |
| **5 Dimensions** | Uniqueness, Significance, Gap Alignment, Specificity, Verifiability |
| **Consistency Check** | Cross-section alignment validation |
| **Actionable Feedback** | Specific suggestions when validation fails |
| **24h Cache** | Results cached to avoid redundant evaluations |

### New Tools
- `validate_concept` - Full validation with novelty scoring
- `validate_concept_quick` - Fast structural check only

### Tool Count
- Total: 43 tools (was 42)

### Architecture
```
ConceptValidator
├── _validate_structure()    # Required sections check
├── _evaluate_novelty()      # 3-round scoring
├── _check_consistency()     # Section alignment
├── _check_citation_support() # Citation coverage
└── generate_report()        # Human-readable output
```

## DDD Architecture (2025-11-27)

### Overview
Refactored the entire `src/med_paper_assistant/` to follow Domain-Driven Design (DDD) pattern:

```
src/med_paper_assistant/
├── domain/           # Core business logic
│   ├── entities/     # Project, Reference, Draft
│   ├── value_objects/# CitationStyle, SearchCriteria
│   └── services/     # CitationFormatter
├── application/      # Use cases
│   └── use_cases/    # CreateProject, SearchLiterature, SaveReference
├── infrastructure/   # Technical concerns
│   ├── config.py     # AppConfig
│   ├── logging.py    # setup_logger
│   ├── persistence/  # ProjectRepository, ReferenceRepository, FileStorage
│   └── external/     # PubMedClient (wraps entrez/)
├── interfaces/       # External interfaces
│   └── mcp/          # MCP server wrapper
├── shared/           # Cross-cutting concerns
│   ├── constants.py  # PAPER_TYPES, PROJECT_DIRECTORIES
│   └── exceptions.py # MedPaperError hierarchy
├── core/             # Legacy modules (maintained for compatibility)
└── mcp_server/       # Legacy MCP server (maintained for compatibility)
```

### New Files Created
- **shared/**: constants.py, exceptions.py
- **domain/entities/**: project.py, reference.py, draft.py
- **domain/value_objects/**: citation.py, search_criteria.py
- **domain/services/**: citation_formatter.py
- **infrastructure/**: config.py, logging.py
- **infrastructure/persistence/**: project_repository.py, reference_repository.py, file_storage.py
- **infrastructure/external/pubmed/**: client.py, parser.py
- **application/use_cases/**: create_project.py, search_literature.py, save_reference.py
- **interfaces/mcp/**: server.py (wrapper)

### Backward Compatibility
- `core/` and `mcp_server/` preserved for existing functionality
- All new DDD layers tested and importing correctly
- Legacy code can gradually migrate to new architecture

## Previous Milestones

### MCP Server Refactoring (2025-11-26)
- 42 tools, 7 prompts
- `setup_project_interactive` with MCP Elicitation

### Multi-Project Support (2025-11-26)
- Project isolation with project.json, concept.md
- Project-aware prompts
- 6 new project tools

### Entrez Modular Refactoring
- Refactored search.py into core/entrez/ package
- 6 submodules: base, search, pdf, citation, batch, utils

### Reference Enhancement
- 32 tools total
- Pre-formatted citations, PDF fulltext, citation network
