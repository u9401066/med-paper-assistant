# MedPaper Assistant — Architecture

## Overview

MedPaper Assistant 是一個**以 Copilot Agent Mode 為核心的醫學論文寫作環境**。

它不是一個獨立的應用程式，而是一組 MCP Server + VS Code Extension + Copilot Skills，讓研究者在 VS Code 中完成從文獻搜尋到 Word/LaTeX 匯出的完整論文流程。

```
┌─────────────────────────────────────────────────────────────────┐
│  VS Code                                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Copilot Agent Mode（大腦 / 編排層）                       │  │
│  │  Skills + Prompts 定義 SOP                                │  │
│  └────────┬──────────┬──────────┬──────────┬─────────────────┘  │
│           │          │          │          │                     │
│      ┌────▼───┐ ┌────▼───┐ ┌───▼────┐ ┌──▼──────┐             │
│      │mdpaper │ │pubmed- │ │  cgu   │ │ drawio  │  MCP        │
│      │  MCP   │ │search  │ │  MCP   │ │  MCP    │  Servers    │
│      └────┬───┘ └────────┘ └────────┘ └─────────┘             │
│           │                                                     │
│      ┌────▼──────────────────────────────────────┐             │
│      │  projects/{slug}/                          │  Shared     │
│      │    concept.md · drafts/ · references/      │  Filesystem │
│      └───────────────────────────────────────────┘             │
│           │              │                                      │
│      ┌────▼───┐     ┌───▼──────┐                               │
│      │  Foam  │     │Dashboard │  VS Code Extensions            │
│      │ (refs) │     │(Next.js) │                                │
│      └────────┘     └──────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

**核心設計原則**：檔案系統是共享狀態。所有元件（MCP Server、Dashboard、Foam）讀寫同一個 `projects/` 目錄。

---

## MCP Server（DDD Architecture）

主要的 Python MCP Server，提供 53 個 tools。

### 層級結構

```
src/med_paper_assistant/
├── domain/                          # 領域層：純業務邏輯，無外部依賴
│   ├── entities/                    # 實體
│   │   ├── project.py              #   Project（專案）
│   │   ├── reference.py            #   Reference（文獻）
│   │   └── draft.py                #   Draft（草稿）
│   ├── value_objects/               # 值物件
│   │   ├── reference_id.py         #   ReferenceId（PMID > Zotero > DOI）
│   │   ├── citation.py             #   Citation
│   │   └── search_criteria.py      #   SearchCriteria（Pydantic）
│   ├── services/                    # 領域服務
│   │   ├── reference_converter.py  #   多來源文獻轉換
│   │   ├── novelty_scorer.py       #   新穎性評分
│   │   ├── citation_formatter.py   #   引用格式化
│   │   ├── wikilink_validator.py   #   [[wikilink]] 驗證
│   │   └── pre_analysis_checklist.py
│   └── paper_types.py              # 論文類型定義
│
├── application/                     # 應用層：Use Case 編排
│   └── use_cases/
│       ├── save_reference.py       #   儲存文獻（MCP-to-MCP 驗證流程）
│       └── create_project.py       #   建立專案
│
├── infrastructure/                  # 基礎設施層：外部世界的實作
│   ├── persistence/                 # 持久化
│   │   ├── project_manager.py      #   專案 CRUD + Exploration
│   │   ├── reference_manager.py    #   文獻存儲
│   │   ├── project_repository.py   #   專案 Repository
│   │   ├── reference_repository.py #   文獻 Repository
│   │   ├── file_storage.py         #   檔案儲存抽象
│   │   ├── workspace_state_manager.py  # 跨 Session 狀態
│   │   └── project_memory_manager.py   # AI 記憶管理
│   ├── services/                    # 外部服務
│   │   ├── drafter.py              #   草稿撰寫 + wikilink 引用
│   │   ├── formatter.py            #   引用格式化（Vancouver/APA/...）
│   │   ├── analyzer.py             #   統計分析 + Table 1
│   │   ├── concept_validator.py    #   概念驗證（Three Reviewers Model）
│   │   ├── word_writer.py          #   Word 文件操作
│   │   ├── template_reader.py      #   Word 模板解析
│   │   ├── exporter.py             #   Legacy Word 匯出
│   │   ├── foam_settings.py        #   Foam 設定動態更新
│   │   ├── pubmed_api_client.py    #   MCP-to-MCP HTTP client
│   │   ├── citation_assistant.py   #   引用助手
│   │   ├── concept_template_reader.py
│   │   └── prompts.py              #   Section 寫作指引
│   ├── external/                    # 外部 MCP 整合
│   ├── config.py                    # 配置
│   └── logging.py                   # 日誌
│
├── interfaces/                      # 介面層：MCP Protocol 對接
│   └── mcp/
│       ├── server.py               #   create_server() → FastMCP
│       ├── __main__.py             #   Entry point（python -m）
│       ├── config.py               #   SERVER_INSTRUCTIONS
│       ├── instructions.py         #   動態指令生成
│       ├── prompts/                #   MCP Prompts
│       └── tools/                  #   MCP Tools（7 groups）
│           ├── project/            #     CRUD, settings, exploration, diagrams
│           ├── reference/          #     save, search, format, citations
│           ├── draft/              #     write, read, cite, templates
│           ├── validation/         #     concept validation, novelty
│           ├── analysis/           #     stats, Table 1, plots
│           ├── review/             #     reviewer response, consistency
│           ├── export/             #     Word document pipeline
│           ├── discussion/         #     debate/discussion tools
│           └── _shared/            #     共用 helpers
│
└── shared/                          # 共用
    ├── constants.py
    └── exceptions.py
