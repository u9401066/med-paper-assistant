# Medical Paper Assistant

<p align="center">
  <a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white"></a>
  <a href="https://modelcontextprotocol.io/"><img alt="MCP" src="https://img.shields.io/badge/MCP-Compatible-green"></a>
  <a href="https://github.com/features/copilot"><img alt="Copilot" src="https://img.shields.io/badge/GitHub_Copilot-Ready-8957e5?logo=github&logoColor=white"></a>
  <a href="https://github.com/u9401066/med-paper-assistant"><img alt="License" src="https://img.shields.io/badge/License-Apache_2.0-blue"></a>
</p>

<p align="center">
  <img alt="Windows" src="https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white">
  <img alt="Linux" src="https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black">
  <img alt="macOS" src="https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white">
</p>

<p align="center">
  <b>🔬 A Guided & Exploratory Medical Paper Writing Tool</b><br>
  <i>Powered by MCP + GitHub Copilot</i>
</p>

> 📖 [繁體中文版](README.zh-TW.md)

---

## 🎯 Why This Tool?

**Traditional paper writing tools** require you to know exactly what you want before you start. But research is rarely that linear.

**Medical Paper Assistant** is different:
- 🔍 **Explore First, Decide Later** - Browse literature freely, save interesting papers, then decide your research direction
- 💬 **Conversational Workflow** - Chat naturally with AI to refine your ideas, not fight with forms
- 🧭 **Guided Process** - Step-by-step prompts guide you from concept to publication-ready manuscript
- 🔗 **Native MCP + Copilot Integration** - Works directly inside VS Code, no context switching

### 💡 What Makes Us Unique

| Traditional Tools | Medical Paper Assistant |
|-------------------|------------------------|
| Fixed templates, rigid workflow | Flexible, exploratory approach |
| Separate apps for search/write/cite | All-in-one integrated experience |
| Manual reference management | Auto-save with rich metadata & citation formats |
| Export then format | Direct Word export with journal styles |
| Learn complex UI | Natural language conversation |

---

## 🚀 Quick Start: MCP Prompts

Just type these in Copilot Chat to get started:

| Prompt | What It Does |
|--------|--------------|
| `/mdpaper.search` | 🔍 **Start here!** Explore literature freely, save interesting papers |
| `/mdpaper.concept` | 📝 Develop research concept with novelty validation |
| `/mdpaper.strategy` | ⚙️ Configure search strategy (date, exclusions, article types) |
| `/mdpaper.analysis` | 📊 Analyze CSV data, generate figures & Table 1 |
| `/mdpaper.draft` | ✍️ Write manuscript draft with auto-citations |
| `/mdpaper.clarify` | 🔄 Refine specific sections through conversation |
| `/mdpaper.format` | 📄 Export to Word with journal formatting |

> 💡 **Recommended Workflow**: `/mdpaper.search` → `/mdpaper.concept` → `/mdpaper.draft` → `/mdpaper.format`

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Literature Search & Management** | Connect to PubMed API, search articles, download PDFs from PMC Open Access, build local reference library with Foam integration |
| **Smart Reference Storage** | Save references with YAML frontmatter, pre-formatted citations (Vancouver/APA/Nature), and Foam wikilink support |
| **Data Analysis** | Read CSV data, perform statistical tests (t-test, correlation, etc.), generate publication-ready figures |
| **Intelligent Draft Generation** | Generate manuscript drafts based on concept and analysis results |
| **Automatic Citations** | Insert `[[citation_key]]` wikilinks, auto-convert to numbered references on export |
| **Interactive Refinement** | Fine-tune specific sections through conversational dialogue |
| **Word Export** | Export Markdown drafts to `.docx` files conforming to journal templates |

---

## 🏗️ Architecture: MCP Orchestration

This project uses a **modular MCP architecture** with Domain-Driven Design (DDD):

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          👤 User Layer                                    │
│  ┌─────────────────┐    ┌──────────────────────────────────────────────┐ │
│  │   VS Code       │    │  Foam Extension                              │ │
│  │   Editor        │    │  • [[wikilinks]] autocomplete                │ │
│  │                 │    │  • Hover preview (see abstract)              │ │
│  │                 │    │  • Backlinks panel                           │ │
│  └─────────────────┘    └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    🤖 VS Code Copilot Agent (Orchestrator)                │
│                                                                          │
│    /mdpaper.search  →  /mdpaper.concept  →  /mdpaper.draft  →  export   │
└───────┬──────────────────┬──────────────────┬──────────────────┬─────────┘
        │                  │                  │                  │
        ▼                  ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ 📝 mdpaper    │  │🔍 pubmed-     │  │💡 cgu         │  │🔌 External    │
