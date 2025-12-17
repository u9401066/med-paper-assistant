# Architect

## 系統架構

### 整體架構
```
med-paper-assistant/
├── src/med_paper_assistant/       # 核心程式碼
│   ├── domain/                    # 領域層 (DDD)
│   ├── application/               # 應用層
│   ├── infrastructure/            # 基礎設施層
│   ├── interfaces/mcp/            # MCP 介面
│   └── shared/                    # 共用模組
├── integrations/                  # 外部整合
│   ├── pubmed-search-mcp/         # PubMed 搜尋子模組
│   └── next-ai-draw-io/           # Draw.io 整合
├── memory-bank/                   # 專案記憶 (版控)
├── .github/bylaws/                # 子法規範
├── .claude/skills/                # Claude Skills
└── scripts/                       # 跨平台腳本
```

### MCP Server 架構 (2025-12-17 解耦後)
```
.vscode/mcp.json
├── mdpaper        # 主要 MCP (~45 tools) - 專案/草稿/參考/匯出/技能
├── pubmed-search  # PubMed 搜尋 (submodule)
├── cgu            # Creativity Generation (submodule)
├── zotero-keeper  # 書目管理 (uvx)
└── drawio         # Draw.io 圖表 (uvx)
```

**MCP 間通訊原則：**
- MCP 對 MCP 只要 API！
- 不直接 import 其他 MCP 的模組
- Agent (Copilot) 負責協調 MCP 間資料傳遞

**範例工作流程：**
```
用戶：「幫我儲存這篇 PMID:12345678」
1. Agent → pubmed-search: fetch_article_details(pmids="12345678")
2. Agent 取得 metadata dict
3. Agent → mdpaper: save_reference(article=<metadata>)
```

### 跨平台支援
- Windows: `.venv/Scripts/python.exe`
- Linux/macOS: `.venv/bin/python`
- 透過 mcp.json 的 `platforms` 配置自動切換

## 技術決策

### 2025-12-17: 跨平台架構
- 採用 VS Code MCP 的 platforms 配置
- setup.sh (Linux/macOS) + setup.ps1 (Windows) 並行維護

### 2025-12-03: Foam 整合
- 參考文獻使用 `[[author_year_pmid]]` 格式
- 自動建立 Foam alias 檔案

### 2025-12-02: 子模組獨立化
- pubmed-search-mcp 獨立為 Git 子模組
- 可單獨使用或整合
