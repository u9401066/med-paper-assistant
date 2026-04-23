# Tech Context

## Technology Stack

- **Core Language**: Python 3.12+ (MCP server, data processing)
- **MCP Framework**: FastMCP (mcp library)
- **Interface**: VS Code + GitHub Copilot via MCP
- **Environment**: uv + venv (pyproject.toml + uv.lock)
- **Key Dependencies**:
  - biopython - PubMed search via Entrez
  - pandas, scipy, matplotlib - Data analysis & visualization
  - citeproc-py - CSL citation formatting
  - pandoc (external) - Document export (replaces python-docx for formatting)
  - python-docx - Word document generation (legacy, being replaced)
- **Documentation**: Markdown (Memory Bank, drafts)
- **Templates**: .docx (Word), CSL styles (templates/csl/), journal profiles (YAML)
- **Version Control**: Git (GitHub: u9401066/med-paper-assistant)
- **Architecture**: DDD (Domain → Application → Infrastructure → Interfaces)

## Project Structure

```
med-paper-assistant/
├── src/med_paper_assistant/
│   ├── domain/
│   │   ├── entities/          # Reference, Project, Draft
│   │   ├── services/          # CitationConverter
│   │   └── value_objects/     # Enums, configs
│   ├── application/
│   │   ├── use_cases/         # SaveReference, etc.
│   │   └── export_pipeline.py # ExportPipeline
│   ├── infrastructure/
│   │   ├── persistence/       # DraftSnapshotManager, CheckpointManager,
│   │   │                      # GitAutoCommitter, HookEffectivenessTracker,
│   │   │                      # MetaLearningEngine, QualityScorecard
│   │   └── services/          # Drafter, CSLFormatter, PandocExporter
│   ├── interfaces/
│   │   └── mcp/tools/         # compact-first MCP surface (115 full / 21 default)
│   └── shared/                # Cross-cutting utilities
├── templates/
│   ├── csl/                   # CSL style files
│   └── journal-profile.template.yaml
├── tests/                     # Python tests + authority / sync guards
├── memory-bank/               # Context persistence
├── .claude/skills/            # 26 skills
├── vscode-extension/          # VSIX packaged surface v0.7.2
└── dashboard/                 # Next.js dashboard
```

## Constraints

- **OS**: Windows (primary), Linux (CI)
- **Agent**: Claude Opus 4.6 (via GitHub Copilot)
- **Python**: 3.12+ required (uv managed)
- **Current Drift Risk**: source-side MCP instructions, bundled Python mirror, and README authority snippets must stay synchronized via `npm run bundle:sync-python`, `npm run validate`, and `scripts/check_tool_surface_authority.py`

## Installation

```bash
git clone https://github.com/u9401066/med-paper-assistant.git
cd med-paper-assistant
./scripts/setup.sh   # Linux
./scripts/setup.ps1  # Windows
```
