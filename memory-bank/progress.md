# Progress (Updated: 2026-02-28)

## Done

- **v0.3.12+ (unreleased)**:
  - **B9-B16 Section-Specific Writing Hooks** (8 new Code-Enforced): Tense consistency (B9), Paragraph quality (B10), Results objectivity (B11), Introduction structure (B12), Discussion structure (B13), Ethical statements (B14), Hedging density (B15), Effect size reporting (B16)
  - **ICMJE Word Count Fix (C6)**: Body-only counting per ICMJE convention — excludes Abstract, References, Tables, Figure legends, Acknowledgments. New helpers: `BODY_SECTIONS`, `_strip_markdown_tables()`, `_extract_body_word_count()`. Journal profile override via `counts_toward_total`.
  - **count_words MCP tool rewrite**: Shows Body? column (✅/—), ICMJE-labeled total
  - Hook count: 56 → **65** (23 Code-Enforced / 42 Agent-Driven)
  - Tests: 694 → **738 passed**
- **v0.3.12 release** — Self-Evolution Infrastructure + Pipeline Flexibility + Deep Review
- Self-Evolution L2 完整：ToolInvocationStore, PendingEvolutionStore, guidance.py, tool_health.py
- Pipeline Flexibility: request_section_rewrite, pause/resume_pipeline, approve_section (4 MCP tools)
- WritingHooksEngine expansion: +2034 lines (A5/A6/B8-B16/C6/C9/F checks)
- MetaLearningEngine: \_flush_meta_learning_evolutions for cross-conversation persistence
- CheckpointManager: section approval, pause/resume, rollback history
- autonomous_audit_loop.py: structured audit loop
- GitHub Actions: evolution-health.yml weekly health check
- tool_logging.py: automatic tool invocation telemetry
- CONSTITUTION v1.6.0: §25-26 核心哲學 — 逐步多輪演進
- AGENTS.md + copilot-instructions.md: 完整重寫，如實標記 Code-Enforced vs Agent-Driven
- Deep code review: 2 rounds — input validation, regex robustness, defensive guards, assert removal
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
