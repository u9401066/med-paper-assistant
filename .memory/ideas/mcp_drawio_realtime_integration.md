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

## 2025-11-28 更新：MCP 啟動時自動啟動 Web + 分頁管理

### 新需求分析

1. **MCP 啟動時自動啟動 Draw.io Web**
   - Draw.io MCP 啟動時 → 自動執行 `npm run dev`
   - 確保 Next.js 服務在 MCP 工具可用前就緒

2. **Web 頁面一次只顯示一張圖**
   - 多張圖需要「分頁管理」
   - 每個分頁 = 一個獨立的圖表會話

3. **MCP 需要知道操作哪個分頁**
   - 新增 `tab_id` 概念
   - MCP 工具需支援指定目標分頁

### 架構設計

```
┌─────────────────────────────────────────────────────────────────┐
│                    VS Code MCP Host                              │
│  ┌─────────────────┐      ┌─────────────────┐                   │
│  │  mdpaper MCP    │      │  drawio MCP     │                   │
│  │  (46 tools)     │      │  (6+ tools)     │                   │
│  └─────────────────┘      └────────┬────────┘                   │
│                                    │                             │
│                                    │ 啟動時自動執行              │
│                                    ▼                             │
│                           ┌─────────────────┐                   │
│                           │ npm run dev     │                   │
│                           │ (subprocess)    │                   │
│                           └────────┬────────┘                   │
└────────────────────────────────────┼────────────────────────────┘
                                     │ HTTP API
                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                Next.js Draw.io App (port 6002)                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     Tab Manager                              ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        ││
│  │  │ Tab 1   │  │ Tab 2   │  │ Tab 3   │  │  + New  │        ││
│  │  │ active  │  │         │  │         │  │         │        ││
│  │  └────┬────┘  └─────────┘  └─────────┘  └─────────┘        ││
│  └───────┼──────────────────────────────────────────────────────┘│
│          ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Draw.io Editor (Current Tab)                    ││
│  │                                                              ││
│  │    ┌─────────┐    ┌─────────┐    ┌─────────┐               ││
│  │    │  Start  │───▶│ Process │───▶│   End   │               ││
│  │    └─────────┘    └─────────┘    └─────────┘               ││
│  │                                                              ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### API 設計更新

#### 1. 新增分頁管理 API (`/api/tabs`)

```typescript
// GET /api/tabs - 列出所有分頁
{
  "tabs": [
    { "id": "tab-1", "name": "CONSORT Flowchart", "active": true },
    { "id": "tab-2", "name": "Study Protocol", "active": false }
  ]
}

// POST /api/tabs - 建立新分頁
{ "action": "create", "name": "New Diagram" }
→ { "id": "tab-3", "name": "New Diagram" }

// POST /api/tabs - 切換分頁
{ "action": "switch", "id": "tab-2" }

// POST /api/tabs - 關閉分頁
{ "action": "close", "id": "tab-1" }
```

#### 2. 更新 MCP 工具

```python
@mcp.tool()
async def create_diagram(
    description: str,
    diagram_type: str = "flowchart",
    tab_id: Optional[str] = None,      # 指定分頁，None = 新開分頁
    tab_name: Optional[str] = None,    # 新分頁名稱
    send_to_browser: bool = True,
    output_path: Optional[str] = None
) -> str:
    """創建圖表，可指定顯示在哪個分頁"""

@mcp.tool()
async def list_tabs() -> str:
    """列出所有開啟的圖表分頁"""

@mcp.tool()
async def switch_tab(tab_id: str) -> str:
    """切換到指定分頁"""

@mcp.tool()
async def close_tab(tab_id: str) -> str:
    """關閉指定分頁"""

@mcp.tool()
async def edit_diagram(
    changes: str,
    tab_id: Optional[str] = None,  # None = 編輯當前活躍分頁
    file_path: Optional[str] = None
) -> str:
    """編輯指定分頁的圖表"""
