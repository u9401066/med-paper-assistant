# Project Context

## Goals
- Develop a suite for assisting in writing medical papers.
- Provide a VSCode-compatible tool/MCP for literature search (usable by Copilot/Antigravity).
- **Advanced Search**: Support customizable search strategies (Date range, Article Type, Sort order).
- **Reference Management**: Save selected literature with metadata and content (abstract/full text) to a local `references/` directory.
- **Draft Generation**: Create draft files in `drafts/` with automatic citation insertion and bibliography generation.
- **Workflow Automation**: Standardized `/mdpaper.draft` workflow to generate drafts from `concept.md` and templates.
- **Data Analysis**: Upload raw data to `data/`, perform statistical analysis, and generate figures/tables in `results/`.
- **Refinement**: `/mdpaper.clarify` workflow to interactively refine specific sections of `concept.md` or drafts.
- **Refinement**: `/mdpaper.clarify` workflow to interactively refine specific sections of `concept.md` or drafts.
- **Template Flexibility**: Support user-uploaded template files for draft generation.
- **Word Export**: `/mdpaper.apply_format` workflow to export drafts and figures to `.docx` using a template.
- Assist in converting ideas into documentation (similar to Speckit).
- Support various journal format templates.
- Generate first drafts with correct citations and formatting.

## Project Description
This project is a Medical Paper Writing Assistant designed to streamline the research and writing process for medical professionals. It integrates with VSCode via MCP (Model Context Protocol) to provide intelligent literature search, formatting, and drafting capabilities. It aims to bridge the gap between raw ideas and submission-ready manuscripts.
