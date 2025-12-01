# Active Context

## Current Focus
Draw.io WebSocket 即時通訊系統 - 穩定性修復完成

## Recent Changes (2025-12-01)

### 1. WebSocket 連線穩定性修復 ✅ (LATEST!)

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
