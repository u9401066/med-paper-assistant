# Active Context

## Current Focus
Foam 整合完成 + pubmed-search-mcp 獨立 MCP server

## Recent Changes (2025-12-03)

### 1. Foam 整合 ✅ (LATEST!)

完整實作 Foam 參考文獻預覽功能：

**功能:**
```
save_reference(pmid="38049909")
    ↓
建立 references/
├── 38049909/content.md    ← 主內容
└── tang2023_38049909.md   ← Foam 別名
    ↓
在草稿中使用 [[tang2023_38049909]]
    ↓
滑鼠懸停即可看到：
- 標題、作者
- ⭐ 專案選擇的引用格式
- 所有其他格式
- 完整摘要
```

**修改的檔案:**
| 檔案 | 變更 |
|------|------|
| `reference_manager.py` | 新增 `_generate_citation_key()`, `_create_foam_alias()` |
| `reference_manager.py` | `_generate_content_md()` 支援 YAML frontmatter + 格式置頂 |
| `manager.py` | `set_citation_style()` 儲存到專案設定 |
| `project_manager.py` | 新增 `settings` dict 支援 |
| `README.md` | 完整 Foam 使用說明（中英文） |

### 2. pubmed-search-mcp 獨立 MCP Server ✅

在 `.vscode/mcp.json` 新增 pubmed server：
- 獨立的 PubMed 搜尋 MCP
- 使用子模組 `integrations/pubmed-search-mcp`
- 現在有 3 個 MCP servers: mdpaper, pubmed, drawio

## Recent Changes (2025-12-03) (earlier)

### 0. 推薦擴展 + Chonky 檔案瀏覽器 ✅ (LATEST!)

**README 更新:**
- 新增「推薦的 VS Code 擴展」區塊
- 推薦 Project Manager + Foam 擴展
- 提供快速安裝指令

**Dashboard 檔案瀏覽器規劃:**
使用現成的 [Chonky](https://chonky.io/) React 元件（不造輪子！）：
- 772 GitHub Stars
- 12k 週下載
- TypeScript 支援
- 支援拖放、Grid/List 視圖、鍵盤快捷鍵

**實作計劃:**
```
dashboard/
├── src/components/
│   └── FileBrowser.tsx  # 整合 Chonky
├── package.json         # 新增 chonky 依賴
```

**安裝:**
```bash
npm install chonky chonky-icon-fontawesome
```

### 1. Foam 整合規劃 ✅

調研 [Foam](https://github.com/foambubble/foam) VS Code 擴展，規劃未來整合：

**Foam 功能亮點:**
| 功能 | 對 MedPaper 的價值 |
|------|-------------------|
| **Wikilink 自動完成** | 快速連結參考文獻、研究筆記 |
| **Backlinks Panel** | 查看哪些筆記引用了當前文獻 |
| **Graph Visualization** | 視覺化研究主題之間的關聯 |
| **Orphan/Placeholder Detection** | 找出未連結的筆記或缺失的參考 |
| **Sync links on rename** | 重命名檔案時自動更新所有連結 |

**目前 MedPaper 缺少的:**
| 缺少功能 | 解決方案 |
|----------|----------|
| 專案檔案瀏覽器 | Dashboard 擴展或新元件 |
| 參考文獻之間的關聯 | Foam 的 Graph + Backlinks |
| 研究筆記連結 | Foam 的 Wikilink |

**Roadmap 更新:**
- 📋 Foam Integration - Wikilink 檢查、反向連結、知識圖譜
- 📋 Project File Manager - 視覺化檔案瀏覽器

### 1. pubmed-search-mcp 子模組獨立化 ✅

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
