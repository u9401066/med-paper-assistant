# Active Context - Development

## Current Focus
- MCP Server for VS Code + GitHub Copilot
- **Multi-Project Support** with per-project `.memory/`
- Project-aware prompts and tools

## System Memory vs Project Memory

| Type | Location | Purpose |
|------|----------|---------|
| **System Memory** | `.memory/` | Development notes, architecture, tool registry |
| **Project Memory** | `projects/{slug}/.memory/` | Research context, user preferences, progress |

## Architecture (Current)
```
med-paper-assistant/
├── .memory/                        # SYSTEM MEMORY (development)
│   ├── activeContext.md            # This file
│   ├── progress.md                 # Development milestones
│   └── .agent_constitution.md      # Agent behavior rules
├── projects/                       # RESEARCH PROJECTS
│   └── {project-slug}/
│       ├── project.json            # Settings (paper_type, preferences, memo)
│       ├── concept.md              # Research concept (type-specific template)
│       ├── .memory/                # PROJECT MEMORY
│       │   ├── activeContext.md    # User preferences, interaction style
│       │   └── progress.md         # Research milestones
│       ├── drafts/
│       ├── references/
│       ├── data/
│       └── results/
├── src/med_paper_assistant/
│   ├── core/
│   │   ├── project_manager.py      # Project management (paper types, settings)
│   │   ├── entrez/                 # Modular Entrez package (6 submodules)
│   │   ├── reference_manager.py    # Uses project paths
│   │   └── drafter.py              # Uses project paths
│   └── mcp_server/
│       ├── server.py               # Entry point
│       ├── config.py               # Tool selection guide (41 tools)
│       ├── tools/                  # 41 tools in 7 modules
│       └── prompts/                # 7 guided workflows
```

## MCP Prompts (7 total)
| Command | Description |
|---------|-------------|
| `/mdpaper.project` | **NEW** Setup project with paper type & preferences |
| `/mdpaper.concept` | Develop research concept |
| `/mdpaper.strategy` | Configure search strategy |
| `/mdpaper.draft` | Write paper sections |
| `/mdpaper.analysis` | Analyze data |
| `/mdpaper.clarify` | Refine content |
| `/mdpaper.format` | Export to Word |

## MCP Tools (41 total)
| Category | Count | Key Tools |
|----------|-------|-----------|
| Project | 8 | create_project, list_projects, switch_project, **get_paper_types**, **update_project_settings** |
| Search | 5 | search_literature, find_related/citing_articles |
| Reference | 8 | save_reference, read_reference_fulltext, format_references |
| Draft | 8 | write_draft, validate_concept, count_words |
| Analysis | 4 | analyze_dataset, generate_table_one, create_plot |
| Export | 8 | read_template → insert_section → save_document |

## Paper Types (7)
- `original-research`: Clinical trial, cohort, cross-sectional (IMRAD)
- `systematic-review`: PRISMA format
- `meta-analysis`: PRISMA + forest plots
- `case-report`: Intro, Case, Discussion
- `review-article`: Narrative review
- `letter`: Brief communication
- `other`: Editorial, perspective

---
*Last Updated: 2025-11-26*
