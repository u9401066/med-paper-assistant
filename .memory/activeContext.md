# Active Context

## Current Focus
Draw.io WebSocket 即時通訊系統 - 取代 HTTP Polling

## Recent Changes (2025-12-01)

### 1. WebSocket 即時通訊系統 ✅ (NEW!)

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

### 2. 增量編輯系統 ✅ (昨日完成)

差異式編輯，減少 XML token 消耗：

**前端:**
- `lib/diagram-diff-tracker.ts` - XML 差異追蹤
- `lib/diagram-operations-handler.ts` - 操作處理器

**後端:**
- `tools/diff_tools.py` - MCP 差異工具

### 3. Port 佔用問題 ✅

```bash
npm run dev:smart  # 自動處理 port 佔用
```

## Status
✅ WebSocket 即時通訊實作完成
✅ 增量編輯系統基礎設施完成
✅ Port 智能啟動腳本
✅ 整合測試通過 (test-websocket.py 4/4)
⏳ 完整場景測試（貓 → 狗屋 → 走路）
