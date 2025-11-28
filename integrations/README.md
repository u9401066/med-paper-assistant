# Integrations 整合模組

This folder contains integrated external tools that extend Medical Paper Assistant's capabilities.

## 📊 next-ai-draw-io

**Purpose**: Generate diagrams (CONSORT, PRISMA, study flow) from natural language via Draw.io

**Repository**: https://github.com/u9401066/next-ai-draw-io

### Quick Setup

```bash
# From project root
./scripts/setup-integrations.sh
```

### Submodule Management

#### 🔄 Update when your fork has new commits

```bash
# Option 1: One-liner from project root
git submodule update --remote integrations/next-ai-draw-io
git add integrations/next-ai-draw-io
git commit -m "chore: update next-ai-draw-io submodule"

# Option 2: Manual pull
cd integrations/next-ai-draw-io
git pull origin main
cd ../..
git add integrations/next-ai-draw-io
git commit -m "chore: update next-ai-draw-io submodule"
```

#### 📥 For users cloning this repo

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/u9401066/med-paper-assistant.git

# Or initialize after clone
git clone https://github.com/u9401066/med-paper-assistant.git
cd med-paper-assistant
git submodule update --init --recursive
```

### Setup

**Step 1: Install Next.js App**
```bash
cd integrations/next-ai-draw-io
npm install
```

**Step 2: Configure Environment**
```bash
cp env.example .env.local
# Edit .env.local with your LLM provider settings
```

**Step 3: Install MCP Server**
```bash
cd mcp-server
# Using uv (recommended)
uv sync
# Or using pip
pip install -e .
```

### VS Code MCP Configuration

Add both MCP servers to your `.vscode/mcp.json`:

```json
{
  "servers": {
    "mdpaper": {
      "command": "/path/to/med-paper-assistant/.venv/bin/python",
      "args": ["-m", "med_paper_assistant.mcp_server.server"],
      "cwd": "/path/to/med-paper-assistant"
    },
    "drawio": {
      "command": "/path/to/med-paper-assistant/integrations/next-ai-draw-io/mcp-server/.venv/bin/python",
      "args": ["-m", "drawio_mcp"],
      "cwd": "/path/to/med-paper-assistant/integrations/next-ai-draw-io/mcp-server"
    }
  }
}
```

### Running Both Services

**Terminal 1 - Draw.io Web App:**
```bash
cd integrations/next-ai-draw-io
npm run dev
# Opens at http://localhost:3000
```

**Terminal 2 - Use in VS Code Copilot:**
Both MCP servers are automatically available in Copilot Chat.

### Available Draw.io MCP Tools

| Tool | Description |
|------|-------------|
| `create_diagram` | Create a new diagram from natural language description |
| `edit_diagram` | Edit an existing diagram |
| `read_diagram` | Read and describe diagram contents |
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
