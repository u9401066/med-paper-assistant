# Changelog

## 0.6.9 - 2026-04-21

- Added full-surface agent wiki stage 2 orchestration: `ingest_web_source`, `ingest_markdown_source`, `build_knowledge_map`, `build_synthesis_page`, and `materialize_agent_wiki`.
- Extended canonical reference persistence so markdown/web intake, knowledge maps, synthesis pages, and `notes/index.md` all flow through the same durable writer.
- Updated packaged instructions and VSIX README counts to reflect the current `101 full / 44 compact` MCP surface.

## 0.6.8 - 2026-04-20

- Synced the bundled MedPaper Python package to include the latest reference persistence and MCP registration changes.
- Added the `mdpaper.toolSurface` VS Code setting so packaged VSIX installs can switch from the default compact surface to the full surface when advanced wiki/reference orchestration tools are needed.
- Updated bundled instructions and help prompt counts to reflect the current `96 full / 44 compact` MCP surface.
- Documented the local import -> canonical identity resolution workflow for agent wiki materialization in the VSIX README.
- Tightened reference identity resolution so stale DOI registry entries are cleaned up, merged artifact conflicts are preserved instead of overwritten, and the final knowledge-base index is rebuilt once at the correct point.