```

### 依賴方向

```
interfaces → application → domain ← infrastructure
     │              │          ↑           │
     │              │          │           │
     └── MCP ───────┘    純邏輯/無依賴  ───┘
```

- **Domain** 不依賴任何外部套件（除 Pydantic）
- **Application** 只依賴 Domain
- **Infrastructure** 實作 Domain 定義的介面
- **Interfaces** 將 MCP Protocol 對接到 Application/Infrastructure

---

## External MCP Servers

Copilot Agent Mode 同時連接多個 MCP Server：

| Server | 來源 | 用途 | Tools 數量 |
|--------|------|------|-----------|
| **mdpaper** | 本專案 | 專案管理、草稿、引用、匯出 | 53 |
| **pubmed-search** | `integrations/pubmed-search-mcp/` (submodule) | PubMed 文獻搜尋 | ~30 |
| **cgu** | `integrations/cgu/` (submodule) | 創意發想（快思慢想） | ~6 |
| **drawio** | `uvx drawio-mcp-server` | CONSORT/PRISMA 圖表 | ~5 |
| **zotero-keeper** | `uvx zotero-keeper` | Zotero 書目管理 | ~15 |

### MCP-to-MCP 通訊

文獻儲存採用**分層信任架構**，避免 Agent 幻覺污染書目資料：

```
Agent: "存這篇 PMID:24891204"
    │
    │  只傳 PMID + agent_notes
    ▼
mdpaper MCP: save_reference_mcp(pmid="24891204")
    │
    │  Direct HTTP API（不經過 Agent）
    ▼
pubmed-search MCP: /api/cached_article/24891204
    │
    │  回傳驗證過的 PubMed 資料
    ▼
Reference file:
  🔒 VERIFIED: title, authors, journal（PubMed 原始資料，不可修改）
  🤖 AGENT:    notes, relevance（AI 產生，清楚標記）
  ✏️ USER:     highlights（人類筆記，AI 不碰觸）
