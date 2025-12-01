# Active Context

## Current Focus
Skills 技能系統與並行搜尋功能開發完成

## Recent Changes (2025-12-01)

### 1. Skills 技能系統 ✅ (LATEST!)

建立完整的技能系統，讓 AI Agent 知道如何組合多個工具完成複雜任務：

**核心概念:**
```
工具 (Tool) = 單一能力（搜尋、儲存、分析...）
技能 (Skill) = 完整知識（如何做好一件事）
```

**新增檔案:**
| 檔案 | 說明 |
|------|------|
| `.skills/README.md` | Skills 系統說明 |
| `.skills/_template.md` | Skill 檔案模板 |
| `.skills/ARCHITECTURE.md` | 架構設計文件 |
| `.skills/INTEGRATION.md` | 整合方案說明 |
| `.skills/research/literature_review.md` | 系統性文獻回顧技能 |
| `.skills/research/concept_development.md` | 研究概念發展技能 |
| `.skills/research/parallel_search.md` | 並行搜尋技能 |

**MCP 工具:**
| 工具 | 功能 |
|------|------|
| `list_skills` | 列出所有可用技能 |
| `load_skill` | 載入特定技能內容 |
| `suggest_skill` | 根據任務描述建議技能 |

### 2. 並行搜尋功能 ✅

利用 Agent 並行呼叫能力加速文獻搜尋：

**新增工具:**
| 工具 | 功能 |
|------|------|
| `generate_search_queries` | 根據主題生成多組搜尋語法 |
| `merge_search_results` | 合併多個搜尋結果並去重 |

**工作流程:**
```
1. generate_search_queries(topic="remimazolam ICU") 
   → 返回 5 組不同角度的搜尋語法

2. 並行呼叫 search_literature × 5
   → 同時執行所有搜尋

3. merge_search_results(results=[...])
   → 合併去重，分析來源
```

**測試結果:**
- 搜尋 "remimazolam ICU sedation"
- 5 組策略並行執行
- 找到 42 篇去重後文獻
- 12 篇被多個策略找到（高相關性）

### 3. WebSocket 連線穩定性修復 ✅

修復 WebSocket 不斷重連的問題，原因是 React callback 依賴變化導致：

**問題症狀:**
```
[WS] Client connected: client-xxx (total: 1)
[WS] Client disconnected: client-xxx (remaining: 0)
[WS] Client connected: client-yyy (total: 1)
[WS] Client disconnected: client-yyy (remaining: 0)
... (每 ~350ms 重複)
```

**修復方案:**
| 檔案 | 修改 |
|------|------|
| `lib/websocket/useWebSocket.ts` | 使用 `callbacksRef` 儲存 callbacks，避免依賴變化 |
| `contexts/diagram-context.tsx` | 使用 `sendOperationResultRef` 避免循環依賴 |

**修改細節:**
1. `useWebSocket.ts`:
   - 新增 `callbacksRef` 保存 `onDiagramUpdate`, `onPendingOperations`, `onConnected`, `onDisconnected`
   - `handleMessage` 使用 `callbacksRef.current` 呼叫 callbacks
   - 移除 `connect` 函數的不必要依賴
   - 新增空 URL 檢查避免無效連線

2. `diagram-context.tsx`:
   - 新增 `sendOperationResultRef` 避免 `handlePendingOperationsWS` 的循環依賴
   - 移除 `handleDiagramUpdateWS` 的 `loadDiagram` 依賴

**修復結果:**
- WebSocket 連線穩定維持
- 不再有不斷斷線重連的問題
- Fallback 機制正常運作

### 2. WebSocket 即時通訊系統 ✅

實作 WebSocket 取代 HTTP Polling，提供即時雙向通訊：

**架構:**
```
Browser ←WebSocket→ WS Server (6003) ←HTTP→ Next.js API (6002) ←HTTP→ MCP Server
```

**新增檔案:**
| 檔案 | 說明 |
|------|------|
| `lib/websocket/types.ts` | WebSocket 訊息類型定義 |
| `lib/websocket/server.ts` | WebSocket server 模組 |
| `lib/websocket/useWebSocket.ts` | React hook (瀏覽器端) |
| `lib/websocket/index.ts` | 模組匯出 |
| `scripts/ws-server.ts` | 獨立 WebSocket server |
| `test-websocket.py` | 整合測試腳本 |

**啟動方式:**
```bash
# 分開啟動
npm run dev:ws   # WebSocket server (port 6003/6004)
npm run dev      # Next.js (port 6002)

# 同時啟動
npm run dev:all
```

**訊息類型:**
| 類型 | 方向 | 說明 |
|------|------|------|
| `diagram_update` | Server→Client | 新圖表載入 |
| `pending_operations` | Server→Client | 待執行操作 |
| `changes_report` | Client→Server | 用戶變更報告 |
| `operation_result` | Client→Server | 操作執行結果 |
| `ping/pong` | 雙向 | 心跳檢測 |

**Fallback 機制:**
- WebSocket 連線時: 使用 WebSocket 即時通訊
- WebSocket 斷線時: 自動降級到 HTTP Polling (10秒間隔)

### 3. 增量編輯系統 ✅

差異式編輯，減少 XML token 消耗：

**前端:**
- `lib/diagram-diff-tracker.ts` - XML 差異追蹤
- `lib/diagram-operations-handler.ts` - 操作處理器

**後端:**
- `tools/diff_tools.py` - MCP 差異工具

### 4. Port 佔用問題 ✅

```bash
npm run dev:smart  # 自動處理 port 佔用
```

## Status
✅ WebSocket 連線穩定性修復完成
✅ WebSocket 即時通訊實作完成
✅ 增量編輯系統基礎設施完成
✅ Port 智能啟動腳本
✅ 整合測試通過 (test-websocket.py 4/4)
✅ 完整場景測試通過（畫貓成功！）