```

### MCP 啟動自動啟動 Web 的實作

```python
# server.py

import subprocess
import time
import atexit

_web_process = None

def start_web_server():
    """啟動 Next.js Web 服務"""
    global _web_process
    
    # 檢查是否已經在運行
    try:
        response = httpx.get(f"{NEXTJS_URL}/api/health", timeout=2)
        if response.status_code == 200:
            return  # 已經在運行
    except:
        pass
    
    # 啟動 Next.js
    web_dir = Path(__file__).parent.parent.parent.parent.parent  # 到 next-ai-draw-io 根目錄
    _web_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=web_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # 等待啟動
    for _ in range(30):  # 最多等 30 秒
        try:
            response = httpx.get(f"{NEXTJS_URL}/api/health", timeout=1)
            if response.status_code == 200:
                print(f"✅ Draw.io Web 已啟動: {NEXTJS_URL}")
                return
        except:
            time.sleep(1)
    
    print("⚠️ Draw.io Web 啟動超時")

def stop_web_server():
    """停止 Web 服務"""
    global _web_process
    if _web_process:
        _web_process.terminate()
        _web_process = None

# MCP 啟動時自動啟動 Web
start_web_server()
atexit.register(stop_web_server)
```

### 前端分頁 UI 變更

```tsx
// components/tab-bar.tsx
export function TabBar({ tabs, activeTabId, onSwitch, onClose, onCreate }) {
  return (
    <div className="flex border-b bg-gray-50">
      {tabs.map(tab => (
        <div 
          key={tab.id}
          className={`px-4 py-2 cursor-pointer flex items-center gap-2 ${
            tab.id === activeTabId ? 'bg-white border-b-2 border-blue-500' : ''
          }`}
          onClick={() => onSwitch(tab.id)}
        >
          <span>{tab.name}</span>
          <button onClick={(e) => { e.stopPropagation(); onClose(tab.id); }}>×</button>
        </div>
      ))}
      <button onClick={onCreate} className="px-3 py-2 text-gray-500">+ New</button>
    </div>
  );
}
```

### 實作優先順序

1. **Phase 1: MCP 啟動自動啟動 Web** (最重要)
   - [ ] 修改 `server.py` 加入 `start_web_server()`
   - [ ] 加入健康檢查 API `/api/health`
   - [ ] 測試 MCP 啟動時 Web 自動啟動

2. **Phase 2: 基本分頁管理**
   - [ ] 新增 `/api/tabs` API
   - [ ] 前端 TabBar 組件
   - [ ] MCP `list_tabs`, `switch_tab` 工具

3. **Phase 3: 完整分頁操作**
   - [ ] `create_diagram` 支援 `tab_id` 參數
   - [ ] `edit_diagram` 支援指定分頁
   - [ ] 分頁狀態持久化

### 使用情境

```
User: 請為我的研究計畫生成 CONSORT 流程圖和研究設計圖

Copilot:
1. 調用 create_diagram(description="CONSORT flowchart...", tab_name="CONSORT")
   → 自動開啟瀏覽器 (如果還沒開)
   → 在 Tab 1 顯示 CONSORT 圖

2. 調用 create_diagram(description="Study protocol...", tab_name="Protocol")
   → 在 Tab 2 顯示研究設計圖

3. 用戶可在瀏覽器中：
   - 點擊 Tab 1 編輯 CONSORT 圖
   - 點擊 Tab 2 編輯研究設計圖
   - 手動儲存各圖

4. Copilot 需要編輯時：
   調用 edit_diagram(changes="修改...", tab_id="tab-1")
   → 切換到 Tab 1 並編輯
```

---

## 參考

- MCP Specification: https://modelcontextprotocol.io/
- VS Code Extension API: https://code.visualstudio.com/api
- Next.js WebSocket: https://nextjs.org/docs/app/building-your-application/routing/route-handlers
