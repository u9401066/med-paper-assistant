# Active Context

## Current Focus
- MCP Server for VS Code + GitHub Copilot (Modular Architecture)
- **Multi-Project Support**: Each research paper has isolated workspace
- Draft prompt MANDATES concept file for innovation preservation

## Architecture (Refactored + Multi-Project)
```
med-paper-assistant/
├── projects/                       # Multi-project support
│   └── {project-slug}/
│       ├── project.json            # Project metadata
│       ├── concept.md              # Research concept (🔒 protected sections)
│       ├── drafts/                 # Paper drafts
│       ├── references/             # Literature by PMID
│       ├── data/                   # Analysis data
│       └── results/                # Exported documents
├── src/med_paper_assistant/
│   ├── core/
│   │   ├── project_manager.py      # Multi-project management
│   │   ├── entrez/                 # Modular Entrez package
│   │   ├── search.py               # Backward-compatible facade
│   │   ├── reference_manager.py    # Uses project paths
│   │   └── drafter.py              # Uses project paths
│   └── mcp_server/
│       ├── server.py               # Entry point
│       ├── config.py               # Configuration
│       ├── tools/                  # 39 tools in 6 modules
│       └── prompts/                # 6 guided workflows (project-aware)
```

## MCP Prompts (6 total)
| Command | Argument | Description |
|---------|----------|-------------|
| `/mdpaper.concept` | topic | Develop research concept (creates project if needed) |
| `/mdpaper.strategy` | keywords | Configure search strategy |
| `/mdpaper.draft` | section | Write paper draft ⚠️ REQUIRES concept file |
| `/mdpaper.analysis` | - | Analyze data (auto-lists project files) |
| `/mdpaper.clarify` | - | Refine content |
| `/mdpaper.format` | - | Export to Word (8-step workflow) |

## MCP Tools (39 total)
| Category | Count | Tools |
|----------|-------|-------|
| Project | 6 | create_project, list_projects, switch_project, get_current_project, update_project_status, get_project_paths |
| Search | 5 | search_literature, configure_search_strategy, get_search_strategy, find_related_articles, find_citing_articles |
| Reference | 8 | save_reference, list_saved_references, search_local_references, get_reference_details, read_reference_fulltext, retry_pdf_download, format_references, set_citation_style |
| Draft | 8 | write_draft, read_draft, list_drafts, insert_citation, draft_section, get_section_template, count_words, validate_concept |
| Analysis | 4 | analyze_dataset, run_statistical_test, create_plot, generate_table_one |
| Export | 8 | read_template, list_templates, start_document_session, insert_section, verify_document, check_word_limits, save_document, export_word |

## Current Research Project
- **Project**: nasotracheal-intubation-comparison
- **Topic**: Trachway rigid video stylet vs Fiberoptic bronchoscope for NTI
- **Location**: projects/nasotracheal-intubation-comparison/
- **Status**: concept
- **Saved references**: 16 PMIDs

---

## Recent Changes

### Multi-Project Support (2025-11-26)
- ✅ Project-based directory structure with isolated workspaces
- ✅ ProjectManager class: create, switch, list projects
- ✅ 6 new tools for project management
- ✅ Project-aware prompts showing current project status
- ✅ Total tools: 39 (was 33)

### Entrez Modularization (2025-11-26)
- ✅ Refactored search.py (~550 lines) into core/entrez/ package
- ✅ 6 submodules: base, search, pdf, citation, batch, utils
- ✅ All 9 Entrez utilities covered
- ✅ Backward-compatible facade

### Reference Enhancement
- ✅ Pre-formatted citations (Vancouver, APA, Nature, in-text)
- ✅ PDF fulltext from PMC Open Access
- ✅ Citation network tools (related, citing articles)

### Agent Instructions
- ✅ Detailed tool selection guide
- ✅ Agent Constitution in .memory/.agent_constitution.md

---

## Concept Protection (COMPLETED)
- ✅ 🔒 markers for protected sections
- ✅ 📝 markers for editable sections
- ✅ validate_concept tool for checking required sections
- ✅ Draft prompt warns about protection rules
