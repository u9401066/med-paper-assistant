# Active Context

## 當前焦點
跨平台架構重構 + Memory Bank 統一化

## 最近變更 (2025-12-17)

### 1. 跨平台支援 ✅
- `.vscode/mcp.json` 使用 `platforms` 配置自動切換
- `scripts/setup.ps1` (Windows) 和 `scripts/setup.sh` (Linux/macOS) 並行維護
- README 新增 Windows/Linux/macOS 徽章

### 2. Memory Bank 統一化 ✅
- 從 `.memory/` 遷移到 `memory-bank/`
- 更新 `.gitignore` 確保 `memory-bank/` 被版控
- 更新 `.github/bylaws/memory-bank.md` 強制寫入位置

### 3. Template 整合 ✅
從 `template-is-all-you-need` 整合：
- `.github/bylaws/` - 子法規範
- `.claude/skills/` - Claude Skills
- `CONSTITUTION.md` - 專案憲法
- `AGENTS.md` - Agent 指引
- `.editorconfig` - 編輯器配置

## 相關檔案
- `.vscode/mcp.json` - MCP 跨平台配置
- `scripts/setup.ps1` - Windows 安裝腳本
- `scripts/setup.sh` - Linux/macOS 安裝腳本
- `memory-bank/` - 統一的記憶目錄
- `.github/bylaws/memory-bank.md` - Memory Bank 規範

## 待解決問題
- [ ] 測試 Windows 環境安裝
- [ ] 測試 MCP Server 啟動
- [ ] 驗證 Skills 觸發

## 上下文
本次改版主要目的是讓專案從 Linux-only 變成跨平台支援，
並整合 template-is-all-you-need 的 Skills 和 Bylaws 架構。

## 更新時間
2025-12-17 16:30
