# Active Context

## User Preferences

- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點 (2026-02-27)

全部 infrastructure 完成：WritingHooksEngine + EvolutionVerifier + DomainConstraintEngine + 驗證基礎設施。準備深度 code review 後提交。

### v0.3.11→master 變更摘要

| 變更                                           | 狀態             |
| ---------------------------------------------- | ---------------- |
| structlog migration (25+ files)                | ✅               |
| Code review I1/I2 fixes                        | ✅               |
| WritingHooksEngine (A5/A6/B8/C9/F)             | ✅ + 42 tests    |
| EvolutionVerifier (cross-project evidence)     | ✅ + 15 tests    |
| DomainConstraintEngine (Triad-inspired)        | ✅ + 34 tests    |
| Integration pipeline tests                     | ✅ + 32 tests    |
| QualityScorecard 6→8 dimensions                | ✅               |
| SKILL.md Phase 2.5/4.5/9.5 + hooks             | ✅ (both copies) |
| AGENTS.md + copilot-instructions.md 56 checks  | ✅               |
| ARCHITECTURE.md Self-Evolution section         | ✅               |
| verify_evolution + run_writing_hooks MCP tools | ✅               |
| check_domain_constraints + evolve_constraint   | ✅               |
| scripts/check_consistency.py                   | ✅               |
| Fix integration tests (11 API mismatches)      | ✅               |
| Fix ruff import sorting                        | ✅               |
| Fix mypy errors (author.py, diagrams.py, etc.) | ✅               |

### 關鍵數字

- MCP Tools: **79** `@mcp.tool()` decorated functions
- Skills: **26**
- Hooks: **56 checks** (A1-6 + B1-8 + C1-9 + D1-8 + E1-5 + F1-4 + P1-8 + G1-8)
- Infrastructure classes: **8** core
- Python unit tests: **525 passed** (+ 1 skipped)
- Test files: **36**
- Ruff errors: **0**
- Mypy: ✅

### 已知問題

- `application/__init__.py` 的 import chain 壞掉（missing pubmed, search_literature modules）— 測試用 sys.modules mock 繞過

## 下一步

- 深度 code review → 修正 → git commit
- Run full pipeline with actual project to generate evolution data
- vscode-extension sync with new MCP tools
- Dashboard integration for evolution reports

- [ ] Git commit (~43 files: structlog + writing hooks + self-evolution + docs)
- [ ] Run actual project pipeline to generate evolution data
- [ ] Dashboard integration for evolution reports
- [ ] Consider grammar checker (language-tool-python as A7)
- [ ] Phase 5c: Full VSX Extension 升級

## 更新時間

2026-02-26
