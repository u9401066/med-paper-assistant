# Active Context

## Current Focus
- MCP Server for VS Code + GitHub Copilot.
- Prompts with required arguments (user inputs via dialog).
- Agent instructions in SERVER_INSTRUCTIONS constant.

## Architecture (2025-11-25)
```
┌─────────────────────────────────────────────────────┐
│ VS Code + Copilot                                   │
│   └─ /mcp.mdpaper.concept                          │
│       └─ Dialog: "topic" input                     │
│       └─ Result: "Help me develop... {topic}"      │
│       └─ Agent receives: SERVER_INSTRUCTIONS       │
└─────────────────────────────────────────────────────┘
```

## MCP Prompts (with required arguments)
| Command | Argument | Description |
|---------|----------|-------------|
| `/mcp.mdpaper.concept` | topic | Develop research concept |
| `/mcp.mdpaper.strategy` | keywords | Configure search strategy |
| `/mcp.mdpaper.draft` | section | Write paper draft |
| `/mcp.mdpaper.analysis` | request | Analyze data |
| `/mcp.mdpaper.clarify` | request | Refine content |
| `/mcp.mdpaper.format` | draft | Export to Word |

## MCP Tools (16 total)
- search_literature, save_reference, list_saved_references
- configure_search_strategy, get_search_strategy
- write_draft, insert_citation, draft_section
- set_citation_style, search_local_references, get_section_template
- analyze_dataset, run_statistical_test, create_plot, generate_table_one
- export_word

## Recent Changes (2025-11-25)
- ✅ Prompts with required arguments for user input
- ✅ SERVER_INSTRUCTIONS for agent guidance
- ✅ 16 tools, 6 prompts












