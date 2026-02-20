# MedPaper Assistant - VS Code Extension

AI-powered medical paper writing assistant with MCP tools, prompts, and skills.

## Features

- � **Auto Paper** - 全自動 9-Phase 論文撰寫 + 3 層 Audit Hooks
- 🔍 **PubMed Literature Search** - Search and save references
- ✍️ **Draft Writing** - Write paper sections with citation-aware editing
- 💡 **Concept Development** - Develop and validate research novelty
- 📊 **Data Analysis** - Statistical tests, Table 1, visualizations
- 📄 **Word Export** - Export to journal-ready Word documents
- 🔔 **Dual-Hook Architecture** - Copilot Hooks (寫作時) + Pre-Commit Hooks (提交前)

## Installation

### From VSIX

```bash
code --install-extension medpaper-assistant-0.2.0.vsix
```

Or in VS Code: `Ctrl+Shift+P` → `Extensions: Install from VSIX...`

## Requirements

- VS Code 1.100.0 or higher
- GitHub Copilot (for Agent Mode)
- Python 3.11+ with `uv` (recommended)

## Quick Start

### 🚀 全自動寫論文 (Auto Paper)

1. 安裝擴充功能
2. 在 Agent Mode 輸入：「全自動寫論文」
3. 系統自動執行 9-Phase Pipeline：

| Phase | 名稱 | 說明 |
|-------|------|------|
| 1 | 文獻搜索 | 並行搜尋 + save_reference_mcp |
| 2 | 概念發展 | concept.md 撰寫 |
| 3 | Novelty 驗證 | 三輪評分 ≥ 75 |
| 4 | 專案建立 | paper type + sections |
| 5 | 逐節撰寫 | Introduction → Discussion |
| 6 | 引用同步 | sync_references |
| 7 | 全稿一致性 | manuscript consistency |
| 8 | Word 匯出 | 產生 .docx |
| 9 | Meta-Learning | 更新 SKILL.md |

## Usage

### Chat Commands (@mdpaper)

| 指令 | 說明 |
|------|------|
| `@mdpaper /autopaper` | 🚀 全自動寫論文 |
| `@mdpaper /search` | 搜尋 PubMed 文獻 |
| `@mdpaper /draft` | 撰寫論文章節 |
| `@mdpaper /concept` | 發展研究概念 |
| `@mdpaper /project` | 管理研究專案 |
| `@mdpaper /format` | 匯出 Word 文件 |
| `@mdpaper /analysis` | 資料分析與統計 |
| `@mdpaper /strategy` | 搜尋策略設定 |
| `@mdpaper /help` | 顯示所有指令 |

### Command Palette (Ctrl+Shift+P)

| 指令 | 說明 |
|------|------|
| `MedPaper: Auto Paper` | 全自動寫論文 |
| `MedPaper: Show Status` | 顯示擴充功能狀態 |

### Agent Mode 自然語言

直接在 Agent Mode 輸入：
- 「全自動寫論文」「一鍵寫論文」→ Auto Paper Pipeline
- 「找論文」「搜尋 PubMed」→ 文獻搜尋
- 「寫 Introduction」→ 草稿撰寫
- 「驗證 novelty」→ 概念驗證

## Architecture

```
Capability → Skill → Hook → MCP Tool
```

### 🔔 Dual-Hook System

| Hook | 時機 | 功能 |
|------|------|------|
| Copilot Hook A | 每段寫完 | 字數、引用密度、Anti-AI |
| Copilot Hook B | 每節寫完 | 概念一致性、🔒 保護內容 |
| Copilot Hook C | 全稿完成 | 全稿一致性 |
| Copilot Hook D | Pipeline 結束 | Meta-Learning |
| Pre-Commit P1-P7 | Git commit 前 | Safety net |

### Bundled Skills (14)

| 類別 | Skills |
|------|--------|
| 核心 | auto-paper, draft-writing, concept-development |
| 搜尋 | literature-review, parallel-search |
| 管理 | project-management, reference-management |
| 品質 | concept-validation, manuscript-review |
| 分析 | academic-debate, idea-validation |
| 匯出 | word-export, submission-preparation |
| Git | git-precommit (Paper-Aware P1-P7) |

### MCP Tools (53)

自動註冊 3 個 MCP Server：
- **MedPaper Assistant** - 53 工具（專案、文獻、寫作、分析、匯出）
- **CGU Creativity** - 創意發想工具
- **Draw.io Diagrams** - 圖表繪製

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `mdpaper.pythonPath` | Python 執行路徑 | Auto-detect (uv > venv > system) |
| `mdpaper.projectsDirectory` | 專案目錄 | Workspace |
| `mdpaper.defaultCitationStyle` | 引用風格 | vancouver |

## Development

```bash
# Clone
git clone https://github.com/u9401066/med-paper-assistant
cd med-paper-assistant/vscode-extension

# Install & Build
npm install
./scripts/build.sh    # Copies skills, prompts, Python source, compiles, packages

# Manual steps
npm run compile       # TypeScript only
npm run package       # Generate .vsix
```

## License

Apache-2.0
