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
  - **Total Tools**: 32

- **Documentation Enhancement Update**:
  - **Bilingual README.md**: English + 繁體中文 with language toggle
  - **Bilingual CONTRIBUTING.md**: Detailed contribution guidelines
  - **Mermaid Diagrams**: Replaced ASCII art with GitHub-native flowcharts
  - **Tables**: Replaced ASCII directory trees with markdown tables
  - **Tool Count Fix**: Corrected from 33 to 32 across all documentation
  - **SERVER_INSTRUCTIONS**: Enhanced with tool selection guide and decision tree

- **Concept Enhancement Design** (COMPLETED):
  - **Goal**: Preserve novelty and selling points throughout paper writing
  - **Approaches Selected**:
    1. Structured Concept Template with 🔒/📝 markers
    2. Integrated Concept Development (single step with mandatory literature search + user confirmation)
    3. Novelty Checklist Validation before draft
  - **Modification Policy**: Agent can refine wording but must ask before major changes
  - **Implementation Phases**:
    - [x] Phase 1: Design planning and Memory recording
    - [x] Phase 2: Create Concept Template (`mcp_server/templates/`)
    - [x] Phase 3: Implement Integrated Concept Development (literature → gap confirmation → concept)
    - [x] Phase 4: Implement `validate_concept` tool
    - [x] Phase 5: Update Draft Prompt protection (🔒 markers)
    - [x] Phase 6: Test and Git commit

- **Entrez Modular Refactoring** (COMPLETED):
  - Refactored search.py (~550 lines) into core/entrez/ package
  - 6 submodules: base, search, pdf, citation, batch, utils
  - All 9 Entrez utilities covered
  - Backward-compatible facade

- **Multi-Project Support** (COMPLETED - 2025-11-26):
  - **Goal**: Isolate each research paper in its own workspace
  - **New Structure**:
    ```
    projects/{project-slug}/
    ├── project.json      # Metadata (name, status, target journal)
    ├── concept.md        # Research concept with 🔒 protected sections
    ├── drafts/           # Paper drafts
    ├── references/       # Literature by PMID
    ├── data/             # Analysis data
    └── results/          # Exported documents
    ```
  - **New Tools (6)**:
    - create_project: Create new research project
    - list_projects: List all projects
    - switch_project: Switch active project
    - get_current_project: Get current project info
    - update_project_status: Update project status (concept→drafting→review→submitted→published)
    - get_project_paths: Get all project paths
  - **Project-Aware Prompts**: All prompts show current project status
  - **Migration**: Existing drafts/ and references/ moved to projects/nasotracheal-intubation-comparison/

- **Project Configuration & Memory** (COMPLETED - 2025-11-26):
  - **Goal**: Per-project settings, preferences, and AI memory
  - **New Prompt**: `/mdpaper.project` - Guided project setup
  - **Paper Types (7)**:
    - original-research, systematic-review, meta-analysis
    - case-report, review-article, letter, other
  - **Type-specific Templates**: concept.md and progress.md vary by paper type
  - **User Preferences**: interaction_style, language, writing_style stored in project
  - **Project Memo**: Persistent notes for each project
  - **New Tools (2)**:
    - get_paper_types: List available paper types
    - update_project_settings: Update paper type, preferences, memo
  - **Project Memory**: Each project has `.memory/` with activeContext.md and progress.md
  - **System Memory**: Root `.memory/` now development-only
  - **Total Tools**: 41 (was 39)



- **MCP Server Modular Refactoring** (COMPLETED - 2025-11-26):
  - **Goal**: Clean up and organize mcp_server module structure
  - **Changes**:
    - Split `config.py` (154 lines) into:
      - `config.py` (49 lines) - Server configuration only
      - `instructions.py` (112 lines) - TOOL_GUIDE and server instructions
    - Cleaned tools imports (removed unused `Literal` from project_tools.py)
    - Verified prompts module structure (already well organized)
    - Validated server.py integration
  - **Final Structure**:
    ```
    mcp_server/
    ├── config.py          # 49 lines - paths, settings, word limits
    ├── instructions.py    # 112 lines - TOOL_GUIDE, get_server_instructions()
    ├── server.py          # 108 lines - entry point
    ├── tools/             # 1881 lines total
    │   ├── __init__.py
    │   ├── analysis_tools.py
    │   ├── draft_tools.py
    │   ├── export_tools.py
    │   ├── project_tools.py
    │   ├── reference_tools.py
    │   └── search_tools.py
    ├── prompts/           # 143 lines total
    │   ├── __init__.py
    │   └── prompts.py
    └── templates/
    ```
  - **Total**: 42 tools, 7 prompts
  - **New Feature**: `setup_project_interactive` with MCP Elicitation for dropdown menus
