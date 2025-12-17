# Decision Log

## [2025-12-17] 跨平台架構重構

### 背景
原專案在 Linux 環境開發，需要支援 Windows 開發環境。

### 選項
1. 維持 Linux only，使用 WSL
2. 重構為跨平台支援 (Windows/Linux/macOS)

### 決定
選擇方案 2：跨平台架構

### 理由
- 提高開發彈性
- 減少環境依賴
- VS Code MCP 支援 platforms 配置

### 影響
- `.vscode/mcp.json` 使用 platforms 配置
- `scripts/setup.sh` 和 `setup.ps1` 並行維護
- 路徑使用正斜線 `/` 以相容兩平台

---

## [2025-12-17] Memory Bank 統一化

### 背景
原本使用 `.memory/` 目錄，與 template 的 `memory-bank/` 不一致。

### 決定
統一使用 `memory-bank/` 目錄，並納入版本控制。

### 理由
- 與 template-is-all-you-need 一致
- 透過 bylaws 和 skills 強制寫入
- 便於協作和追蹤

### 影響
- 刪除 `.memory/` 目錄
- 更新所有引用路徑
- 更新 .gitignore 確保追蹤 memory-bank
| 2025-12-17 | 將 .agent_constitution.md 整合進正式 CONSTITUTION.md，版本升級至 v1.1.0 | Agent 行為規範和研究操作規則應納入專案憲法正式管理，避免分散在多個檔案造成維護困難。新增第四至六章涵蓋：Agent 行為規範、研究操作規則（含 Concept/Draft 流程）、互動指南。 |
| 2025-12-17 | 重構 integrations 為選擇性 submodule 架構 | 採用選擇性 submodule 策略：pubmed-search-mcp 和 CGU 作為 submodule（常改代碼），drawio 和 zotero-keeper 改用獨立 uvx 安裝（較少改動）。Python 版本升級至 >=3.11 以支援 CGU。 |
| 2025-12-17 | mdpaper MCP 完全解耦 pubmed_search 依賴 | **MCP 對 MCP 只要 API！** 移除 mdpaper 對 pubmed_search 的所有 import，改為透過 Agent 協調 MCP 間通訊。刪除：infrastructure/external/{entrez,pubmed}、services/strategy_manager.py、tools/search/、use_cases/search_literature.py。重構 ReferenceManager 接受 metadata dict 而非 PMID。 |
