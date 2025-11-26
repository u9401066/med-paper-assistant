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
**Search (6)**: search_literature, configure_search_strategy, get_search_strategy, find_related_articles, find_citing_articles
**Reference (8)**: save_reference, list_saved_references, search_local_references, get_reference_details, read_reference_fulltext, retry_pdf_download, format_references, set_citation_style
**Draft (7)**: write_draft, read_draft, list_drafts, insert_citation, draft_section, get_section_template, count_words
**Analysis (4)**: analyze_dataset, run_statistical_test, create_plot, generate_table_one
**Export (10)**: read_template, list_templates, start_document_session, insert_section, verify_document, check_word_limits, save_document, export_word

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
