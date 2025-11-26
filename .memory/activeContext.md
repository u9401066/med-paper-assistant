# Active Context

## Current Work
MCP Server 模組重構完成。

## Recently Completed
- **MCP Server Refactoring** (2025-11-26):
  - Split `config.py` → `config.py` + `instructions.py`
  - Cleaned unused imports in tools modules
  - Validated all 42 tools and 7 prompts working correctly
  - Added `setup_project_interactive` with MCP Elicitation API

## Architecture Summary
```
mcp_server/
├── config.py          # 49 lines - paths, settings, word limits
├── instructions.py    # 112 lines - TOOL_GUIDE, get_server_instructions()
├── server.py          # 108 lines - entry point
├── tools/             # 1881 lines (6 modules)
├── prompts/           # 143 lines (2 files)
└── templates/         # Word/MDPI templates
```

## Key Patterns
- **Elicitation**: Use `ctx.elicit()` with Pydantic models for user input
- **Enum Dropdown**: Use `json_schema_extra={"enum": [...], "enumNames": [...]}` in Pydantic
- **Server Instructions**: Constitution + TOOL_GUIDE combined via `get_server_instructions()`

## Notes
- MCP SDK 1.22.0 uses `schema=` parameter for elicitation
- fastmcp package (external) uses `response_type=` - different from mcp.server.fastmcp
- All tools registered successfully (42 tools, 7 prompts)
