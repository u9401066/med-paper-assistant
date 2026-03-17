# MedPaper Assistant - VS Code Extension

AI-powered medical paper writing assistant with MCP tools, prompts, and skills.

## Features

- � **Auto Paper** - 全自動 9-Phase 論文撰寫 + 3 層 Audit Hooks
- 🔍 **PubMed Literature Search** - Search and save references
- ✍️ **Draft Writing** - Write paper sections with citation-aware editing
- 💡 **Concept Development** - Develop and validate research novelty
- 📊 **Data Analysis** - Statistical tests, Table 1, visualizations
- 📄 **Word Export** - Export to journal-ready Word documents
- 🔔 **Dual-Hook Architecture** - 78 個品質檢查（55 Code-Enforced / 23 Agent-Driven）

## Installation

### From VSIX

```bash
code --install-extension medpaper-assistant-0.4.0.vsix
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
3. 系統自動執行 11-Phase Pipeline：

| Phase | 名稱          | 說明                             |
| ----- | ------------- | -------------------------------- |
| 1     | 文獻搜索      | 並行搜尋 + save_reference_mcp    |
| 2     | 全文閱讀      | asset-aware + fulltext           |
| 3     | 概念發展      | concept.md 撰寫                  |
| 4     | Novelty 驗證  | 三輪評分 ≥ 75                    |
| 5     | 逐節撰寫      | Introduction → Discussion        |
| 6     | 引用同步      | sync_references                  |
| 7     | 同行審查      | min_rounds=2 + R1-R6 gates       |
| 8     | 全稿一致性    | manuscript consistency           |
| 9     | 匯出          | docx + pdf（CRITICAL Gate）      |
| 10    | Meta-Learning | D1-D9 自我改進                   |
| 11    | 提交          | git commit+push（CRITICAL Gate） |

## Usage

### Chat Commands (@mdpaper)

| 指令                  | 說明             |
| --------------------- | ---------------- |
| `@mdpaper /autopaper` | 🚀 全自動寫論文  |
| `@mdpaper /search`    | 搜尋 PubMed 文獻 |
| `@mdpaper /draft`     | 撰寫論文章節     |
| `@mdpaper /concept`   | 發展研究概念     |
| `@mdpaper /project`   | 管理研究專案     |
| `@mdpaper /format`    | 匯出 Word 文件   |
| `@mdpaper /analysis`  | 資料分析與統計   |
| `@mdpaper /strategy`  | 搜尋策略設定     |
| `@mdpaper /help`      | 顯示所有指令     |

### Command Palette (Ctrl+Shift+P)

| 指令                    | 說明             |
| ----------------------- | ---------------- |
| `MedPaper: Auto Paper`  | 全自動寫論文     |
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

### 🔔 Hook Architecture（78 checks — 55 Code-Enforced / 23 Agent-Driven）

| Hook             | 時機            | 功能                                         |
| ---------------- | --------------- | -------------------------------------------- |
| Copilot A1-7+A3b | 每段寫完        | 字數、引用密度、Anti-AI、語言一致、B2 🔒保護 |
| Copilot B1-16    | 每節寫完        | 概念一致、統計、時態、段落品質               |
| Copilot C1-13    | 全稿完成        | 全稿一致性、C2 投稿清單、引用分布、圖表品質  |
| Copilot D1-D9    | Phase 10        | MetaLearningEngine 自我改進                  |
| Copilot E1-5     | Phase 7 每輪    | EQUATOR 報告指引                             |
| Copilot F1-4     | post-manuscript | DataArtifactTracker                          |
| Review R1-R6     | Phase 7 submit  | ReviewHooksEngine 審查品質 HARD GATE         |
| General G9       | pre-commit      | Git 狀態檢查                                 |
| Pre-Commit P1-P8 | Git commit 前   | Safety net + P6 記憶同步                     |
| General G1-G8    | Git commit 前   | Memory、README、CHANGELOG 等                 |

### Bundled Skills (26)

| 類別 | Skills                                                      |
| ---- | ----------------------------------------------------------- |
| 核心 | auto-paper, draft-writing, concept-development              |
| 搜尋 | literature-review, parallel-search                          |
| 管理 | project-management, reference-management, project-init      |
| 品質 | concept-validation, manuscript-review                       |
| 分析 | academic-debate, idea-validation                            |
| 匯出 | word-export, submission-preparation                         |
| Git  | git-precommit (P1-P8), git-doc-updater                      |
| 維護 | memory-updater, memory-checkpoint, changelog-updater        |
| 開發 | ddd-architect, code-refactor, code-reviewer, test-generator |
| 文件 | readme-updater, readme-i18n, roadmap-updater                |

### MCP Tools (88)

自動註冊 MCP Server：

- **MedPaper Assistant** - 88 工具（project/17, reference/12, draft/13, validation/3, analysis/10, review/23, export/10）
- **CGU Creativity** - 創意發想工具
- **Draw.io Diagrams** - 圖表繪製

## Configuration

| Setting                        | Description     | Default                          |
| ------------------------------ | --------------- | -------------------------------- |
| `mdpaper.pythonPath`           | Python 執行路徑 | Auto-detect (uv > venv > system) |
| `mdpaper.projectsDirectory`    | 專案目錄        | Workspace                        |
| `mdpaper.defaultCitationStyle` | 引用風格        | vancouver                        |

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
