# System Patterns

## Architecture Overview

### Main MCP Server (DDD Pattern - 2025-11-27)

```
src/med_paper_assistant/
├── domain/              # Core business logic
│   ├── entities/        # Project, Reference, Draft
│   ├── value_objects/   # CitationStyle, SearchCriteria
│   └── services/        # CitationFormatter, NoveltyScorer
├── application/         # Use cases + export pipeline orchestration
│   └── use_cases/       # Project/draft/reference workflows
├── infrastructure/      # Technical concerns
│   ├── persistence/     # ProjectManager, ReferenceManager
│   ├── services/        # Analyzer, Drafter, Formatter, Foam settings
│   └── external/        # Integration clients / optional adapters
└── interfaces/mcp/      # MCP server (compact-first; 115 full / 21 default)
    ├── __main__.py      # Entry point (avoids RuntimeWarning)
    ├── server.py        # FastMCP setup
    └── tools/           # Modular tool registration
```

### Draw.io MCP Server (Forked Submodule - 2025-11-28, updated 2026-03-09)

```
integrations/next-ai-draw-io/
├── app/                 # Forked Draw.io web/frontend for interactive editing
│   └── api/             # REST/Web APIs for MCP push flows
└── mcp-server/
  └── src/drawio_mcp_server/
    ├── __main__.py      # Entry point for forked MCP server
    ├── server.py        # FastMCP tools MedPaper can patch directly
    ├── config.py        # Environment config
    ├── web_client.py    # HTTP client to the forked web app
    ├── diagram_generator.py
    ├── validator.py     # XML validation
    └── tools/           # Modular tools

Fallback reference implementation:

integrations/drawio-mcp/
└── src/index.js         # Optional official checkout for protocol/design reference

Resolution order in MedPaper runtime:
1. `integrations/next-ai-draw-io/mcp-server`
2. `integrations/drawio-mcp`
3. installed `drawio-mcp` binary
4. `npx -y @drawio/mcp`
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
  1. inspect_export(action="list_templates") - Available templates
  2. inspect_export(action="read_template") - Get template structure
  3. read_draft - Get draft content
  4. export_document(action="session_start") - Initialize
  5. export_document(action="insert_section") - Insert each section
  6. inspect_export(action="verify_document") - Check content
  7. count_words - Validate limits
  8. export_document(action="docx") / export_document(action="pdf") - Final output
