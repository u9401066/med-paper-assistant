# Active Context

## Current Focus
Draw.io MCP Tools Enhancement - COMPLETED

## Recent Changes (2025-11-28)

### Draw.io MCP 智能圖表生成
- **問題**: `create_diagram` 只產生硬編碼模板，無法根據描述生成複雜圖表
- **解決方案**: 讓 Agent (Copilot) 直接生成 Draw.io XML，工具只負責發送到瀏覽器

#### 修改的檔案
1. `diagram_tools.py`:
   - 新增 `xml` 參數讓 Agent 可直接傳入 XML
   - 參數描述包含完整 Draw.io XML 格式說明
   - 新增 `display_xml_impl()` 和 `_send_xml_to_browser()` 函數
   - 修正提示訊息避免重複開啟瀏覽器

2. `web_client.py`:
   - 新增 `is_port_in_use()` 使用 socket 檢查 port
   - `is_running()` 增加重試機制和更長 timeout
   - `start_web_server()` 智能處理 port 佔用情況

3. `server.py`:
   - 移除預先啟動 Web 服務，改為 lazy start
   - 避免 MCP initialize 超時問題

### 新工作流程
```
用戶「畫研究路線圖」
    ↓
Copilot 讀取 concept.md
    ↓
Copilot 生成 Draw.io XML
    ↓
呼叫 create_diagram(xml=...) MCP 工具
    ↓
格式驗證 + 發送到瀏覽器
    ↓
圖表即時顯示
```

### 測試結果
- ✅ 畫一隻馬：成功生成馬的卡通圖
- ✅ 研究路線圖：成功生成 6 階段詳細路線圖並儲存

## Previous Session (2025-11-27)
- MCP Tools 模組化重構完成
- 29 個 Python 檔案，10 個模組目錄
- Git commit: dbf192e

## Status
✅ Draw.io MCP 智能圖表生成完成
✅ Web 服務啟動問題修正
✅ README 更新
⏳ Git commit and push pending
