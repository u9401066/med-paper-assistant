# Progress

## Milestones
- [x] Project Initialization
- [x] Core Features (PubMed, References, Draft, Analysis, Export)
- [x] Table 1 Generator
- [x] Search Strategy Manager
- [x] MCP Prompts
- [x] Multi-Project Support
- [x] Project Configuration & Memory
- [x] MCP Server Modular Refactoring
- [x] DDD Architecture Refactoring
- [x] Novelty Validation System
- [x] Draw.io MCP Integration
- [x] Draw.io Agent-Generated XML Support (2025-11-28)
- [x] **Draw.io Smart Save & User Events** (2025-11-28)
- [x] **Draw.io Load File & Full Feature Test** (2025-11-28)
- [x] **Draw.io Drawing Guidelines Tools** (2025-11-29)

## Draw.io Drawing Guidelines Tools (2025-11-29)

### New Features

#### 1. Drawing Guidelines Module
新增 `drawing_guidelines.py` 模組，定義繪圖標準：

**連接線樣式 (推薦正交轉角線):**
```python
EDGE_STYLES = {
    "orthogonal": "edgeStyle=orthogonalEdgeStyle;rounded=1;...",  # ⭐⭐⭐
    "straight": "edgeStyle=none;",
    "curved": "edgeStyle=orthogonalEdgeStyle;curved=1;",
    "entityRelation": "edgeStyle=entityRelationEdgeStyle;",
}
```

**標準顏色規範:**
| 顏色 | fillColor | strokeColor | 用途 |
|------|-----------|-------------|------|
| 藍色 | #dae8fc | #6c8ebf | 處理步驟 |
| 綠色 | #d5e8d4 | #82b366 | 開始/成功 |
| 黃色 | #fff2cc | #d6b656 | 決策 |
| 紅色 | #f8cecc | #b85450 | 結束/錯誤 |

**佈局規範:**
- 水平間距: 60px
- 垂直間距: 40px
- 畫布邊距: 40px

#### 2. MCP Tools
| 工具 | 描述 |
|------|------|
| `get_drawing_guidelines` | 取得繪圖最佳實踐 |
| `get_style_string` | 生成 Draw.io style 字串 |
| `list_available_styles` | 列出所有可用樣式 |

### Test Results
```
=== Test 1: General Guidelines === ✅
=== Test 2: Edge Style String === ✅  
→ style="edgeStyle=orthogonalEdgeStyle;rounded=1;...endArrow=classic;"
=== Test 3: Shape Style String === ✅
→ style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
```

### Files Created
| File | Description |
|------|-------------|
| `drawing_guidelines.py` | 繪圖標準定義（350+ 行） |
| `tools/guideline_tools.py` | MCP 工具實作 |

### Files Changed
| File | Changes |
|------|---------|
| `tools/__init__.py` | 註冊 guideline_tools |
| `README.md` | 新增繪圖指南文檔 |

## Draw.io Load File & Full Feature Test (2025-11-28)

### New Features

#### 1. Load File Tool
```python
load_file_impl(file_path: str, tab_name: Optional[str] = None)
```
- 載入現有 .drawio 檔案到瀏覽器編輯器
- 自動使用檔名作為分頁名稱
- 支援完整 Draw.io XML 格式

#### 2. Debug Logging System
前端錯誤可回報到後端終端機，方便除錯：
```typescript
// 前端
fetch('/api/mcp', { body: { action: 'debug_log', message: '...' } });

// 後端 (route.ts)
console.log(`[BROWSER DEBUG] ${message}`);
```

### Test Results
| Test | Description | Status |
|------|-------------|--------|
| Simple diagram | "Test" box | ✅ |
| Baseball field | Full field with bases, lines, outfield | ✅ |
| User save | Ctrl+S triggers user_save event | ✅ |
| Load file | load_file loads .drawio | ✅ |
| Tab switching | Multiple tabs work | ✅ |

### Files Changed
| File | Changes |
|------|---------|
| `tab_tools.py` | Added `load_file_impl` |
| `diagram-context.tsx` | Added debug logging |
| `route.ts` | Added `debug_log` action |
| `page.tsx` | Improved handleSave logging |

