# Progress (Updated: 2026-02-23)

## Done

- Token-efficient documentation compression (a2c7f51)
- User-perspective audit: identified README inconsistencies, setup.sh bugs
- Foam alias lifecycle investigation
- G6 consistency audit: fixed 20+ number inconsistencies across README/ARCHITECTURE/setup scripts
- Auto-Paper 11-Phase Pipeline + 閉環自我改進 (SKILL.md rewrite)
- Dual-Hook Architecture (Copilot A-D + Pre-Commit P1-8 + General G1-8 = 38 checks)
- VSX Extension v0.2.0 (388KB, 14 skills, 12 prompts)
- CONSTITUTION v1.3.0 Ch.8 (§20-§23)
- CSL formatter + Pandoc exporter (31/31 tests) — csl_formatter.py, pandoc_exporter.py, templates/csl/
- DraftSnapshotManager + CheckpointManager (28/28 tests) — version control for drafts
- Hook D meta-learning infrastructure (44/44 tests) — hook_effectiveness_tracker, meta_learning_engine, quality_scorecard
- CitationConverter + ExportPipeline + GitAutoCommitter (68/68 tests)
- pandoc_export.py MCP tool — registered in export/__init__.py
- GitAutoCommitter integrated into drafter.py + editing.py
- Windows cp950 encoding bug fixed in git_auto_committer.py
- docs/design/missing-mcp-tools.md — full MCP tool inventory

## Doing

- Memory Bank update + staged Git commits + push

## Next

- Phase 5c: Full VSX Extension upgrade (TreeView, CodeLens, Diagnostics)
- Citation Intelligence MVP
- Fix broken import chain: application/__init__.py → use_cases → missing pubmed/search_literature modules
