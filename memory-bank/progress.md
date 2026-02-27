# Progress (Updated: 2026-02-27)

## Done

- **v0.3.12 release** — Self-Evolution Infrastructure + Pipeline Flexibility + Deep Review
- Self-Evolution L2 完整：ToolInvocationStore, PendingEvolutionStore, guidance.py, tool_health.py
- Pipeline Flexibility: request_section_rewrite, pause/resume_pipeline, approve_section (4 MCP tools)
- WritingHooksEngine expansion: +1120 lines (A5/A6/B8/C9/F checks)
- MetaLearningEngine: \_flush_meta_learning_evolutions for cross-conversation persistence
- CheckpointManager: section approval, pause/resume, rollback history
- autonomous_audit_loop.py: structured audit loop
- GitHub Actions: evolution-health.yml weekly health check
- tool_logging.py: automatic tool invocation telemetry
- CONSTITUTION v1.6.0: §25-26 核心哲學 — 逐步多輪演進
- AGENTS.md + copilot-instructions.md: 完整重寫，如實標記 Code-Enforced vs Agent-Driven
- Deep code review: 2 rounds — input validation, regex robustness, defensive guards, assert removal
- Tests: 694 passed (42 test files), +163 new tests
- MCP tools: 81 total (review/ from 16→20)

### Previous releases

- v0.3.11: DRY refactor, mypy fixes, 366→402 tests, medRxiv/JAMIA/JBI journals
- v0.3.10: Author Info System, Data Artifact Provenance, Hook F1-F4
- v0.3.9: Multi-Stage Review, 42 Hooks, 11-Phase Pipeline

## Doing

- (none)

## Next

- Run full pipeline with actual project to generate evolution data
- Dashboard integration for evolution reports
- Consider temporal tracking within EvolutionVerifier
- Phase 5c: Full VSX Extension 升級
- Consider grammar checker (language-tool-python as A7)
