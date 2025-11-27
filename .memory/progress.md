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
- [x] **DDD Architecture Refactoring** (NEW)

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
