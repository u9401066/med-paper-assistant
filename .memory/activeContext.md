# Active Context

## Current Focus
pubmed-search-mcp 子模組獨立化 + 工具架構重構

## Recent Changes (2025-12-02)

### 1. pubmed-search-mcp 子模組獨立化 ✅ (LATEST!)

將 PubMed 搜尋功能抽取為獨立的 Git 子模組：

**架構:**
```
med-paper-assistant/
└── integrations/
    └── pubmed-search-mcp/     # Git 子模組
        └── src/pubmed_search/
            ├── entrez/         # Entrez API 核心
            ├── client.py       # PubMedClient
            └── mcp/            # 獨立 MCP Server
                ├── server.py   # create_server()
                ├── tools.py    # 9 個搜尋工具
                └── strategy.py # StrategyManager
```

**子模組功能:**
| 工具 | 說明 |
|------|------|
| `search_literature` | PubMed 搜尋 |
| `find_related_articles` | 找相關文章 |
| `find_citing_articles` | 找引用文章 |
| `fetch_article_details` | 取得文章詳情 |
| `configure_search_strategy` | 設定搜尋策略 |
| `get_search_strategy` | 取得搜尋策略 |
| `generate_search_queries` | 生成並行查詢 |
| `merge_search_results` | 合併結果 |
| `expand_search_queries` | 擴展搜尋 |

**獨立使用:**
```bash
pip install pubmed-search[mcp]
python -m pubmed_search.mcp your@email.com
```

**整合使用:**
```python
from pubmed_search.mcp import register_search_tools
register_search_tools(mcp_server, searcher, strategy_manager)
```

### 2. 工具架構重構 ✅

從 56 個工具精簡為 52 個，更清晰的分類：

| 類別 | 工具數 | 說明 |
|------|--------|------|
| **PROJECT** | 15 | 專案管理、探索、圖表 |
| **WRITING** | 16 | 草稿、模板、驗證、匯出 |
| **SEARCH** | 10 | PubMed 搜尋 (子模組) |
| **REFERENCE** | 8 | 參考文獻、引用 |
| **SKILL** | 3 | 工作流程技能 |

**變更:**
- ❌ 移除 `analysis/` → 獨立 data-analysis-mcp 專案
- ❌ 移除 `diagram/` → 整合到 `project/diagrams.py`
- ✅ 搜尋功能使用 pubmed-search-mcp 子模組

### 3. Skills 技能系統 ✅ (Previous)

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
