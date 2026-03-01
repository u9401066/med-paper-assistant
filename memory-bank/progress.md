# Progress (Updated: 2026-02-28)

## Done

- **v0.4.0 (preparing)**:
  - **Dynamic Count Sync Script** (`scripts/sync_repo_counts.py`): AST-based counting of all repo metrics (tools, hooks, skills, prompts, agents, phases), auto-sync into 7 documentation files. `--check` / `--fix` / `--json` modes. 43 stale counts auto-fixed.
  - **ReviewHooksEngine Export**: Added to `persistence/__init__.py` `__all__`
  - **EXPECTED_HOOKS Expansion**: 40→58 hooks (added B9-B16, C10-C13, R1-R6)
  - **HOOK_CATEGORIES**: Added "R": "review-hooks" to tracker
  - **check_consistency.py**: Updated DECLARED_HOOKS (76), UTF-8 encoding, fixed regex
  - **VSX Extension Update**: Hook table (76), skills (26), tools (85), phases (11), package.json description
  - **Pending Evolutions**: 16 items batch dismissed (all same-draft duplicates)
  - Hook count: 65 → **76** (34 Code-Enforced / 42 Agent-Driven)
  - MCP tools: 81 → **85** (accurate AST count)
  - Tests: **698 passed**
- **v0.3.12+ (unreleased)**:
  - **B9-B16 Section-Specific Writing Hooks** (8 new Code-Enforced): Tense consistency (B9), Paragraph quality (B10), Results objectivity (B11), Introduction structure (B12), Discussion structure (B13), Ethical statements (B14), Hedging density (B15), Effect size reporting (B16)
  - **ICMJE Word Count Fix (C6)**: Body-only counting per ICMJE convention
  - **C10-C13 Manuscript Hooks**: Reference fulltext validation (C10), Citation distribution (C11), Citation relevance audit (C12), Figure/table quality (C13)
  - **F1-F4 Data Artifact Hooks**: Data artifact tracking via DataArtifactTracker
  - **R1-R6 Review Hooks**: Review report depth (R1), Author response completeness (R2), EQUATOR compliance (R3), Review-fix traceability (R4), Post-review anti-AI (R5), Citation budget (R6)
  - **A3b AI Structure Signals**: AI writing pattern detection
  - **G9 Git Status**: Pre-commit git state check (Code-Enforced)
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

- Segmented Git commits + tag 0.4.0 + marketplace publish

## Next

- Run full pipeline with actual project to generate evolution data
- Dashboard integration for evolution reports
- Consider grammar checker (language-tool-python as A7)