```

---

## VS Code Extension

[vscode-extension/](vscode-extension/) — TypeScript，提供三個功能：

1. **MCP Server 註冊**：自動啟動 mdpaper、cgu、drawio MCP servers
2. **Chat Participant**：`@mdpaper` with `/search`, `/draft`, `/concept`, `/project`, `/format`
3. **Commands**：`mdpaper.startServer`, `mdpaper.stopServer`, `mdpaper.showStatus`

---

## Foam Integration

Foam (VS Code extension) 提供論文引用的知識圖譜功能：

- 每篇文獻存為 Markdown note（含 YAML frontmatter）在 `projects/{slug}/references/{pmid}/`
- 草稿中用 `[[citation_key]]` wikilink 引用
- `Drafter.sync_references_from_wikilinks()` 掃描 wikilinks 產生 References section
- `foam_settings.py` 動態切換專案範圍（只顯示當前專案的引用圖譜）
- Hover preview 顯示論文摘要，autocomplete 補全論文標題

---

## Dashboard

[dashboard/](dashboard/) — Next.js + React + Tailwind，嵌入 VS Code Simple Browser：

- 專案切換 UI
- 寫作進度追蹤
- 內嵌 Draw.io 編輯器
- 與 MCP Server 共享同一個 `projects/` 目錄（直接讀檔案系統）

---

## Copilot Skills & Prompts

行為指引層（不是代碼，是 Copilot 的 SOP）：

| 類型 | 位置 | 數量 | 作用 |
|------|------|------|------|
| **Skills** | `.claude/skills/*/SKILL.md` | 26 | 單一任務的知識（如何組合 tools） |
| **Prompts** | `.github/prompts/*.prompt.md` | 15 | 高層編排（多 skill 組合的工作流程） |
| **Bylaws** | `.github/bylaws/*.md` | 4 | 規範（架構、git、memory、python 環境） |
| **Instructions** | `.github/copilot-instructions.md` | 1 | 全域指引入口 |

層級關係：
```
Capability (Prompt) = 編排多個 Skills 完成完整任務
Skill               = 知道如何使用多個 Tools
Tool                = 單一 MCP 操作
```

---

## Project Structure（每個研究專案）

```
projects/{slug}/
├── project.json          # 專案元資料（paper_type, sections, status）
├── concept.md            # 研究概念（NOVELTY STATEMENT, KEY SELLING POINTS）
├── .memory/              # AI 記憶
│   ├── activeContext.md  #   當前工作焦點
│   └── progress.md       #   研究進度
├── drafts/               # 論文草稿（Markdown）
├── references/           # 文獻（每個 PMID 一個子目錄）
│   └── {pmid}/
│       └── metadata.json
├── data/                 # 分析用 CSV
└── results/              # 匯出結果（.docx, figures）
```

---

## Key Workflows

### 1. 文獻搜尋 → 儲存

```
pubmed-search: search_literature(query)
    → Agent 選擇文獻
    → mdpaper: save_reference_mcp(pmid) → Direct API → 驗證資料存入 references/
```

### 2. 草稿撰寫

```
mdpaper: get_section_template(section)
    → Agent 撰寫內容
    → mdpaper: write_draft(filename, content)
    → 草稿中用 [[wikilink]] 引用文獻
    → mdpaper: sync_references() → 掃描 wikilinks → 產生 References section
```

### 3. Word 匯出

```
mdpaper: list_templates() → read_template()
    → mdpaper: start_document_session()
    → mdpaper: insert_section() × N
    → mdpaper: check_word_limits()
    → mdpaper: save_document()
```

### 4. 概念驗證

```
mdpaper: validate_concept(concept.md)
    → Three Reviewers Model（Methodology, Evidence, Clinical Impact）
    → Novelty Score ≥ 75 → 允許開始撰寫草稿
```

---

## Citation Styles

| Style | 範例 |
|-------|------|
| Vancouver | `[1] Kim SH, Lee JW. Title. Journal 2024; 1: 1-10.` |
| APA | `Kim, S.H., Lee, J.W. (2024). Title. *Journal*, 1, 1-10.` |
| Harvard | `Kim, S.H. (2024) 'Title', *Journal*, vol. 1, pp. 1-10.` |
| Nature | `1. Kim SH, Lee JW. Title. Journal 1, 1-10 (2024).` |
| AMA | `1. Kim SH, Lee JW. Title. Journal 1, 1-10 (2024).` |

---

## Dependencies

### Python (managed by uv)

| 套件 | 用途 |
|------|------|
| `mcp[cli]` | Model Context Protocol SDK |
| `python-docx` | Word 文件操作 |
| `pandas` | 資料分析 |
| `scipy` | 統計檢定 |
| `matplotlib` / `seaborn` | 繪圖 |
| `pydantic` | 資料驗證 |
| `tabulate` | 表格格式化 |
| `httpx` | MCP-to-MCP HTTP 通訊 |

### Dev Tools

| 工具 | 用途 |
|------|------|
| `uv` | 套件管理（唯一，禁止 pip） |
| `ruff` | Lint + Format |
| `mypy` | Type checking |
| `bandit` | Security scanning |
| `pytest` | Testing |
| `pre-commit` | Git hooks |

---

## Workspace Layout

```
med-paper-assistant/
├── src/med_paper_assistant/    # MCP Server（DDD）
├── integrations/               # 外部 MCP Servers（git submodules）
│   ├── pubmed-search-mcp/      #   PubMed 搜尋
│   └── cgu/                    #   創意發想
├── vscode-extension/           # VS Code Extension
├── dashboard/                  # Next.js Dashboard
├── templates/                  # Word 模板（.docx）
├── projects/                   # 研究專案（每個 slug 一個目錄）
├── tests/                      # 測試
├── scripts/                    # 工具腳本
├── docs/                       # 設計文件
├── memory-bank/                # 全域 AI 記憶
├── .claude/skills/             # Copilot Skills（26 個）
├── .github/prompts/            # Copilot Prompts（15 個）
├── .github/bylaws/             # 規範（4 個）
└── .pre-commit-config.yaml     # Git hooks
```
