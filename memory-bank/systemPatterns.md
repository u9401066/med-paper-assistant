# System Patterns

## Architecture Overview

### Main MCP Server (DDD Pattern - 2025-11-27)

```
src/med_paper_assistant/
├── domain/              # Core business logic
│   ├── entities/        # Project, Reference, Draft
│   ├── value_objects/   # CitationStyle, SearchCriteria
│   └── services/        # CitationFormatter, NoveltyScorer
├── application/         # Use cases
│   └── use_cases/       # CreateProject, SearchLiterature
├── infrastructure/      # Technical concerns
│   ├── persistence/     # ProjectManager, ReferenceManager
│   ├── services/        # Analyzer, Drafter, Formatter
│   └── external/        # PubMedClient
└── interfaces/mcp/      # MCP server (43 tools)
    ├── __main__.py      # Entry point (avoids RuntimeWarning)
    ├── server.py        # FastMCP setup
    └── tools/           # Modular tool registration
```

### Draw.io MCP Server (Submodule - 2025-11-28)

```
integrations/next-ai-draw-io/
├── app/                 # Next.js 15 frontend
│   └── api/             # REST APIs for MCP
└── mcp-server/
    └── src/drawio_mcp_server/
        ├── __main__.py      # Entry point
        ├── server.py        # FastMCP (10 tools)
        ├── config.py        # Environment config
        ├── web_client.py    # HTTP client
        ├── diagram_generator.py
        ├── validator.py     # XML validation
        └── tools/           # Modular tools
```

- **Memory Bank**: .memory/ directory for context persistence.
- **Agent Constitution**: .memory/.agent_constitution.md defining agent behavior.

## Design Patterns

- **Modular Tool Registration**: Each tool module exports register_xxx_tools(mcp, deps).
- **Dependency Injection**: Tools receive required managers via deps dict.
- **Context Persistence**: Agent reads Memory Bank at start, updates at end or significant changes.
- **Constitution Adherence**: Agent checks Constitution for user preferences (e.g., language).
- **Mandatory Concept Pattern**: /mdpaper.draft prompt REQUIRES concept file before writing.

## Data Structures

- **Reference Storage**:
  - Directory: references/{PMID}/
  - metadata.json: Citation info (Title, Authors, Journal, Year, DOI, etc.).
  - content.md: Abstract or full text.
- **Draft Storage**:
  - Directory: drafts/
  - Naming: concept\_\*.md for research concepts (MANDATORY for draft writing)
  - Format: Markdown with citations [1] and References section.
- **Citation Workflow**:
  - Agent reads draft → Identifies insertion → insert_citation tool → Auto-renumbering.
- **Data & Results**:
  - data/: Raw CSV/Excel files.
  - results/: Generated figures/ and tables/.
- **Word Export Workflow** (8 steps):
  1. read_template - Get template structure
  2. read_draft - Get draft content
  3. Agent decides section mapping
  4. start_document_session - Initialize
  5. insert_section - Insert each section
  6. verify_document - Check content
  7. check_word_limits - Validate limits
  8. save_document - Final output
