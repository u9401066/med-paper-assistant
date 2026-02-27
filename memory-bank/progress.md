# Progress (Updated: 2026-02-27)

## Done

- v0.3.11 release (DRY refactor, mypy fixes, 366→402 tests)
- DOCX/PDF export with 3+ authors, medRxiv/JAMIA/JBI journals
- Code review I1 (silent exception) + I2 (deprecated SaveReferenceUseCase) fixed
- structlog migration: 25+ files migrated to structlog==25.5.0
- Full SKILL.md 9-gap audit: 3 new phases + 5 new hooks + scorecard
- WritingHooksEngine (A5/A6/B8/C9/F): implementation + 42 tests
- QualityScorecard DIMENSIONS 6→8 (+equator_compliance, +reproducibility_data_availability)
- MetaLearningEngine EXPECTED_HOOKS updated (40 hooks)
- HookEffectivenessTracker HOOK_CATEGORIES +E/+F (6 categories)
- AGENTS.md + copilot-instructions.md: 52→56 checks
- SKILL.md synced (both copies): Phase 2.5/4.5/9.5 + A5/A6/B8/C9 hooks
- Fix 3 broken tests (DIMENSIONS 6→8) + hardcoded '6' in audit_hooks.py
- EvolutionVerifier: cross-project self-evolution evidence collector + 15 tests
- verify_evolution MCP tool registered in audit_hooks.py
- ARCHITECTURE.md: Self-Evolution section + Hook Architecture + tool count 54→73
- DomainConstraintEngine: Triad-inspired JSON domain constraints + 34 tests
- check_domain_constraints + evolve_constraint MCP tools
- Integration pipeline tests: 32 tests covering all 8 infrastructure classes
- scripts/check_consistency.py: automated consistency checker
- Fix 11 integration test API mismatches
- Fix ruff import sorting (2 files)
- Fix mypy errors: author.py type hint, diagrams.py/project_context.py null checks, template_reader.py style access
- Fix EvolutionVerifier.\_read_project_snapshot: handle list-format meta-learning audit file

## Doing

- Deep code review → fix → git commit (~50 files)

## Next

- Run full pipeline with actual project to generate evolution data
- vscode-extension sync with new MCP tools
- Dashboard integration for evolution reports
- Consider temporal tracking within EvolutionVerifier
