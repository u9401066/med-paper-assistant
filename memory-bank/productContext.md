# Project Context

## Goals

- Provide a dual-workflow research workspace: `library-wiki` for exploration / knowledge-base building and `manuscript` for formal drafting / review / export.
- Keep PubMed discovery aligned on `unified_search` as the primary search entrypoint, with `generate_search_queries` and `parse_pico` as strategy helpers.
- Preserve verified reference persistence via `save_reference_mcp`, fulltext / analysis enrichment, and Foam-friendly note materialization.
- Support Library Wiki operations: inbox / concepts / review / daily capture, dashboards, publish-safe wikilink packs, and project-specific graph views.
- Support manuscript operations: concept validation, section drafting, citation-aware editing, asset review gates, and Word / PDF export workflows.
- Keep the packaged VSIX surface and the broader repository authoring surface explicitly documented and authority-checked.
- Provide guided prompt workflows, skills, and chat commands that keep end-user help in sync with the actual runtime surface.

## Project Description

This project is an MCP-orchestrated research workspace for medical writing and literature-centered knowledge work. It integrates with VS Code via MCP and the packaged MedPaper extension to support exploration, reference curation, LLM-wiki materialization, manuscript drafting, review, and export from the same workspace. The core value is not just paper drafting, but keeping search, evidence, notes, and writing surfaces coherent across repo authoring and packaged end-user workflows.
