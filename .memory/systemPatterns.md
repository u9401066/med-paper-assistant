# System Patterns

## Architecture (Modular - 2025-11-25)
```
src/med_paper_assistant/mcp_server/
├── server.py           # Entry point (~90 lines)
├── config.py           # SERVER_INSTRUCTIONS, constants
├── tools/              # Tool modules
│   ├── __init__.py     # register_all_tools()
│   ├── search.py       # search_literature, configure_search_strategy, etc.
│   ├── reference.py    # save_reference, format_references, etc.
│   ├── draft.py        # write_draft, insert_citation, etc.
│   ├── analysis.py     # analyze_dataset, generate_table_one, etc.
│   └── export.py       # Word export workflow (10 tools)
└── prompts/
    ├── __init__.py     # register_prompts()
    └── prompts.py      # 6 guided workflow prompts
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
  - Naming: concept_*.md for research concepts (MANDATORY for draft writing)
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
