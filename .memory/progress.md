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
- [x] **Draw.io MCP Integration** (NEW)

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