│  (46 tools)   │  │  search       │  │  (submodule)  │  │   MCPs (uvx)  │
│               │  │  (submodule)  │  │               │  │               │
│ • projects    │  │ • search      │  │ • brainstorm  │  │ 🎨 drawio     │
│ • references  │  │ • PICO        │  │ • deep_think  │  │ • diagrams    │
│ • drafts      │  │ • citations   │  │ • methods     │  │               │
│ • analysis    │  │ • session     │  │               │  │ 📖 zotero     │
│ • export      │  │               │  │               │  │ • import refs │
└───────┬───────┘  └───────────────┘  └───────────────┘  └───────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          💾 Local Storage                                 │
│  projects/{slug}/                                                        │
│  ├── concept.md          ← Research concept with 🔒 protected sections   │
│  ├── references/{pmid}/  ← Foam-compatible .md + metadata.json           │
│  ├── drafts/             ← Markdown drafts with [[citations]]            │
│  ├── data/               ← CSV data files                                │
│  └── results/            ← Figures, .docx exports                        │
└──────────────────────────────────────────────────────────────────────────┘
```

### Complete Integration Stack

| Component | Type | Purpose |
|-----------|------|---------|
| **mdpaper** | Core MCP | Paper writing: projects, references, drafts, analysis, export |
| **pubmed-search** | Submodule | Literature search: PubMed API, PICO, session management |
| **cgu** | Submodule | Creative thinking: brainstorm, deep think, methods |
| **drawio** | External (uvx) | Diagrams: CONSORT, PRISMA flowcharts |
| **zotero-keeper** | External (uvx) | Import references from Zotero library |
| **Foam** | VS Code Extension | Wikilinks, hover preview, backlinks, graph view |

**Key Principle: MCP-to-MCP via Agent Only**
- MCP servers do NOT import each other directly
- Agent coordinates data flow between MCPs
- Example: `pubmed-search` returns metadata → Agent passes to `mdpaper.save_reference()`

---

## 📚 Reference File Structure

References are stored with a Foam-optimized structure:

```
references/
└── {pmid}/
    ├── {citation_key}.md   ← Main file with YAML frontmatter
    └── metadata.json       ← Full metadata for programmatic access
```

**Example**: `references/27345583/greer2017_27345583.md`

```yaml
---
aliases:
  - greer2017_27345583      # Primary wikilink
  - "PMID:27345583"         # PMID format
  - "27345583"              # Numeric only
type: reference
source: "pubmed"
pmid: "27345583"
year: 2017

# Pre-formatted citations
cite:
  vancouver: "Greer D, Marshall KE. Review of..."
  apa: "Greer, D. & Marshall, K. E. (2017)..."
  inline: "Greer & Marshall, 2017"
---

# Title

**Authors**: Greer Devon, Marshall Kathryn E

