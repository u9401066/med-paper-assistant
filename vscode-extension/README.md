# MedPaper Assistant - VS Code Extension

AI-powered medical paper writing assistant with MCP tools, prompts, and skills.

## Features

- 🔍 **PubMed Literature Search** - Search and save references
- ✍️ **Draft Writing** - Write paper sections with AI assistance
- 💡 **Concept Development** - Develop and validate research novelty
- 📄 **Word Export** - Export to journal-ready Word documents

## Installation

### From Marketplace (Recommended)

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "MedPaper Assistant"
4. Click Install

### From VSIX

```bash
code --install-extension medpaper-assistant-0.1.0.vsix
```

## Requirements

- VS Code 1.100.0 or higher
- GitHub Copilot (for Agent Mode)
- Python 3.11+ (optional, uses bundled if not available)

## Usage

### Chat Commands

Use `@mdpaper` in the chat:

- `@mdpaper /search` - Search PubMed literature
- `@mdpaper /draft` - Write paper sections
- `@mdpaper /concept` - Develop research concepts
- `@mdpaper /project` - Manage projects
- `@mdpaper /format` - Export to Word

### MCP Prompts (Agent Mode)

In Agent Mode, use these prompts:

- `/mcp.mdpaper.write-paper` - Complete paper writing workflow
- `/mcp.mdpaper.literature-survey` - Systematic literature survey
- `/mcp.mdpaper.manuscript-revision` - Respond to reviewer comments

### MCP Tools

46 tools available for:
- Project management
- Literature search and reference management
- Draft writing and validation
- Data analysis
- Word export

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `mdpaper.pythonPath` | Python executable path | Auto-detect |
| `mdpaper.projectsDirectory` | Default projects directory | Workspace |
| `mdpaper.defaultCitationStyle` | Citation style | vancouver |

## Related Extensions

For full functionality, consider installing:

- **PubMed Zotero MCP** - Enhanced literature search and reference management
- **CGU (Creativity Generation Unit)** - AI-powered creative thinking

## Development

```bash
# Install dependencies
npm install

# Compile
npm run compile

# Package
npm run package
```

## License

Apache-2.0
