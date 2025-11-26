# Progress

## Milestones
- [x] Project Initialization
  - [x] Memory Bank Setup
  - [x] Agent Constitution Setup
  - [x] Python Environment Setup
- [x] Core Features
  - [x] PubMed Integration
  - [x] Reference Management
  - [x] Draft Generation
  - [x] Data Analysis
  - [x] Word Export
- [x] Table 1 Generator (PR merged)
- [x] Search Strategy Manager
- [x] MCP Prompts Improvement

## Status
- **2025-11-25**: 
  - Project initialized with Git and basic structure.
  - Core Python modules created.
  - Documentation (README, LICENSE, CONTRIBUTING) added.
  - **PubMed Integration**: Implemented `search_literature` using `biopython`.
  - **Reference Management**: Implemented `save_reference` and local storage structure.
  - **Draft Generation**: Implemented `write_draft` with automatic citation formatting.
  - **Citation Insertion**: Implemented `insert_citation` for safe editing and renumbering.
  - **Workflow Automation**: Defined `/mdpaper.draft` workflow and templates.
  - **Advanced Search**: Implemented date range, article type, and sort options.
  - **Data Analysis**: Implemented `analyze_dataset`, `run_statistical_test`, and `create_plot`.
  - **Analysis Workflow**: Defined `/mdpaper.data_analysis` and integrated results into draft.
  - **Refinement**: Defined `/mdpaper.clarify` for interactive content adjustment.
  - **Word Export**: Implemented `WordExporter` with smart template filling (replacing sections instead of appending).
  - **Cleanup**: Refactored test suite, consolidated scripts, and removed temporary files.
  - **Verification**: Passed full test suite (9 tests).
  - **Status**: Initial Release Ready.

- **2025-11-25 (Update 2)**:
  - **Table 1 Generator**: Added `generate_table_one()` for baseline characteristics tables with automatic statistical tests.
  - **Search Strategy Manager**: Added `configure_search_strategy` and `get_search_strategy` tools.
  - **MCP Prompts**: Renamed to `mdpaper.*` format with short descriptions.
  - **Setup Script**: Added `scripts/setup.sh` for one-click installation.
  - **Total Tools**: 16 tools, 6 prompts.
  - **Tests**: 19 tests (18 passed, 1 minor string format issue).

- **2025-11-25 (Update 3)**:
  - **MCP Prompts Refactor**: Prompts now have required arguments for user input dialog.
  - **SERVER_INSTRUCTIONS**: Agent guidance moved to FastMCP instructions parameter.
  - **Workflow Files**: Kept in `.agent/workflows/` for reference/Antigravity compatibility.
  - **VS Code Behavior**: `/mcp.mdpaper.concept` → dialog asks for "topic" → sends to agent.

- **2025-11-25 (Update 4 - Major Refactor)**:
  - **Modular Architecture**: Refactored server.py from ~500 lines to ~90 lines entry point.
  - **New Structure**:
    - `tools/` - 5 modules (search, reference, draft, analysis, export)
    - `prompts/` - Guided workflow prompts
    - `config.py` - Server configuration and constants
  - **ARCHITECTURE.md**: Complete documentation of new structure.
  - **Total**: 27 tools, 6 prompts.
  - **Commit**: 096a57c

- **2025-11-25 (Update 5 - Draft Prompt Enhancement)**:
  - **MANDATORY Concept File**: `/mdpaper.draft` now requires concept file.
  - Auto-scans `drafts/` for files with 'concept' in filename.
  - Shows ⚠️ warning with file list if found (MUST USE).
  - Shows ❌ ERROR and blocks if no concept file exists.
  - Ensures innovation and discussion content is preserved.
  - **Commit**: 4850c9f

- **2025-11-25 (Research Project)**:
  - **Topic**: Trachway vs Fiberscope for nasotracheal intubation
  - **Literature search**: 16 references saved (PMIDs in references/)
  - **Concept draft**: `concept_nasotracheal_intubation.md` (1014 words)
  - **Introduction draft**: `introduction_nasotracheal.md` (620 words, 5 citations)

- **Reference Enhancement Update**:
  - **Pre-formatted Citations**: metadata.json now includes Vancouver, APA, Nature, in-text formats
  - **PDF Fulltext**: Automatic download from PMC Open Access (📄 indicator in list)
  - **Fulltext Reading**: pypdf extracts text for analysis
  - **Citation Network**: find_related_articles, find_citing_articles tools
  - **Rich Metadata**: DOI, PMC ID, MeSH terms, keywords, volume/issue/pages
  - **New Tools Added**:
    - `get_reference_details` - Complete reference info with all citation formats
    - `read_reference_fulltext` - Extract and read PDF content
    - `retry_pdf_download` - Retry failed PDF downloads
    - `find_related_articles` - PubMed related articles search
    - `find_citing_articles` - Citation network exploration
  - **Dependencies**: Added `requests`, `pypdf` to pyproject.toml
  - **Total Tools**: 33 (was 27)
