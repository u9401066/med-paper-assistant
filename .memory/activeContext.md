# Active Context

## Current Focus
Draw.io 增量編輯系統 (Incremental Editing) - 減少 XML Token 消耗

## Recent Changes (2025-12-01)

### 1. 增量編輯系統實作 ✅

實作差異式編輯，取代每次全量 XML 傳輸：

**設計文件:**
| 文件 | 說明 |
|------|------|
| `docs/INCREMENTAL_EDITING_RFC.md` | 設計 RFC |
| `docs/DIFF_COMMUNICATION_DESIGN.md` | 雙向 Diff 通訊設計 |

**前端新增:**
| 檔案 | 說明 |
|------|------|
| `lib/diagram-diff-tracker.ts` | XML 差異追蹤器 |
| `lib/diagram-operations-handler.ts` | 增量操作處理器 |
| `contexts/diagram-context.tsx` | 整合 diff 追蹤 + 輪詢 |

**後端新增:**
| 檔案 | 說明 |
|------|------|
| `tools/diff_tools.py` | MCP 差異工具 |
| `web_client.py` | 新增 diff API 方法 |

**API 端點 (route.ts):**
| 端點 | 說明 |
|------|------|
| `GET ?action=get_changes` | 取得用戶變更 |
| `GET ?action=check_pending_ops` | 檢查待執行操作 |
| `POST apply_operations` | 應用增量操作 |
| `POST report_changes` | 回報用戶變更 |
| `POST sync_diff_state` | 同步 diff 狀態 |

### 2. Port 佔用問題解決 ✅

創建智能啟動腳本自動處理 port 佔用：

```bash
# 新命令
npm run dev:smart

# 或直接
./scripts/start-dev.sh 6002
```

**新增檔案:**
- `scripts/start-dev.sh` - 智能啟動腳本

### 3. 差異操作類型

```typescript
type DiagramOperation = 
  | 'add_node'     // 新增節點
  | 'modify_node'  // 修改節點
  | 'delete_node'  // 刪除節點
  | 'add_edge'     // 新增連線
  | 'modify_edge'  // 修改連線
  | 'delete_edge'; // 刪除連線
```

### 4. 輪詢機制

前端每 2 秒檢查待執行操作，每 3 秒回報變更：
```typescript
// diagram-context.tsx
useEffect(() => {
  const opsInterval = setInterval(checkAndApplyPendingOperations, 2000);
  const changesInterval = setInterval(reportChangesToServer, 3000);
  // ...
}, []);
```

## Previous Session (2025-11-29)

### 繪圖指南工具 ✅
- `get_drawing_guidelines` - 取得繪圖最佳實踐
- `get_style_string` - 生成 style 字串
- `list_available_styles` - 列出可用樣式

### 上游同步 ✅
從 DayuanJiang/next-ai-draw-io 合併改進：
- maxDuration: 60 → 300 秒
- 空內容過濾（Bedrock API 相容）
- 複製按鈕

## Status
✅ 增量編輯系統基礎設施完成
✅ Port 智能啟動腳本
✅ 測試通過 (simple-test.py)
⏳ 完整場景測試（貓 → 狗屋 → 走路）
⏳ 考慮 WebSocket 替代 Polling
