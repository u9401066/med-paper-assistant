# Bundled Python Tool

This directory contains the bundled MedPaper MCP server.

## Structure

```
bundled/
├── tool/           # Python MCP server source
│   └── mdpaper_mcp/
├── libs/           # Bundled Python dependencies
└── python/         # (Optional) Bundled Python interpreter
```

## Building

The bundled tool is created during the extension build process:

```bash
# From extension root
npm run bundle-python
```

This will:

1. Build the Python wheel from `../../src/med_paper_assistant`
2. Install dependencies to `libs/`
3. Copy the wheel to `tool/`