## Draw.io Smart Save & User Events (2025-11-28)

### New Features

#### 1. Smart Save Workflow
```
save_tab() 無路徑 → 回傳提示 → Agent 詢問/自動判斷 → save_tab(path)
```

#### 2. User Event Query (Pull Model)
```
瀏覽器操作 → 事件隊列 → Agent 需要時呼叫 get_user_events()
```
- 隱私保護：不自動發送給 AI
- 節省 Token：按需拉取

#### 3. Browser Save Button
- Ctrl+S 觸發檔案下載
- 檔名格式：`diagram-2025-11-28T10-30-00.drawio`
- 防抖動：2 秒內不重複

### MCP-to-MCP Collaboration (TODO)
```
用戶「存到專案」
    ↓
Agent → MDPaper MCP (取專案路徑)
    ↓
Agent → Draw.io MCP (save_tab)
```

### Files Changed
| File | Changes |
|------|---------|
| `tab_tools.py` | `save_tab` 可選路徑 |
| `web_tools.py` | 新增 `get_user_events` |
| `web_client.py` | 新增事件查詢 API |
| `api/mcp/route.ts` | 新增 `user_save`, `events` |
| `page.tsx` | `onSave` + 檔案下載 |

## Draw.io Agent-Generated XML (2025-11-28)

### Problem
原本 `create_diagram` 工具只產生硬編碼模板（開始→處理→結束），無法根據描述生成複雜圖表。

### Solution
讓 Agent (Copilot) 自己生成 Draw.io XML，MCP 工具只負責驗證和發送到瀏覽器。

### Changes
```
mcp-server/src/drawio_mcp_server/
├── tools/diagram_tools.py   # 新增 xml 參數和格式說明
├── web_client.py            # 修正 port 檢測和 lazy start
└── server.py                # 移除預先啟動避免阻塞
```

### New Workflow
```
用戶請求 → Agent 生成 XML → create_diagram(xml=...) → 驗證 → 瀏覽器顯示
```

### Key Features
| Feature | Description |
|---------|-------------|
| **xml 參數** | Agent 可直接傳入 Draw.io XML |
| **格式說明** | 參數描述包含完整 XML 格式文檔 |
| **智能 Port 檢測** | 使用 socket 檢查 port 狀態 |
| **Lazy Start** | Web 服務首次使用時才啟動 |
| **避免重複開啟** | 提示 Agent 不要重複呼叫 open_browser |

### Test Results
- ✅ 畫一隻馬：成功生成卡通馬圖
- ✅ 研究路線圖：成功生成 6 階段詳細流程圖

## Draw.io MCP Integration (2025-11-28)

### Overview
Integrated Draw.io diagram creation/editing as a submodule with its own MCP server:

```
integrations/next-ai-draw-io/           # Git submodule
├── app/                                # Next.js 15 frontend
│   ├── api/mcp/route.ts               # MCP communication API
│   └── api/tabs/route.ts              # Tab management API
└── mcp-server/                         # Python MCP server
    └── src/drawio_mcp_server/
        ├── __main__.py                # Entry point
        ├── server.py                  # FastMCP server (10 tools)
        ├── config.py                  # Configuration management
        ├── web_client.py              # HTTP client for Next.js
        ├── diagram_generator.py       # XML generation
        ├── validator.py               # XML validation
        ├── templates.py               # Diagram templates
        └── tools/                     # Modular tool definitions
            ├── diagram_tools.py       # create/edit/read
            ├── template_tools.py      # templates & export
            ├── tab_tools.py           # tab management
            └── web_tools.py           # web service control
```

### Key Features
| Feature | Description |
|---------|-------------|
| **10 MCP Tools** | Create, edit, read, export diagrams |
| **Auto Web Start** | MCP auto-starts Next.js server |
| **Multi-Tab** | Multiple diagrams in tabs |
| **XML Validation** | Validates Draw.io XML before sending |
| **9 Diagram Types** | flowchart, aws, gcp, azure, mindmap, sequence, er, network, custom |