## Abstract
...
```

---

## 🔗 Foam Integration

This project integrates with [Foam](https://foambubble.github.io/foam/) for powerful reference management:

| Feature | How to Use | Benefit |
|---------|------------|---------|
| **Wikilinks** | `[[greer2017_27345583]]` | Link references in drafts |
| **Hover Preview** | Mouse over any `[[link]]` | See abstract without opening file |
| **Backlinks Panel** | Open reference file | See which drafts cite this paper |
| **Graph View** | `Ctrl+Shift+P` → `Foam: Show Graph` | Visualize paper connections |

### 📝 Citation Autocomplete (How to Use)

When writing drafts, type `[[` to trigger the citation autocomplete menu:

```markdown
According to previous studies [[    ← Type [[ here
                              ┌─────────────────────────────┐
                              │ 🔍 greer2017_27345583       │
                              │    smith2020_12345678       │
                              │    chen2019_87654321        │
                              └─────────────────────────────┘
```

**Search Options:**
| Type | Example | Matches |
|------|---------|---------|
| Author | `[[greer` | Papers by Greer |
| Year | `[[2017` | Papers from 2017 |
| PMID | `[[27345583` | Specific paper by PMID |
| Keyword | `[[sedation` | Papers with "sedation" in title |

**Keyboard Shortcuts:**
- `[[` - Open autocomplete menu
- `Ctrl+Space` - Force trigger autocomplete
- `↑↓` - Navigate options
- `Enter` - Insert selected citation

### ⚠️ Project Isolation

When switching projects, the system automatically updates Foam settings to ensure you **only see references from the current project**:

```
switch_project("my-research")
→ Foam only shows projects/my-research/references/
→ Other projects' references are automatically excluded
```

This prevents accidentally citing papers from the wrong project!

---

## 🚀 Installation

### Prerequisites

| Requirement | Version | How to Check |
|-------------|---------|--------------|
| **Python** | 3.11+ | `python3 --version` |
| **Git** | Any recent | `git --version` |
| **VS Code** | Latest | Help → About |
| **GitHub Copilot** | Extension | Extensions panel |

### Quick Install

```bash
# Clone repository
git clone https://github.com/u9401066/med-paper-assistant.git
cd med-paper-assistant

# Run setup script
# Linux/macOS:
./scripts/setup.sh

# Windows (PowerShell):
.\scripts\setup.ps1
```

The script will:
1. ✅ Create Python virtual environment (`.venv/`)
2. ✅ Install all dependencies
3. ✅ Create `.vscode/mcp.json` configuration
4. ✅ Verify installation

**Verify**: In Copilot Chat, type `/mcp` - you should see `mdpaper (46 tools)` 🎉

### Optional: Recommended Extensions

```bash
# Foam for reference linking
code --install-extension foam.foam-vscode

# Project Manager for multi-project workflow
code --install-extension alefragnani.project-manager
```

### Optional: Draw.io Integration

For diagram generation (CONSORT/PRISMA flowcharts):

```bash
./scripts/setup-integrations.sh
./scripts/start-drawio.sh
```

---

## 📂 Project Structure

```
med-paper-assistant/
├── src/med_paper_assistant/
│   ├── domain/           # Core business logic (DDD)
│   ├── application/      # Use cases, services
│   ├── infrastructure/   # DAL, external services
│   └── interfaces/       # MCP server, API
│
├── projects/             # Research projects (isolated workspaces)
│   └── {project-slug}/
│       ├── concept.md    # Research concept with 🔒 protected sections
│       ├── drafts/       # Markdown drafts
│       ├── references/   # Local reference library
│       ├── data/         # CSV data files
│       └── results/      # Generated outputs (figures, .docx)
│
├── integrations/         # External MCP servers
│   ├── pubmed-search-mcp/
│   └── cgu/              # Creative generation utilities
│
├── memory-bank/          # Project memory (cross-session context)
├── .claude/skills/       # Agent skill definitions
└── templates/            # Journal Word templates
```

---

## 🛠️ Available Tools

### 📝 mdpaper Tools (46 total)

| Category | Tools | Description |
|----------|-------|-------------|
| **Reference** (8) | `save_reference`, `list_saved_references`, `get_reference_details`, `rebuild_foam_aliases` | Reference storage & Foam integration |
| **Writing** (16) | `write_draft`, `draft_section`, `validate_concept`, `count_words`, `export_word` | Manuscript preparation |
| **Project** (12) | `create_project`, `switch_project`, `start_exploration`, `convert_exploration_to_project` | Multi-project management |
| **Search** (10) | Facade tools delegating to pubmed-search MCP | Literature search |

### 🔍 pubmed-search MCP Tools

| Category | Key Tools |
|----------|----------|
| **Search** | `search_literature`, `generate_search_queries`, `parse_pico`, `merge_search_results` |
| **Article Info** | `fetch_article_details`, `find_related_articles`, `find_citing_articles` |
| **Export** | `prepare_export`, `get_article_fulltext_links`, `analyze_fulltext_access` |
| **Session** | `get_session_pmids`, `list_search_history`, `get_session_summary` |

---

## 🎯 Novelty Validation System

Before writing drafts, concepts must pass novelty validation:

| Setting | Value | Description |
|---------|-------|-------------|
| **Rounds** | 3 | Independent evaluations |
| **Threshold** | 75/100 | Minimum score per round |
| **Pass Criteria** | All 3 ≥ 75 | Must pass all rounds |

---

## 🗺️ Roadmap

| Status | Feature | Description |
|--------|---------|-------------|
| ✅ | **Foam Integration** | Wikilinks, hover preview, backlinks |
| ✅ | **Project Isolation** | Auto-update Foam settings on project switch |
| ✅ | **PubMed MCP** | Independent literature search server |
| ✅ | **Parallel Search** | Multi-query parallel execution |
| ✅ | **Table 1 Generator** | Auto-generate baseline characteristics |
| ✅ | **Reference Refactor** | Single .md with YAML frontmatter & aliases |
| 🔜 | **Citation Tools** | `insert_citation`, `auto_cite_draft`, `verify_citations` |
| 📋 | **Multi-language Support** | Full UI localization |
| 📋 | **Journal Style Library** | Pre-configured journal formats |
| 📋 | **REST API Mode** | Expose tools as REST API |

**Legend:** ✅ Complete | 🔜 In Progress | 📋 Planned

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- 🐛 **Report bugs** - Open an issue
- 💡 **Suggest features** - Share your ideas
- 🔧 **Submit code** - Fork → Branch → PR

---

## 📄 License

Apache License 2.0 - See [LICENSE](LICENSE)
