# MCP + Draw.io 即時互動整合架構

## 問題分析

### 現狀
```
User Request → mdpaper MCP → drawio MCP → 產生 .drawio 檔案
                                              ↓
                              需要手動開 http://localhost:6002 查看
```

### 理想流程
```
User Request → mdpaper MCP → drawio MCP → 即時顯示在瀏覽器
                                              ↓
                              用戶可以在 Draw.io 編輯器中互動修改
                                              ↓
                              修改後自動儲存回 .drawio 檔案
```

## 技術挑戰

### 1. MCP 無法直接控制瀏覽器
- MCP 是 server-side 工具
- 無法主動開啟/控制 VS Code Simple Browser
- 需要 VS Code Extension API 或其他機制

### 2. 跨 MCP 通訊
- `mdpaper` MCP 需要調用 `drawio` MCP
- 目前沒有 MCP-to-MCP 直接調用機制
- Copilot Agent 是中間協調者

## 解決方案選項

### Option A: VS Code Extension 整合 (推薦)
```
med-paper-assistant VSCode Extension
    ├── 監聽 MCP 事件
    ├── 自動開啟 Simple Browser
    └── 管理 Draw.io 會話
```

**實作方式**:
1. 建立 VS Code Extension
2. Extension 監聽特定檔案變更 (`.drawio` 在 results/ 目錄)
3. 檔案變更時自動在 Simple Browser 開啟
4. 或透過 WebSocket 與 Next.js 即時通訊

### Option B: Next.js WebSocket 推送
```
drawio MCP → 產生圖表 → POST to Next.js API
                              ↓
                    Next.js 透過 WebSocket 推送到瀏覽器
                              ↓
                    Draw.io 編輯器即時更新
```

**實作方式** (next-ai-draw-io 已部分支援):
1. MCP 呼叫 Next.js API endpoint
2. Next.js 儲存圖表並通知前端
3. 前端 Draw.io 編輯器自動載入新圖表

### Option C: 檔案監控 + 自動重載
```
drawio MCP → 產生 .drawio 檔案
                 ↓
     Next.js 監控目錄變化 (chokidar/fs.watch)
                 ↓
     偵測到新檔案 → 自動載入到編輯器
```

**實作方式**:
1. Next.js 後端監控指定目錄
2. 新 .drawio 檔案出現時，透過 WebSocket 通知前端
3. 前端自動載入並顯示

### Option D: mdpaper MCP 內建 Draw.io 調用
```python
# 在 mdpaper MCP 中新增工具
@mcp.tool()
async def create_study_flowchart(concept_file: str):
    """Generate study flowchart from concept.md and display in browser"""
    
    # 1. 讀取 concept.md
    concept = read_concept(concept_file)
    
    # 2. 調用 drawio API (HTTP)
    response = await httpx.post(
        "http://localhost:6002/api/create-diagram",
        json={
            "description": generate_flowchart_prompt(concept),
            "output_path": f"{project_dir}/results/flowchart.drawio"
        }
    )
    
    # 3. 返回結果，讓 Copilot 開啟瀏覽器
    return {
        "status": "success",
        "file": output_path,
        "browser_url": "http://localhost:6002"  # 提示 Copilot 開啟
    }
```

## 推薦方案

### 短期 (現在可做): Option B + D
1. **修改 next-ai-draw-io**: 
   - 確保 `/api/mcp` 可以接收圖表並即時顯示
   - 加入 WebSocket 即時更新

2. **修改 drawio MCP**:
   - `create_diagram` 成功後自動發送到瀏覽器
   - 返回 `browser_url` 提示用戶/Copilot 開啟

3. **Copilot Agent 自動開啟瀏覽器**:
   - 當 drawio MCP 返回 `browser_url` 時
   - Agent 自動呼叫 `open_simple_browser`

### 長期: Option A (VS Code Extension)
1. 建立 `med-paper-assistant` VS Code Extension
2. 整合 MCP Server 管理
3. 自動開啟/管理 Draw.io 瀏覽器視窗
4. 提供更好的 UX

## 實作優先順序

1. **Phase 1**: 修改 drawio MCP 的 `create_diagram`
   - 確保圖表發送到 Next.js 即時顯示
   - 這部分 **已經在做** (`send_to_browser=true`)

2. **Phase 2**: 修改 Copilot Agent 行為
   - 在 `instructions.py` 中加入指引
   - 當生成圖表後自動開啟瀏覽器

3. **Phase 3**: 建立 VS Code Extension
   - 完整的整合體驗
   - 自動化流程

## 程式碼變更位置

### next-ai-draw-io (submodule)
```
mcp-server/src/drawio_mcp_server/
├── server.py          ← 修改 create_diagram 邏輯
└── api_client.py      ← 確保 HTTP 推送正確

app/api/mcp/
├── route.ts           ← 處理 MCP 推送
└── [確保 WebSocket 連接]
```

### med-paper-assistant
```
src/med_paper_assistant/interfaces/mcp/
├── instructions.py    ← 加入 drawio 使用指引
└── [未來可加入 diagram_tools.py]
```

## 下一步行動

1. [ ] 檢查 next-ai-draw-io 的 `/api/mcp` 實作
2. [ ] 確認 WebSocket 即時推送是否正常
3. [ ] 測試 `send_to_browser=true` 參數
4. [ ] 在 instructions.py 加入使用指引
5. [ ] 考慮是否需要 VS Code Extension

---

## 參考

- MCP Specification: https://modelcontextprotocol.io/
- VS Code Extension API: https://code.visualstudio.com/api
- Next.js WebSocket: https://nextjs.org/docs/app/building-your-application/routing/route-handlers
