# Copilot Instructions for Medical Paper Assistant

## Project Overview

This is a Medical Paper Assistant built with MCP (Model Context Protocol) for VS Code + GitHub Copilot integration.

## MCP Server Configuration

### Important Configuration Notes (Updated: 2025-12-01)

The MCP server configuration in `.vscode/mcp.json` **must include** `"type": "stdio"` for each server. This is a required property according to VS Code's MCP documentation.

**Correct Configuration Format:**
```json
{
  "inputs": [],
  "servers": {
    "mdpaper": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["-m", "med_paper_assistant.interfaces.mcp"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    }
  }
}
```

**Common Mistakes to Avoid:**
1. ❌ Missing `"type": "stdio"` - VS Code won't recognize the server
2. ❌ Using old module path `med_paper_assistant.mcp_server.server` - The correct path is `med_paper_assistant.interfaces.mcp`

### Module Structure

The MCP server is located at:
- `src/med_paper_assistant/interfaces/mcp/` - MCP server implementation

### Troubleshooting MCP Server

If VS Code doesn't recognize the MCP server:
1. Ensure `"type": "stdio"` is present in server configuration
2. Reload VS Code window: `Ctrl+Shift+P` → `Developer: Reload Window`
3. Check MCP status: `Ctrl+Shift+P` → `MCP: List Servers`
4. View logs: `Ctrl+Shift+P` → `MCP: Show Output`

## Architecture

The project follows Clean Architecture / Hexagonal Architecture:
- `domain/` - Business entities and rules
- `application/` - Use cases and services
- `infrastructure/` - External integrations (PubMed, file system, etc.)
- `interfaces/` - Entry points (MCP server, CLI)
- `shared/` - Shared utilities

## Development Notes

- Python 3.10+ required
- Virtual environment at `.venv/`
- Install with `pip install -e .` for development mode
