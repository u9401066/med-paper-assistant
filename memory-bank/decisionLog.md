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
