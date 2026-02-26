# Progress (Updated: 2026-02-25)

## Done

- Token-efficient documentation compression (a2c7f51)
- User-perspective audit: identified README inconsistencies, setup.sh bugs
- Foam alias lifecycle investigation
- G6 consistency audit: fixed 20+ number inconsistencies across README/ARCHITECTURE/setup scripts
- Auto-Paper 11-Phase Pipeline + 閉環自我改進 (SKILL.md rewrite)
- Dual-Hook Architecture (Copilot A-D + Pre-Commit P1-8 + General G1-8 = 42 checks)
- VSX Extension v0.3.9 (14 skills, 12 prompts, 1 template)
- CONSTITUTION v1.3.0 Ch.8 (§20-§23)
- CSL formatter + Pandoc exporter (31/31 tests)
- DraftSnapshotManager + CheckpointManager (28/28 tests)
- Hook D meta-learning infrastructure (44/44 tests)
- CitationConverter + ExportPipeline + GitAutoCommitter (68/68 tests)
- pandoc_export.py MCP tool
- GitAutoCommitter integrated into drafter.py + editing.py
- Windows cp950 encoding bug fixed
- Self-referential paper: full 9-phase autonomous execution
- Hook C7-C8 + Hook Propagation Procedure (D3)
- Multi-Stage Review Architecture design doc
- VSX Template Bundling + CI/CD sync
- pytest addopts default exclusion
- v0.3.9 release
- Data Artifact Provenance + DataArtifactTracker (validate_data_artifacts MCP tool)
- CONSTITUTION v1.5.0 §23.2 數據產出物溯源
- Hook F1-F4 data-artifacts (52 checks total)
- Author Info: Author value object + generate_author_block + update_authors MCP tool
- Full project ruff lint cleanup (60→0 errors)
- Version 0.3.10 release preparation
- PDF export fixes: author YAML, date removal, Unicode/emoji handling
- DRY refactor: centralized shared helpers (\_shared/project_context.py)
- Review loop fixes: \_active_loops cache invalidation, Severity enum
- count_words path resolution fix
- Review Loop Round 1 completed (quality 8.87/10)
- validation/concept.py refactored to use shared helpers

## Doing

- (none)

## Next

- Phase 5c: Full VSX Extension upgrade (TreeView, CodeLens, Diagnostics)
- Citation Intelligence MVP
- Fix broken import chain: application/**init**.py