### MCP RuntimeWarning Fix
Fixed Python module import warnings for both MCP servers:

```python
# Before: python -m package.server (causes RuntimeWarning)
# After:  python -m package (uses __main__.py)
```

Updated:
- `med_paper_assistant.interfaces.mcp/__main__.py` - New entry point
- `med_paper_assistant.interfaces.mcp/__init__.py` - Lazy imports
- `.vscode/mcp.json` - Updated args to use package module

## Novelty Validation System (2025-11-27)

### Overview
Implemented comprehensive concept validation with multi-round novelty scoring:

```
domain/services/
└── novelty_scorer.py      # Scoring criteria, dimensions, LLM prompts

infrastructure/services/
└── concept_validator.py   # Validation service with caching
```

### Key Features
| Feature | Description |
|---------|-------------|
| **3-Round Scoring** | Multiple independent evaluations for reliability |
| **75+ Threshold** | All rounds must pass to proceed |
| **5 Dimensions** | Uniqueness, Significance, Gap Alignment, Specificity, Verifiability |
| **Consistency Check** | Cross-section alignment validation |
| **Actionable Feedback** | Specific suggestions when validation fails |
| **24h Cache** | Results cached to avoid redundant evaluations |

### New Tools
- `validate_concept` - Full validation with novelty scoring
- `validate_concept_quick` - Fast structural check only

### Tool Count
- Total: 43 tools (was 42)

### Architecture
```
ConceptValidator
├── _validate_structure()    # Required sections check
├── _evaluate_novelty()      # 3-round scoring
├── _check_consistency()     # Section alignment
├── _check_citation_support() # Citation coverage
└── generate_report()        # Human-readable output
```

## DDD Architecture (2025-11-27)

### Overview
Refactored the entire `src/med_paper_assistant/` to follow Domain-Driven Design (DDD) pattern:

```
src/med_paper_assistant/
├── domain/           # Core business logic
│   ├── entities/     # Project, Reference, Draft
│   ├── value_objects/# CitationStyle, SearchCriteria
│   └── services/     # CitationFormatter
├── application/      # Use cases
│   └── use_cases/    # CreateProject, SearchLiterature, SaveReference
├── infrastructure/   # Technical concerns
│   ├── config.py     # AppConfig
│   ├── logging.py    # setup_logger
│   ├── persistence/  # ProjectRepository, ReferenceRepository, FileStorage
│   └── external/     # PubMedClient (wraps entrez/)
├── interfaces/       # External interfaces
│   └── mcp/          # MCP server wrapper
├── shared/           # Cross-cutting concerns
│   ├── constants.py  # PAPER_TYPES, PROJECT_DIRECTORIES
│   └── exceptions.py # MedPaperError hierarchy
├── core/             # Legacy modules (maintained for compatibility)
└── mcp_server/       # Legacy MCP server (maintained for compatibility)
```

### New Files Created
- **shared/**: constants.py, exceptions.py
- **domain/entities/**: project.py, reference.py, draft.py
- **domain/value_objects/**: citation.py, search_criteria.py
- **domain/services/**: citation_formatter.py
- **infrastructure/**: config.py, logging.py
- **infrastructure/persistence/**: project_repository.py, reference_repository.py, file_storage.py
- **infrastructure/external/pubmed/**: client.py, parser.py
- **application/use_cases/**: create_project.py, search_literature.py, save_reference.py
- **interfaces/mcp/**: server.py (wrapper)

### Backward Compatibility
- `core/` and `mcp_server/` preserved for existing functionality
- All new DDD layers tested and importing correctly
- Legacy code can gradually migrate to new architecture

## Previous Milestones

### MCP Server Refactoring (2025-11-26)
- 42 tools, 7 prompts
- `setup_project_interactive` with MCP Elicitation

### Multi-Project Support (2025-11-26)
- Project isolation with project.json, concept.md
- Project-aware prompts
- 6 new project tools

### Entrez Modular Refactoring
- Refactored search.py into core/entrez/ package
- 6 submodules: base, search, pdf, citation, batch, utils

### Reference Enhancement
- 32 tools total
- Pre-formatted citations, PDF fulltext, citation network
