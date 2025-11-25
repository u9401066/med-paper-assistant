# Tech Context

## Technology Stack
- **Core Language**: Python 3.10+ (MCP server, data processing)
- **MCP Framework**: FastMCP (mcp library)
- **Interface**: VS Code + GitHub Copilot via MCP
- **Environment**: venv (Python virtual environment)
- **Key Dependencies**:
  - biopython - PubMed search via Entrez
  - pandas, scipy, matplotlib - Data analysis & visualization
  - python-docx - Word document generation
- **Documentation**: Markdown (Memory Bank, drafts)
- **Templates**: .docx (Word templates in templates/)
- **Version Control**: Git (GitHub: u9401066/med-paper-assistant)

## Project Structure
```
med-paper-assistant/
├── src/med_paper_assistant/
│   ├── core/              # Business logic
│   │   ├── search.py      # PubMed search
│   │   ├── reference_manager.py
│   │   ├── drafter.py     # Draft generation
│   │   ├── analyzer.py    # Data analysis
│   │   └── exporter.py    # Word export
│   └── mcp_server/        # MCP interface
│       ├── server.py      # Entry point
│       ├── config.py      # Configuration
│       ├── tools/         # 27 tools
│       └── prompts/       # 6 prompts
├── .memory/               # Context persistence
├── drafts/                # Paper drafts
├── references/            # Saved literature
├── templates/             # Word templates
├── scripts/setup.sh       # One-click install
└── tests/                 # Test suite
```

## Constraints
- **OS**: Linux (Ubuntu/Debian)
- **Agent**: Claude Opus 4.5 (via GitHub Copilot)
- **Compatibility**: VS Code MCP protocol
- **Python**: 3.10+ required

## Installation
```bash
git clone https://github.com/u9401066/med-paper-assistant.git
cd med-paper-assistant
./scripts/setup.sh
```
