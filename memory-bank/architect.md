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

### MCP Server 架構
```
.vscode/mcp.json
├── mdpaper     # 主要 MCP (52 tools)
├── pubmed      # PubMed 搜尋 (9 tools)
└── drawio      # Draw.io 圖表 (15 tools)
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
