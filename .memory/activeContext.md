# Active Context

## Current Focus
- MCP Server for VS Code + GitHub Copilot (Modular Architecture)
- Research project: Trachway vs Fiberscope for nasotracheal intubation
- Draft prompt now MANDATES concept file for innovation preservation

## Architecture (Refactored + Enhanced)
```
src/med_paper_assistant/mcp_server/
├── server.py           # Entry point (~90 lines)
├── config.py           # Configuration & constants
├── tools/              # 33 tools in 5 modules
│   ├── search.py       # Literature search (6 tools) +2
│   ├── reference.py    # Reference management (8 tools) +4
│   ├── draft.py        # Draft writing (5 tools)
│   ├── analysis.py     # Data analysis (4 tools)
│   └── export.py       # Word export (10 tools)
└── prompts/
    └── prompts.py      # 6 guided workflow prompts
```

## MCP Prompts (6 total)
| Command | Argument | Description |
|---------|----------|-------------|
| `/mdpaper.concept` | topic | Develop research concept |
| `/mdpaper.strategy` | keywords | Configure search strategy |
| `/mdpaper.draft` | section | Write paper draft ⚠️ REQUIRES concept file |
| `/mdpaper.analysis` | - | Analyze data (auto-lists files) |
| `/mdpaper.clarify` | - | Refine content |
| `/mdpaper.format` | - | Export to Word (8-step workflow) |

## MCP Tools (33 total)
**Search (5)**: search_literature, configure_search_strategy, get_search_strategy, find_related_articles, find_citing_articles
**Reference (8)**: save_reference, list_saved_references, search_local_references, get_reference_details, read_reference_fulltext, retry_pdf_download, format_references, set_citation_style
**Draft (8)**: write_draft, read_draft, list_drafts, insert_citation, draft_section, get_section_template, count_words, validate_concept
**Analysis (4)**: analyze_dataset, run_statistical_test, create_plot, generate_table_one
**Export (8)**: read_template, list_templates, start_document_session, insert_section, verify_document, check_word_limits, save_document, export_word

## Current Research Project
- **Topic**: Trachway rigid video stylet vs Fiberoptic bronchoscope for NTI
- **Concept file**: drafts/concept_nasotracheal_intubation.md (1014 words)
- **Introduction draft**: drafts/introduction_nasotracheal.md (620 words, 5 citations)
- **Saved references**: 16 PMIDs in references/

## Recent Changes (2025-11-25)
- ✅ Major refactor: Modular architecture (tools/, prompts/, config.py)
- ✅ ARCHITECTURE.md documentation added
- ✅ Draft prompt now MANDATES concept file (checks drafts/ for *concept*.md)
- ✅ 27 tools, 6 prompts
- ✅ Restored scripts/setup.sh (was accidentally deleted)

## Recent Changes (Reference Enhancement)
- ✅ Enhanced metadata format with pre-formatted citations (Vancouver, APA, Nature, in-text)
- ✅ PDF fulltext download from PMC Open Access
- ✅ New tools: `get_reference_details`, `read_reference_fulltext`, `retry_pdf_download`
- ✅ New tools: `find_related_articles`, `find_citing_articles`
- ✅ Rich metadata: DOI, PMC ID, MeSH terms, keywords, volume/issue/pages
- ✅ Dependencies: Added `requests`, `pypdf` to pyproject.toml
- ✅ Total tools: 33

## Recent Changes (Agent Instructions Enhancement)
- ✅ Expanded SERVER_INSTRUCTIONS with detailed tool selection guide
- ✅ Added decision tree for quick tool selection
- ✅ Organized 32 tools into 5 categories with usage tables
- 🔜 **FUTURE**: Consider tool naming convention for grouping (ref_*, search_*, data_*, etc.)

---

## 🎯 Concept Enhancement Design Plan

### Problem Statement
當前的 concept 開發流程缺乏對創新性 (novelty) 和核心賣點 (selling points) 的結構化保護機制，
導致在後續 draft 撰寫過程中，這些關鍵內容可能被意外修改或淡化。

### Design Goals
1. **Novelty Preservation**: 確保研究創新性不會在撰寫過程中流失
2. **Selling Points Protection**: 保護用戶定義的核心賣點
3. **Structured Template**: 提供清晰的 concept 模板，區分可修改與受保護區域
4. **Agent Guidance**: 引導 Agent 在修改受保護內容前必須詢問確認

### Selected Approaches (Combined)

#### Approach 1: Structured Concept Template
- 創建 `templates/concept_template.md`
- 使用 `🔒` 標記受保護區塊
- 使用 `📝` 標記可修改區塊
- 區塊類型：
  - `🔒 NOVELTY STATEMENT`: 研究創新性聲明（受保護）
  - `🔒 KEY SELLING POINTS`: 核心賣點（用戶定義，受保護）
  - `📝 Background`: 背景資料（可修改）
  - `📝 Research Gap`: 研究缺口（可修改但需參照 novelty）
  - `📝 Methods Overview`: 方法概述（可修改）
  - `📝 Expected Outcomes`: 預期結果（可修改但需參照 selling points）

#### Approach 2: Integrated Concept Development (Single Step)
- **在單一 `/mdpaper.concept` 中完成所有步驟**
- **強制流程**:
  1. Literature Search - 搜尋現有文獻
  2. Gap Identification - 識別研究缺口，**強制詢問用戶確認**
  3. Concept Writing - 用戶確認後才撰寫 concept
- **Research Gap 區塊必須包含文獻證據**

#### Approach 3: Novelty Checklist Validation
- 新增 `validate_concept` 工具
- 在 draft 撰寫前自動檢查：
  - [ ] NOVELTY STATEMENT 是否存在且完整
  - [ ] KEY SELLING POINTS 是否已定義
  - [ ] 所有受保護區塊是否有內容
- 檢查失敗則顯示警告，引導完善

### Modification Policy
- **受保護內容 (🔒)**:
  - Agent 可以潤飾文字 (refine wording)
  - 但必須先詢問用戶確認才能修改
  - 不可自行刪除或大幅改動
- **可修改內容 (📝)**:
  - Agent 可以自由改進
  - 但需保持與受保護內容的一致性

### Implementation Phases
| Phase | Description | Status |
|-------|-------------|--------|
| 1 | 記錄設計規劃到 Memory | ✅ |
| 2 | 創建 Concept Template | ⏳ |
| 3 | 實作 Two-Phase Concept Development | ⏳ |
| 4 | 實作 Novelty Checklist Validation | ⏳ |
| 5 | 修改 Draft Prompt 保護機制 | ⏳ |
| 6 | 測試與 Git 提交 | ⏳ |
