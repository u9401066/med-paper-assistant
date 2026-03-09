# Integrations 整合模組

This folder contains integrated external tools that extend Medical Paper Assistant's capabilities.

## 🔬 pubmed-search-mcp

**Purpose**: PubMed literature search with parallel query and strategy management

**Repository**: https://github.com/u9401066/pubmed-search-mcp

### Features

| Tool | Description |
|------|-------------|
| `search_literature` | Search PubMed for medical literature |
| `find_related_articles` | Find related articles by PMID |
| `find_citing_articles` | Find articles citing a PMID |
| `fetch_article_details` | Get detailed article info |
| `configure_search_strategy` | Set date range, exclusions, article types |
| `get_search_strategy` | View current strategy |
| `generate_search_queries` | Generate parallel search queries |
| `merge_search_results` | Merge and deduplicate results |
| `expand_search_queries` | Expand search with synonyms/related terms |

### Standalone Usage

```bash
# Run as standalone MCP server using uvx (recommended)
uvx --with pubmed-search[mcp] python -m pubmed_search.mcp your@email.com

# Or install via uv
uv pip install pubmed-search[mcp]
python -m pubmed_search.mcp your@email.com
```

### Integrated Usage (Default)

The search tools are automatically registered in med-paper-assistant. No additional setup needed.

---

## 📊 Draw.io MCP

**Purpose**: Generate diagrams (CONSORT, PRISMA, study flow) from natural language via Draw.io MCP.

**Current setup**: This repo prefers your forked Draw.io submodule at `integrations/next-ai-draw-io/mcp-server` for co-development. That lets MedPaper and the Draw.io integration evolve in the same workspace. If the forked submodule is absent, it falls back to an optional official checkout at `integrations/drawio-mcp`, then to the published package `@drawio/mcp` via `npx -y @drawio/mcp`.

### Quick Setup

```bash
# From project root
./scripts/setup-integrations.sh
./scripts/start-drawio.sh
```

On Windows PowerShell:

```powershell
.\scripts\setup-integrations.ps1
.\scripts\start-drawio.ps1
```

### VS Code MCP Configuration

The recommended `.vscode/mcp.json` fallback entry is:

```json
{
  "servers": {
    "drawio": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@drawio/mcp"]
    }
  }
}
```

### Runtime Notes

- For local development, keep your fork at `integrations/next-ai-draw-io`; the extension will prefer `uv run --directory integrations/next-ai-draw-io/mcp-server python -m drawio_mcp_server` automatically.
- If you also keep an official checkout at `integrations/drawio-mcp`, it is treated as a secondary reference implementation.
- No separate Next.js app is required for the current Draw.io MCP integration.
- `./scripts/start-drawio.sh` is now a verification helper that checks the forked submodule first, then official workspace checkout, then `drawio-mcp`, then `npx -y @drawio/mcp`.
- `./scripts/start-drawio.ps1` provides the same verification flow for Windows PowerShell.
- Official `jgraph/drawio-mcp` should be treated as a design/reference source for new ideas and protocol behavior, while the forked submodule remains the integration branch MedPaper can patch directly.
| `list_templates` | List available diagram templates |
| `create_from_template` | Create diagram from a template |
| `export_diagram` | Export diagram to SVG/PNG/PDF |

### Use Cases for Medical Papers

1. **CONSORT Flowchart** (RCT)
   ```
   Create a CONSORT flowchart showing:
   - 500 patients assessed for eligibility
   - 120 excluded (80 not meeting criteria, 40 declined)
   - 380 randomized to intervention (190) and control (190)
   - 10 lost to follow-up in each group
   - 180 analyzed in each group
   ```

2. **PRISMA Flowchart** (Systematic Review)
   ```
   Create a PRISMA flowchart:
   - 1500 records from database search
   - 200 duplicates removed
   - 1300 screened, 1100 excluded
   - 200 full-text assessed, 150 excluded
   - 50 included in qualitative synthesis
   - 30 included in meta-analysis
   ```

3. **Study Flow Diagram**
   ```
   Create a study flow diagram from my concept.md showing the
   methodology: data collection → preprocessing → model training → validation
   ```

---

## Future Integrations

- [ ] **Zotero Connector** - Sync with Zotero library
- [ ] **ORCID Integration** - Auto-fill author information
- [ ] **Journal Submission API** - Direct submission to supported journals
