# Medical Paper Assistant

[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![MCP SDK 2.x](https://img.shields.io/badge/MCP_SDK-2.x-green)](https://modelcontextprotocol.io/)
[![Copilot](https://img.shields.io/badge/GitHub_Copilot-Ready-8957e5?logo=github&logoColor=white)](https://github.com/features/copilot)
[![Wiki](https://img.shields.io/badge/docs-GitHub_Pages-0f766e?logo=materialformkdocs&logoColor=white)](https://u9401066.github.io/med-paper-assistant/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue)](https://github.com/u9401066/med-paper-assistant)

![Windows](https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black)
![macOS](https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white)

## 🔬 An Auditable MCP Research Workspace for Autonomous and Human-Guided Academic Writing

Core research surfaces: mdpaper 118 full / 12 compact + PubMed 45 + CGU 24 · Managed MCP integrations: 6 (adds Asset-Aware 30 + Draw.io 23 + Zotero Keeper 32) · 38 Skills · 15 Prompt Workflows

> 📖 [繁體中文版](README.zh-TW.md)
> 🤖 **[Auto-Paper: Autonomous + Human-Guided Writing Guide](docs/auto-paper-guide.md)** — 13 main gate checkpoints + Phase 2.1 sub-gate, 79 Quality Hooks, Structured Review Loop
> 🧭 **[GitHub Pages Wiki](https://u9401066.github.io/med-paper-assistant/)** — 35 topic pages with Mermaid workflows, SVG architecture maps, full-text search, and dark mode

The goal is not one-shot text generation. MedPaper Assistant supports bounded autonomous runs and researcher-led writing through the same observable checkpoints, evidence locators, quality gates, review receipts, and reproducible exports. A solver produces artifacts; independent checks score those artifacts without granting unsupported claims evidence credit.

![MedPaper Assistant overview](docs/assets/medpaper-intro.svg)

---

## 📦 What's in the Box

This repository is the **full authoring and integration workspace** behind MedPaper Assistant. It combines the core MCP runtime, the packaged VSIX extension, bundled guides, and pinned integration submodules in one place.

| Component                                                          | Type                   | Tools                             | Description                                                                                                                           |
| ------------------------------------------------------------------ | ---------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **mdpaper**                                                        | Core MCP Server        | 118 (full) / 12 (compact default) | Dual workflow server for manuscript and library-wiki paths, plus 3 MCP prompts and 3 MCP resources                                    |
| **[pubmed-search](https://github.com/u9401066/pubmed-search-mcp)** | MCP Server (submodule) | 45                                | PubMed/Europe PMC/CORE search, PICO, citation metrics, session mgmt                                                                   |
| **[CGU](https://github.com/u9401066/creativity-generation-unit)**  | MCP Server (submodule) | 24                                | Creative generation: brainstorm, deep think, spark collision                                                                          |
| **[VS Code Extension](vscode-extension/)**                         | Extension              | 9 cmds + 10 chat                  | MCP auto-registration, compact-first packaged surface, workspace setup, LLM wiki guide, Foam graph views, `@mdpaper` chat participant |
| **[Dashboard](dashboard/)**                                        | Next.js Web App        | —                                 | Project management UI, diagram editor                                                                                                 |
| **[Foam](https://foambubble.github.io/foam/)**                     | VS Code Extension      | —                                 | `[[wikilink]]` citation linking, hover preview, graph view                                                                            |
| **[Skills](.claude/skills/)**                                      | Agent Workflows        | 38                                | Guided multi-tool workflows plus a shared Claude Code / Codex / OpenClaw academic-writing contract                                    |
| **[Prompts](.github/prompts/)**                                    | Prompt Files           | 15                                | `/mdpaper.search`, `/mdpaper.draft`, etc.                                                                                             |

The table above shows the three core research servers. These optional servers complete the six managed MCP integrations (installed via uvx):

- **asset-aware (30 tools)** — Ingest user-provided DOCX/XLSX/PDF/PPTX source materials and reference full text before drafting
- **drawio (23 tools)** — CONSORT/PRISMA flowchart generation
- **zotero-keeper (32 tools)** — Import references from Zotero library

Counts in these tables are release-gated via `tool-surface-authority.json` and `vscode-extension/bundle-manifest.json`.

### Choose Your Install Surface

| Surface             | Best for                                       | What you get                                                                                                                                                                                      |
| ------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Full repository** | Maintainers, power users, and workflow authors | Core `mdpaper` runtime, pinned MCP integrations/submodules, 38 skills, 15 prompt workflows, cross-agent harness, repo scripts, tests, and authoring docs                                          |
| **VSIX extension**  | End users who want the packaged experience     | `@mdpaper`, 9 palette commands, compact-first `mdpaper` runtime (12 tools by default / 118 optional), 14 bundled skills, 13 bundled prompt workflows, 9 bundled agents, and bundled LLM wiki docs |

The repository is the broader engineering surface. The VSIX is the curated end-user surface.

**VSX note**: The extension verifies or installs checksum-pinned `uv`/`uvx` 0.12.5, then launches the matching core package and all managed external MCPs through isolated, exact SDK 2 sources. A workspace that explicitly defines `mdpaper` in `.vscode/mcp.json` remains authoritative and suppresses extension auto-registration. CI smoke covers `ubuntu-latest`, `windows-latest`, and `macos-14`, plus all five exact-archive integrations.

### How the Pieces Fit Together

![MedPaper Assistant architecture](docs/assets/medpaper-architecture.svg)

### Claude Code, Codex, and OpenClaw

The same evidence and quality gates are available across agent runtimes:

| Runtime     | Project instructions                                  | Academic-writing skill                                                                 |
| ----------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Claude Code | [`CLAUDE.md`](CLAUDE.md) and [`AGENTS.md`](AGENTS.md) | [`.claude/skills/academic-writing-harness/`](.claude/skills/academic-writing-harness/) |
| Codex       | [`AGENTS.md`](AGENTS.md)                              | [`.agents/skills/academic-writing-harness/`](.agents/skills/academic-writing-harness/) |
| OpenClaw    | [`AGENTS.md`](AGENTS.md) plus workspace policy        | [`.agents/skills/academic-writing-harness/`](.agents/skills/academic-writing-harness/) |

The platform-neutral [academic-writing workflow](docs/harness/academic-writing-workflow.md) covers manuscripts, proposals, project closeout reports, student papers, preprints, audit gates, and safe exemplar use.

---

## 🎯 Why This Tool?

**Traditional paper writing tools** require you to know exactly what you want before you start. But research is rarely that linear.

**Medical Paper Assistant** is not just a writing assistant. It is a research workspace orchestrator:

- 🔍 **Explore First, Decide Later** — Browse literature freely, save interesting papers, then decide your research direction
- 📥 **Source Material Intake First** — Phase 0 scans user-provided DOCX/XLSX/PDF/CSV inputs and flags files that must go through asset-aware ingestion before drafting
- 💬 **Conversational Workflow** — Chat naturally with AI to refine your ideas, not fight with forms
- 🧭 **Guided Process** — Step-by-step prompts guide you from concept to publication-ready manuscript
- 🔗 **All-in-One** — Search, write, cite, analyze, export — all integrated inside VS Code

| Traditional Tools                   | Medical Paper Assistant                                                         |
| ----------------------------------- | ------------------------------------------------------------------------------- |
| Fixed templates, rigid workflow     | Flexible, exploratory approach                                                  |
| Separate apps for search/write/cite | One workspace: 118/12 mdpaper + 45 PubMed + 24 CGU tools and packaged workflows |
| Manual reference management         | Auto-save with verified PubMed data                                             |
| Export then format                  | Direct Word export with journal styles                                          |
| Learn complex UI                    | Natural language conversation                                                   |

---

## 🚀 Quick Start

### Prerequisites

| Requirement        | Version    | Check                                                    |
| ------------------ | ---------- | -------------------------------------------------------- |
| **Python**         | 3.12+      | `python3 --version`                                      |
| **Node.js**        | 24+        | `node --version` (maintainer VSIX/dashboard builds only) |
| **Git**            | Any recent | `git --version`                                          |
| **VS Code**        | Latest     | Help → About                                             |
| **GitHub Copilot** | Extension  | Extensions panel                                         |

### Install

```bash
# Clone with submodules
git clone --recursive https://github.com/u9401066/med-paper-assistant.git
cd med-paper-assistant

# Run setup script
./scripts/setup.sh          # Linux/macOS
.\scripts\setup.ps1         # Windows PowerShell
```

The script will:

1. ✅ Create Python virtual environment (`.venv/`)
2. ✅ Initialize pinned Git submodules from this repository
3. ✅ Install all dependencies (via `uv`)
4. ✅ Create `.vscode/mcp.json` configuration for `mdpaper`, `pubmed-search`, `cgu`, `zotero-keeper`, `asset-aware`, and `drawio`
5. ✅ Verify MedPaper and CGU startup paths

Important installation notes:

- The setup script uses pinned submodule commits for reproducible installs. It does not auto-track the latest upstream submodule HEAD.
- If you intentionally want newer submodule code, run `git submodule update --remote --merge` yourself and test before committing.
- The Draw.io MCP server is the pinned Python SDK 2 package in the submodule (or its immutable commit archive). Node.js/npm is needed only for the optional interactive Draw.io web UI, not as an MCP 1 fallback.
- Repository mode launches pinned submodules. Marketplace mode installs exact SDK 2 commit archives for PubMed, CGU, Zotero Keeper, and Draw.io; it never floats to an unverified latest package.
- The frozen Python lock currently resolves the stable MCP SDK 2.1.1 runtime. Source builds of the VSIX and dashboard use the same Node.js 24 baseline as CI; Marketplace users do not need Node.js to run the packaged extension.

**Verify**: In Copilot Chat, type `/mcp` — you should see `mdpaper` listed 🎉

### Optional Integrations

```bash
# Foam for reference linking (highly recommended)
code --install-extension foam.foam-vscode

# Draw.io for diagram generation
./scripts/setup-integrations.sh && ./scripts/start-drawio.sh
```

Windows PowerShell:

```powershell
.\scripts\setup-integrations.ps1
.\scripts\start-drawio.ps1
```

---

## 💬 MCP Prompts — Just Type and Go

In Copilot Chat, type these prompts to trigger guided workflows:

| Prompt              | Description                                         |
| ------------------- | --------------------------------------------------- |
| `/mdpaper.search`   | 🔍 **Start here!** Explore literature, save papers  |
| `/mdpaper.concept`  | 📝 Develop research concept with novelty validation |
| `/mdpaper.draft`    | ✍️ Write manuscript with auto-citations             |
| `/mdpaper.analysis` | 📊 Analyze CSV data, generate figures & Table 1     |
| `/mdpaper.format`   | 📄 Export to Word with journal formatting           |
| `/mdpaper.clarify`  | 🔄 Refine specific sections through conversation    |
| `/mdpaper.project`  | 📁 Create or switch research projects               |
| `/mdpaper.strategy` | ⚙️ Configure search strategy (dates, filters)       |
| `/mdpaper.help`     | ❓ Show all available commands                      |

### Two Workflow Paths

**Library Wiki Path**

- Create a project with `workflow_mode="library-wiki"`
- Move through `reference_action` plus direct `save_reference_mcp` verified saves → `library_action` → full-surface wiki materialization when needed
- Use `materialize_agent_wiki`, Foam graph views, and `docs/how-to/llm-wiki.md` for cross-note synthesis and traversal

**Manuscript Path**

- Create a project with `workflow_mode="manuscript"`
- Move through `/mdpaper.search` → `/mdpaper.concept` → `/mdpaper.draft` → `/mdpaper.format`
- Only this path enforces concept validation, review loops, and export gates

> 💡 **Recommended usage**: converge your literature and concepts in Library Wiki Path first, then switch to Manuscript Path for formal drafting.

## Foam + Copilot Knowledge Base

MedPaper already uses Foam as the browse-and-graph layer while Copilot drives ingestion, identity resolution, knowledge-map generation, synthesis pages, block-anchor embeds, and managed graph slices.

The current Foam/Copilot layer now includes orphan / placeholder repair loops, template-driven capture into `inbox/`, `review/`, and `daily/`, richer `foam-query` dashboards, publish-safe wikilink reference packs under `notes/publish/`, and project-specific `graph_views_json` slices.

Docs and tutorials:

- [GitHub Pages Wiki](https://u9401066.github.io/med-paper-assistant/)
- [Formal academic output profiles](docs/harness/output-profiles.md)
- [Production academic-writing architecture](docs/design/production-academic-writing-harness.md)
- [Using the MedPaper LLM Wiki](docs/how-to/llm-wiki.md)
- [Foam Dependency Reference](docs/reference/foam.md)
- [Graph-view example for ICU sedation / delirium review](docs/how-to/llm-wiki.md)

---

## 🧠 Skill System + Project Memory

**Our core differentiator:** We don't just provide tools — we provide **guided workflows** that know how to combine tools effectively, AND **project memory** that remembers your research journey across sessions.

### What is a Skill?

```text
Tool  = Single capability (search, save, analyze...)
Skill = Complete knowledge (how to combine tools to accomplish tasks)
```

Representative skill families across the 38 skills:

| Category       | Skills                                                                              | Triggers                                  |
| -------------- | ----------------------------------------------------------------------------------- | ----------------------------------------- |
| 🔬 Research    | `literature-review`, `concept-development`, `concept-validation`, `parallel-search` | "找論文", "search", "concept", "validate" |
| ✍️ Writing     | `draft-writing`, `reference-management`, `word-export`                              | "寫草稿", "draft", "citation", "export"   |
| 📁 Management  | `project-management`, `memory-updater`, `memory-checkpoint`                         | "新專案", "切換", "存檔"                  |
| 🛠️ Development | `git-precommit`, `code-refactor`, `test-generator`, `code-reviewer`                 | "commit", "refactor", "test"              |

### Project Memory

Each project maintains its own `.memory/` folder so the AI can continue previous research coherently. The directory layout now splits by workflow mode:

**Manuscript Path**

```text
projects/{slug}/
├── .memory/
│   ├── activeContext.md   ← Agent's working memory
│   └── progress.md        ← Research milestones
├── concept.md             ← Research concept (with 🔒 protected sections)
├── references/            ← Foam-compatible literature library
├── drafts/                ← Markdown drafts with [[citations]]
├── data/                  ← CSV data files
└── results/               ← Figures, .docx exports
```

**Library Wiki Path**

```text
projects/{slug}/
├── .memory/
│   ├── activeContext.md   ← Current library/wiki focus and triage state
│   └── progress.md        ← ingest / organize / synthesize milestones
├── concept.md             ← library workspace seed
├── references/            ← materialized reference notes
├── inbox/                 ← raw notes and capture queue
├── concepts/              ← atomic concept pages and backlinks
├── review/                ← graph repair worklists and review notes
├── daily/                 ← templated daily capture pages
└── projects/              ← synthesis pages / workstreams
```

---

## ✨ Key Features

### Literature & References

- **PubMed + Europe PMC + CORE** search (45 search tools)
- **PICO parsing** for clinical questions
- **MCP-to-MCP verified metadata** — PMID-based retrieval preserves the source response and trust layer; downstream interpretation still requires evidence checks
- Layered trust: 🔒 VERIFIED (PubMed) · 🤖 AGENT (AI notes) · ✏️ USER (your notes)
- Foam wikilinks: `[[author2024_12345678]]` with hover preview & backlinks
- **Library Wiki Path** — `inbox/`, `concepts/`, and `projects/` note flow with reading queues and cross-note dashboards
- **LLM wiki materialization** — auto-generated `notes/index.md`, `notes/library/overview.md`, context hubs, and draft / figure / table graph notes

### Writing & Editing

- **AI draft generation** per section (Introduction, Methods, Results, Discussion)
- **Citation-Aware Editing** — `patch_draft` validates all `[[wikilinks]]` before saving
- **Auto-fix citation format** — `[[12345678]]` → `[[author2024_12345678]]`
- **Novelty validation** — 3-round independent scoring (threshold: 75/100)
- **Style and authorship integrity** — Evidence-led prose, voice/clarity checks, and disclosure-aware review; never optimized to evade AI detectors

### Data Analysis

- CSV dataset analysis with descriptive statistics
- Statistical tests (t-test, ANOVA, chi², correlation, Mann-Whitney, Fisher's)
- **Table 1 generator** — Baseline characteristics with automatic variable detection
- Publication-ready figures (matplotlib/seaborn)
- **Content-integrity review** — SHA-256/MIME receipts, optional C2PA validation, and a version-pinned `remove-ai-watermarks` visible/open-DWT detector; the check is offline and detection-only, preserves the original, writes no cleaned derivative, and never treats “not detected” as clean

### Export & Submission

- **Word export** with journal template support
- Cover letter + highlights generation
- Manuscript consistency checker
- Reviewer response generator (point-by-point format)
- Submission checklist (word count, figure format, etc.)

### Infrastructure

- **DDD Architecture** (Domain-Driven Design) with clean layer separation
- **16 pre-commit hooks** (ruff, mypy, bandit, pytest, prettier, doc-update...)
- **Workspace State** recovery for cross-session continuity
- **uv** for all Python package management
- **MCP SDK 2.x** — the legacy 1.x runtime is not supported; tools, prompts, resources, elicitation, and progress notifications use the v2 SDK surface
- **Managed Foam graph views** — named Default, Evidence, Writing, Assets, and Review graph slices

---

## 🏗️ Architecture

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                          👤 User Layer                                    │
│  ┌─────────────────┐    ┌──────────────────────────────┐  ┌──────────┐  │
│  │   VS Code        │    │  Foam Extension               │  │Dashboard │  │
│  │   Editor         │    │  [[wikilinks]] autocomplete    │  │(Next.js) │  │
│  │                  │    │  hover preview · backlinks     │  │          │  │
│  └─────────────────┘    └──────────────────────────────┘  └──────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│               🤖 Copilot Agent (Orchestrator)                             │
│      38 Skills + 15 Prompt Workflows + Cross-Agent Customization         │
│   /mdpaper.search → /mdpaper.concept → /mdpaper.draft → export          │
└───────┬──────────────────┬──────────────────┬──────────────────┬─────────┘
        │                  │                  │                  │
        ▼                  ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ 📝 mdpaper    │  │🔍 pubmed-     │  │💡 cgu         │  │🔌 External    │
│ 118/12 tools  │  │  search       │  │  24 tools     │  │   MCPs (uvx)  │
│               │  │  45 tools     │  │               │  │               │
│ • projects    │  │ • PubMed      │  │ • brainstorm  │  │ 🎨 drawio     │
│ • references  │  │ • Europe PMC  │  │ • deep_think  │  │ • diagrams    │
│ • drafts      │  │ • CORE        │  │ • spark       │  │               │
│ • validation  │  │ • PICO        │  │ • methods     │  │ 📖 zotero     │
│ • analysis    │  │ • Gene/Chem   │  │               │  │ • import refs │
│ • export      │  │ • Session     │  │               │  │ 📥 asset-aware│
│               │  │               │  │               │  │ • docx/xlsx   │
│               │  │               │  │               │  │ • fulltext    │
└───────┬───────┘  └───────────────┘  └───────────────┘  └───────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          💾 Local Storage                                 │
│  projects/{slug}/                                                        │
│  ├── .audit/source-materials.yaml ← Phase 0 scan of user-provided inputs │
│  ├── .audit/exemplar-usage.yaml  ← non-evidentiary exemplar audit        │
│  ├── concept.md          ← Research concept with 🔒 protected sections   │
│  ├── references/{pmid}/  ← Foam-compatible .md + metadata.json           │
│  ├── drafts/             ← Markdown drafts with [[citations]]            │
│  ├── data/               ← CSV data files                                │
│  └── results/            ← Figures, .docx exports                        │
└──────────────────────────────────────────────────────────────────────────┘
```

### MCP-to-MCP Direct Communication

When saving references, data flows directly between MCP servers — the Agent only passes a PMID, never full metadata:

```text
Agent: "save PMID:24891204"
     │
     ▼
mdpaper.save_reference_mcp(pmid="24891204")
     │  Direct HTTP call (not through Agent)
     ▼
pubmed-search: GET /api/cached_article/24891204
     │  Returns verified PubMed data
     ▼
Saved with layered trust:
  🔒 VERIFIED: PubMed data (immutable)
  🤖 AGENT:    AI notes (marked source)
  ✏️ USER:     Your notes (editable)
```

---

## 🛠️ mdpaper MCP Tools

The mdpaper MCP server exposes **118 (full) / 12 (compact default)** tools, plus **3 MCP prompts** and **3 MCP resources** for official MCP clients.

These counts are runtime-validated via `tool-surface-authority.json` and `scripts/check_tool_surface_authority.py`, and the validate/release gates fail if the docs drift from that authority.

Compact mode exposes exactly these 12 stable entrypoints and hides most granular public verbs; set `MEDPAPER_TOOL_SURFACE=full` to expose the complete surface.

| Compact capability   | Tools                                                      |
| -------------------- | ---------------------------------------------------------- |
| Project / state      | `project_action`, `workspace_state_action`                 |
| Library / references | `library_action`, `reference_action`, `save_reference_mcp` |
| Draft / analysis     | `draft_action`, `analysis_action`                          |
| Validation / review  | `validation_action`, `run_quality_checks`                  |
| Pipeline             | `pipeline_action`                                          |
| Export               | `export_document`, `inspect_export`                        |

`save_reference_mcp(pmid)` remains a direct compact safe verb so verified PubMed retrieval cannot be confused with `reference_action(action="save_agent")`, the lower-trust fallback.

The following tables summarize representative full-surface tools; compact clients reach the same domain capabilities through the entrypoints above.

### 📁 Project Management

Projects, exploration mode, workspace state recovery, diagram management.

| Key Tools                                              | Description                          |
| ------------------------------------------------------ | ------------------------------------ |
| `create_project` / `switch_project` / `delete_project` | Project lifecycle                    |
| `start_exploration` / `convert_exploration_to_project` | Explore-first workflow               |
| `get_workspace_state` / `sync_workspace_state`         | Cross-session recovery               |
| `save_diagram` / `list_diagrams`                       | Draw.io integration                  |
| `setup_project_interactive`                            | Interactive paper type configuration |
| `update_authors`                                       | Manage structured author metadata    |

### 📚 Reference Management

Save, search, format, and manage references with Foam integration.

| Key Tools                                           | Description                                                            |
| --------------------------------------------------- | ---------------------------------------------------------------------- |
| `reference_action`                                  | **Compact default** — browse, retrieve, format, and analyze references |
| `save_reference_mcp`                                | **Recommended** — Save by PMID via MCP-to-MCP (verified data)          |
| `list_saved_references` / `search_local_references` | Browse & search library                                                |
| `format_references` / `set_citation_style`          | Vancouver / APA / Nature                                               |
| `sync_references`                                   | Sync `[[wikilinks]]` to numbered references                            |

### ✍️ Draft & Editing

Write, edit, cite — with built-in validation.

| Key Tools                                     | Description                                              |
| --------------------------------------------- | -------------------------------------------------------- |
| `draft_section` / `write_draft`               | Create and write sections                                |
| `list_drafts` / `read_draft` / `delete_draft` | Draft lifecycle                                          |
| `get_available_citations`                     | List all valid `[[citation_key]]` before editing         |
| `patch_draft`                                 | **Citation-aware** partial edit with wikilink validation |
| `insert_citation` / `suggest_citations`       | Smart citation insertion                                 |
| `scan_draft_citations` / `sync_references`    | Citation management                                      |
| `count_words`                                 | Section and manuscript word-count checks                 |

### ✅ Validation

| Tool                      | Description                                         |
| ------------------------- | --------------------------------------------------- |
| `validate_concept`        | Full novelty scoring against the active concept     |
| `validate_wikilinks`      | Auto-fix `[[12345678]]` → `[[author2024_12345678]]` |
| `compare_with_literature` | Compare the current idea against saved references   |

### 📊 Data Analysis

| Tool                   | Description                                           |
| ---------------------- | ----------------------------------------------------- |
| `analyze_dataset`      | Descriptive statistics for CSV                        |
| `run_statistical_test` | t-test, ANOVA, chi², correlation, etc.                |
| `generate_table_one`   | Baseline characteristics with auto variable detection |
| `create_plot`          | Publication-ready figures                             |
| `insert_figure`        | Insert figure into draft with archive validation      |
| `insert_table`         | Insert table into draft with archive validation       |
| `list_assets`          | List figures and tables in project results            |

### 🔍 Review & Audit

| Category               | Key Tools                                                                 |
| ---------------------- | ------------------------------------------------------------------------- |
| **Pipeline Gates**     | `validate_phase_gate`, `pipeline_heartbeat`, `validate_project_structure` |
| **Review Loop**        | `start_review_round`, `submit_review_round`, `request_section_rewrite`    |
| **Pipeline Control**   | `pause_pipeline`, `resume_pipeline`, `approve_section`                    |
| **Audit & Hooks**      | `run_quality_audit`, `run_writing_hooks`, `record_hook_event`             |
| **Self-Evolution**     | `run_meta_learning`, `verify_evolution`, `apply_pending_evolutions`       |
| **Domain Constraints** | `check_domain_constraints`, `evolve_constraint`                           |
| **Data & Health**      | `validate_data_artifacts`, `diagnose_tool_health`, `check_formatting`     |

### 📄 Export & Submission

| Category       | Key Tools                                                                                                                       |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **Inspection** | `inspect_export(action="list_templates")`, `inspect_export(action="read_template")`, `inspect_export(action="verify_document")` |
| **Session**    | `export_document(action="session_start")`, `export_document(action="session_insert")`, `export_document(action="session_save")` |
| **Pandoc**     | `export_document(action="docx")`, `export_document(action="pdf")`, `inspect_export(action="docx_smoke")`                        |
| **Submission** | `generate_cover_letter`, `generate_highlights`                                                                                  |

### 🧩 MCP Prompts & Resources

| Capability    | Names / URIs                                                                                  | Purpose                                                                              |
| ------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **Prompts**   | `project_bootstrap`, `draft_section_plan`, `word_export_checklist`                            | Materialize guided prompt workflows through the official MCP prompt API              |
| **Resources** | `medpaper://workspace/state`, `medpaper://workspace/projects`, `medpaper://templates/catalog` | Surface live workspace state, project lists, and template metadata via MCP resources |

### 🔍 pubmed-search MCP Tools (45 tools)

| Category        | Key Tools                                                                     |
| --------------- | ----------------------------------------------------------------------------- |
| **Search**      | `unified_search`, `generate_search_queries`, `parse_pico`                     |
| **Databases**   | PubMed, Europe PMC (fulltext + text mining), CORE (200M+ open access)         |
| **Gene/Chem**   | `search_gene`, `get_gene_details`, `search_compound`, `search_clinvar`        |
| **Exploration** | `find_related_articles`, `find_citing_articles`, `get_article_references`     |
| **Export**      | `prepare_export` (RIS/BibTeX/CSV), `get_citation_metrics` (iCite RCR)         |
| **Session**     | `read_session(action="pmids")`, `get_session_log` (survives AI memory limits) |

### 💡 CGU Creative Tools (24 tools)

| Category     | Key Tools                                                   |
| ------------ | ----------------------------------------------------------- |
| **Ideation** | `generate_ideas`, `spark_collision`, `spark_collision_deep` |
| **Analysis** | `deep_think`, `multi_agent_brainstorm`                      |
| **Methods**  | `list_methods`, `select_method`, `apply_method`             |

CGU runtime notes:

- In the repository workflow, CGU is started from the pinned submodule with `uv run --directory integrations/cgu python -m cgu.server`.
- In the VSX workflow, MedPaper registers CGU when bundled code or the workspace submodule is available; otherwise CGU is simply skipped.
- CGU itself supports Python `>=3.11`, but this repository currently requires Python `>=3.12`, so cross-platform repo setup should be treated as Python 3.12 baseline on macOS, Linux, and Windows.
- The default repo MCP example uses `CGU_THINKING_ENGINE=simple`, which is the low-friction mode. Advanced LLM-backed modes still depend on CGU-side model/provider configuration.

---

## 🔗 Foam Integration

| Feature                | How to Use                                        | Benefit                                                         |
| ---------------------- | ------------------------------------------------- | --------------------------------------------------------------- |
| **Wikilinks**          | `[[greer2017_27345583]]`                          | Link drafts, concept pages, and synthesis notes                 |
| **Hover Preview**      | Mouse over any `[[link]]`                         | See abstract without opening file                               |
| **Backlinks Panel**    | Open reference file                               | See which drafts or wiki notes cite this paper                  |
| **Graph View**         | `Ctrl+Shift+P` → `MedPaper: Show Foam Graph: ...` | Jump directly to Default / Evidence / Writing / Assets / Review |
| **Materialized Views** | `notes/index.md`, `notes/library/overview.md`     | Review live counts, context hubs, and asset/draft graph nodes   |
| **Project Isolation**  | Auto-switches on `switch_project`                 | Only see current project's references                           |

### LLM Wiki Enhancements

- `notes/index.md` emits live Foam query counts
- registered figures and tables materialize as first-class graph notes
- draft sections plus journal/author/topic/context hubs carry graph-friendly frontmatter
- the library dashboard now exposes `overview`, `queues`, `concepts`, `links`, and `synthesis` cross-note views

### Citation Autocomplete

Type `[[` in any draft to trigger the autocomplete menu:

<!-- prettier-ignore -->
```markdown
According to previous studies [[    ← Type [[ here
                              ┌─────────────────────────────┐
                              │ 🔍 greer2017_27345583       │
                              │    smith2020_12345678       │
                              │    chen2019_87654321        │
                              └─────────────────────────────┘
```

Search by author (`[[greer`), year (`[[2017`), PMID (`[[27345583`), or keyword (`[[sedation`).

---

## 📚 Reference File Structure

References are stored with **Foam-optimized, layered-trust** structure:

```text
references/{pmid}/
├── {citation_key}.md   ← YAML frontmatter + abstract (human-readable)
└── metadata.json       ← Full metadata (programmatic access)
```

```yaml
---
# 🔒 VERIFIED (from PubMed, immutable)
title: "Complications of airway management"
author:
  - { family: Pacheco-Lopez, given: Paulette C }
year: 2014
journal: Respiratory Care
pmid: "24891204"
_source:
  mcp: pubmed-search
  verified: true

# 🤖 AGENT (AI-generated, marked)
_agent:
  notes: "Key review on airway complications"
  relevance: high

# Foam
aliases: [pachecolopez2014, "PMID:24891204"]
tags: [reference, airway, review]
---
```

---

## 📂 Project Structure

```text
med-paper-assistant/
├── src/med_paper_assistant/       # Core MCP server (DDD architecture)
│   ├── domain/                    #   Business logic, entities, value objects
│   ├── application/               #   Use cases, services
│   ├── infrastructure/            #   DAL, external services
│   └── interfaces/mcp/            #   MCP server, 118 full / 12 compact tools + 3 prompts + 3 resources
│
├── integrations/                  # Bundled MCP servers
│   ├── pubmed-search-mcp/         #   PubMed/PMC/CORE search (45 tools)
│   └── cgu/                       #   Creative generation (24 tools)
│
├── vscode-extension/              # Packaged VSIX surface
│   ├── src/                       #   Extension source
│   ├── bundled/tool/              #   Mirrored Python runtime for marketplace installs
│   ├── skills/                    #   Bundled skill definitions
│   ├── docs/                      #   Bundled Foam / LLM wiki docs
│   └── prompts/                   #   Quick-action prompts
│
├── dashboard/                     # Next.js project management UI
│   └── src/
│
├── projects/                      # Research projects (isolated workspaces)
│   └── {slug}/
│       ├── .memory/               #   Cross-session AI memory
│       ├── concept.md             #   Research concept or library workspace seed
│       ├── references/            #   Local reference library
│       ├── drafts/                #   Markdown drafts (manuscript path)
│       ├── inbox/                 #   Raw notes (library-wiki path)
│       ├── concepts/              #   Atomic concept pages (library-wiki path)
│       ├── projects/              #   Synthesis pages / workstreams (library-wiki path)
│       └── results/               #   Figures, exports
│
├── .agents/skills/                # Codex + OpenClaw repository skills
├── .claude/skills/                # 38 Claude Code / workflow skill definitions
├── .github/prompts/               # 15 Prompt workflow files
├── templates/                     # Journal Word templates
├── memory-bank/                   # Global project memory
└── tests/                         # pytest test suite
```

---

## 🗺️ Roadmap

| Status | Feature                     | Description                                                                          |
| ------ | --------------------------- | ------------------------------------------------------------------------------------ |
| ✅     | **6 managed MCP servers**   | mdpaper (118/12), PubMed (45), CGU (24), Asset-Aware (30), Draw.io (23), Zotero (32) |
| ✅     | **Foam Integration**        | Wikilinks, hover preview, backlinks, named graph views, project isolation            |
| ✅     | **Project Memory**          | `.memory/` for cross-session AI context                                              |
| ✅     | **Table 1 Generator**       | Auto-generate baseline characteristics                                               |
| ✅     | **Novelty Validation**      | 3-round scoring with 75/100 threshold                                                |
| ✅     | **Citation-Aware Editing**  | `patch_draft` with wikilink validation                                               |
| ✅     | **MCP-to-MCP Trust**        | Verified PubMed data via direct HTTP                                                 |
| ✅     | **Pre-commit Hooks**        | 16 hooks (ruff, mypy, bandit, pytest, prettier...)                                   |
| 🔜     | **Richer VSX UX**           | TreeView, CodeLens, Diagnostics, and deeper in-editor surfaces (Direction C)         |
| 🔜     | **Pandoc Export**           | Word + LaTeX dual export with CSL citations                                          |
| 📋     | **Systematic Review**       | PRISMA flow, Risk of Bias, meta-analysis                                             |
| 📋     | **AI Writing Intelligence** | Citation intelligence, coherence engine                                              |
| 📋     | **REST API Mode**           | Expose tools as REST API                                                             |

**Architecture Direction**: [Direction C — Full VSX + Foam + Pandoc](ROADMAP.md)

**Legend:** ✅ Complete | 🔜 In Progress | 📋 Planned

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md), the [Code of Conduct](CODE_OF_CONDUCT.md), and the private vulnerability-reporting process in [SECURITY.md](SECURITY.md).

- 🐛 **Report bugs** — Open an issue
- 💡 **Suggest features** — Share your ideas
- 🔧 **Submit code** — Fork → Branch → PR

---

## 📚 Citation

If you use Medical Paper Assistant, cite the software release described in [`CITATION.cff`](CITATION.cff). A BibTeX example is provided for convenience:

```bibtex
@software{medpaperassistant_2026,
  author  = {{MedPaper Assistant contributors}},
  title   = {Medical Paper Assistant},
  year    = {2026},
  version = {1.0.2},
  url     = {https://github.com/u9401066/med-paper-assistant},
  license = {Apache-2.0}
}
```

Do not cite an unpublished manuscript or invent a DOI. Use the archived release DOI if one is added to `CITATION.cff` in the future.

---

## 📄 License

Apache License 2.0 — See [LICENSE](LICENSE)
