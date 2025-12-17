# Active Context

## 當前焦點
MCP 架構解耦 + 程式碼清理

## 最近變更 (2025-12-17)

### 1. mdpaper MCP 解耦 ✅
**核心決策：MCP 對 MCP 只要 API！**

移除 mdpaper 對 pubmed_search 的所有直接 import：
- ❌ `infrastructure/external/entrez/` - 已刪除
- ❌ `infrastructure/external/pubmed/` - 已刪除  
- ❌ `infrastructure/services/strategy_manager.py` - 已刪除
- ❌ `interfaces/mcp/tools/search/` - 已刪除
- ❌ `application/use_cases/search_literature.py` - 已刪除

重構檔案：
- ✅ `infrastructure/__init__.py` - 移除 PubMedClient, StrategyManager
- ✅ `infrastructure/persistence/reference_manager.py` - 不再需要 searcher
- ✅ `interfaces/mcp/tools/reference/manager.py` - save_reference 改接受 dict
- ✅ `interfaces/mcp/tools/skill/__init__.py` - 修正 import 路徑

### 2. MCP Server 載入測試 ✅
```bash
.venv\Scripts\python.exe -c "from med_paper_assistant.interfaces.mcp.server import create_server; mcp = create_server()"
# ✅ MCP Server created successfully
```

### 3. 新的 MCP 架構
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  mdpaper MCP    │     │ pubmed-search   │     │ zotero-keeper   │
│  (本地儲存/草稿) │     │ MCP (文獻搜尋)   │     │ MCP (書目管理)   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   VS Code Copilot Agent │
                    │   (MCP 間協調)          │
                    └─────────────────────────┘
```

### 4. 跨平台支援 ✅
- uv 套件管理器
- Python >=3.11
- platforms 配置自動切換

## 相關檔案
- `src/med_paper_assistant/interfaces/mcp/server.py` - 主要 MCP 進入點
- `src/med_paper_assistant/infrastructure/persistence/reference_manager.py` - 重構後的參考文獻管理
- `.vscode/mcp.json` - 5 個 MCP Server 配置

## 待解決問題
- [ ] 清理已註解的 tools (review/, discussion/, validation/idea.py)
- [ ] 移除 deprecated save_reference_by_pmid_legacy
- [ ] 更新 .github/copilot-instructions.md 反映新 API

## 更新時間
2025-12-17 17:15
