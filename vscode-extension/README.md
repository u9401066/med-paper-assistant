# MedPaper Assistant - VS Code Extension

AI-powered medical paper writing and literature wiki assistant with MCP tools, prompts, and skills.

![MedPaper Assistant marketplace banner](https://raw.githubusercontent.com/u9401066/med-paper-assistant/master/vscode-extension/resources/marketplace-banner.png)

## Features

- **Auto Paper** - 全自動 11-Phase 論文撰寫 + 3 層 Audit Hooks
- 🔍 **PubMed Literature Search** - Search and save references
- ✍️ **Draft Writing** - Write paper sections with citation-aware editing
- 💡 **Concept Development** - Develop and validate research novelty
- 📊 **Data Analysis** - Statistical tests, Table 1, visualizations
- 📄 **Word Export** - Export to journal-ready Word documents
- 📚 **LLM Wiki / Library Wiki Path** - inbox/concepts/projects note triage, dashboards, and managed Foam graph views
- 🔔 **Dual-Hook Architecture** - 78 個品質檢查（55 Code-Enforced / 23 Agent-Driven）

## Installation

### From VSIX

```bash
code --install-extension medpaper-assistant-0.7.1.vsix
```

Or in VS Code: `Ctrl+Shift+P` → `Extensions: Install from VSIX...`

## Requirements

- VS Code 1.100.0 or higher
- GitHub Copilot (for Agent Mode)
- Python 3.12+ with `uv` (recommended for full MedPaper repo parity; CGU itself supports 3.11+)

## MCP Installation Behavior

- MCP Python tools are installed persistently per machine with `uv tool install`, not once per folder.
- On later MedPaper extension updates, existing managed tools are checked with `uv tool upgrade` so older installs can move forward without manual reinstall.
- If another installed VS Code extension already provides `PubMed Search` or `Zotero Keeper` MCP servers, MedPaper skips both persistent tool installation and MCP registration for those servers to avoid duplicated tools.
- A workspace-level `.vscode/mcp.json` still has highest priority. If the workspace already manages `mdpaper` itself, MedPaper skips auto-registration.
- CGU is registered only when bundled CGU code or a workspace `integrations/cgu` submodule is present. If CGU is absent, MedPaper continues without it.
- Draw.io fallback uses `npx -y @drawio/mcp`, so Node.js/npm must be installed if you rely on the npm path.

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

| 指令                  | 說明              |
| --------------------- | ----------------- |
| `@mdpaper /autopaper` | 🚀 全自動寫論文   |
| `@mdpaper /search`    | 搜尋 PubMed 文獻  |
| `@mdpaper /draft`     | 撰寫論文章節      |
| `@mdpaper /concept`   | 發展研究概念      |
| `@mdpaper /project`   | 管理研究專案      |
| `@mdpaper /format`    | 匯出 Word 文件    |
| `@mdpaper /drawio`    | 開啟 Draw.io 圖表 |
| `@mdpaper /analysis`  | 資料分析與統計    |
| `@mdpaper /strategy`  | 搜尋策略設定      |
| `@mdpaper /help`      | 顯示所有指令      |

### Command Palette (Ctrl+Shift+P)

| 指令                                  | 說明                                    |
| ------------------------------------- | --------------------------------------- |
| `MedPaper: Start MedPaper MCP Server` | 顯示 MCP 啟動說明                       |
| `MedPaper: Stop MedPaper MCP Server`  | 顯示 MCP 停止說明                       |
| `MedPaper: Auto Paper`                | 全自動寫論文                            |
| `MedPaper: Show Status`               | 顯示擴充功能狀態                        |
| `MedPaper: Setup Workspace`           | 複製 skills、prompts、agents、support docs/files、templates |
| `MedPaper: Open LLM Wiki Guide`       | 直接開啟 `docs/how-to/llm-wiki.md`      |
| `MedPaper: Show Foam Graph: Default`  | 開啟預設 Foam 圖譜切片                  |
| `MedPaper: Show Foam Graph: Evidence` | 開啟 evidence 導向圖譜切片              |
| `MedPaper: Show Foam Graph: Writing`  | 開啟 writing 導向圖譜切片               |
| `MedPaper: Show Foam Graph: Assets`   | 開啟 figure/table 資產圖譜切片          |
| `MedPaper: Show Foam Graph: Review`   | 開啟 review / pending 狀態圖譜切片      |

### Agent Mode 自然語言

直接在 Agent Mode 輸入：

- 「全自動寫論文」「一鍵寫論文」→ Auto Paper Pipeline
- 「找論文」「搜尋 PubMed」→ 文獻搜尋
- 「寫 Introduction」→ 草稿撰寫
- 「驗證 novelty」→ 概念驗證

### Workflow Modes

- **Library Wiki Path**：建立 `workflow_mode="library-wiki"` 專案後，先做文獻保存、筆記 triage、dashboard 與 Foam graph 巡覽。
- **Manuscript Path**：建立 `workflow_mode="manuscript"` 專案後，走 concept → draft → review → export。
- 建議順序：先用 Library Wiki Path 累積與整理知識，再切去 Manuscript Path 正式寫稿。

## Architecture

```text
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

### Bundled Assets

The marketplace package bundles **14 skills**, **13 prompt workflows**, **9 reviewer/analysis agents**, **1 journal profile template**, and **7 support/reference files**. The full repository still contains a broader authoring and maintenance surface.

| 類別       | Skills                                                                                       |
| ---------- | -------------------------------------------------------------------------------------------- |
| 核心       | auto-paper, draft-writing, project-management                                                |
| 搜尋       | literature-review, parallel-search, reference-management                                     |
| 概念與審查 | concept-development, concept-validation, academic-debate, idea-validation, manuscript-review |
| 交付       | word-export, submission-preparation                                                          |
| 安全       | git-precommit                                                                                |

Bundled prompt workflows: `mdpaper.write-paper`, `mdpaper.literature-survey`, `mdpaper.manuscript-revision`, `mdpaper.search`, `mdpaper.concept`, `mdpaper.draft`, `mdpaper.project`, `mdpaper.format`, `mdpaper.strategy`, `mdpaper.analysis`, `mdpaper.clarify`, `mdpaper.help`, `mdpaper.audit`.

Bundled reviewer/analysis agents: `concept-challenger`, `domain-reviewer`, `literature-searcher`, `meta-learner`, `methodology-reviewer`, `paper-reviewer`, `reference-analyzer`, `review-orchestrator`, `statistics-reviewer`.

Bundled support/reference files: `.github/prompts/_capability-index.md`, `.github/copilot-instructions.md`, `.copilot-mode.json`, `docs/reference/foam.md`, `docs/reference/llm-wiki.md`, `docs/how-to/llm-wiki.md`, `docs/assets/medpaper_llm_wiki_workflow_clean.png`.

That means a VSIX-only user can now run `MedPaper: Setup Workspace` and receive the Foam dependency reference, the LLM wiki reference/how-to docs, and the workflow figure directly under `docs/` in their workspace.

### MCP Tools (115 full / 21 compact default)

自動註冊 MCP Server：

- **MedPaper Assistant** - 預設 compact 21 工具（可切換 full 115），另含 3 個 MCP prompts 與 3 個 MCP resources
- **CGU Creativity** - 創意發想工具
- **PubMed Search** - 文獻搜尋工具，若未被其他已安裝 VS Code 擴充功能提供才會由 MedPaper 註冊
- **Zotero Keeper** - Zotero 文獻工具，若未被其他已安裝 VS Code 擴充功能提供才會由 MedPaper 註冊
- **Draw.io Diagrams** - 圖表繪製

預設 `compact` 走 facade-first surface，保留 `project_action`、`library_action`、`draft_action`、`validation_action`、`run_quality_checks`、`pipeline_action`、`export_document`、`inspect_export` 等高階入口。若你要在 VSIX 版直接跑 full-surface 的 agent wiki workflow，請把 `mdpaper.toolSurface` 切成 `full`；這會額外暴露 `import_local_papers`、`ingest_web_source`、`ingest_markdown_source`、`resolve_reference_identity`、`build_knowledge_map`、`build_synthesis_page`、`materialize_agent_wiki` 等 granular orchestration 工具。

MCP prompts: `project_bootstrap`, `draft_section_plan`, `word_export_checklist`.

MCP resources: `medpaper://workspace/state`, `medpaper://workspace/projects`, `medpaper://templates/catalog`.

## Configuration

| Setting                        | Description     | Default                          |
| ------------------------------ | --------------- | -------------------------------- |
| `mdpaper.pythonPath`           | Python 執行路徑 | Auto-detect (uv > venv > system) |
| `mdpaper.projectsDirectory`    | 專案目錄        | Workspace                        |
| `mdpaper.toolSurface`          | MCP 工具面      | compact                          |
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
npm run validate      # Cross-platform bundle sync / package consistency checks
npm run package       # Generate .vsix
```

`npm run validate` automatically selects the PowerShell validator on Windows and the shell validator on Unix-like systems, so the same command can be used locally and in CI.

## License

Apache-2.0
