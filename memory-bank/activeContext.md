# Active Context

## User Preferences

- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點 (2026-02-27)

深度 code review 完成，所有 CRITICAL/HIGH 修正已提交。

### 最近提交

- `db5ea87` feat: self-evolution infrastructure + writing hooks + domain constraints (54 files, +5292/-318)
- 本次: fix: code review findings — input validation, regex robustness, safety guards

### Code Review 修正摘要

| 修正                                              | 嚴重度   | 檔案                          |
| ------------------------------------------------- | -------- | ----------------------------- |
| hook_id format validation                         | CRITICAL | audit_hooks.py                |
| Anti-AI word boundary regex                       | CRITICAL | domain_constraint_engine.py   |
| constraint_id + severity input validation         | CRITICAL | domain_constraint_engine.py   |
| params null guard (`or {}`)                       | CRITICAL | domain_constraint_engine.py   |
| Supplementary file matching (word boundary regex) | HIGH     | writing_hooks.py              |
| Supplementary dir traversal (`rglob`)             | HIGH     | writing_hooks.py              |
| Dict inverse mapping assertion                    | HIGH     | writing_hooks.py              |
| R software regex more specific                    | HIGH     | writing_hooks.py              |
| Code block state tracking + wikilink stripping    | HIGH     | writing_hooks.py              |
| Duplicate run_id guard                            | MEDIUM   | hook_effectiveness_tracker.py |
| Required sections heading regex                   | MEDIUM   | domain_constraint_engine.py   |

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

- Run full pipeline with actual project to generate evolution data
- vscode-extension sync with new MCP tools
- Dashboard integration for evolution reports

- [ ] Run actual project pipeline to generate evolution data
- [ ] Dashboard integration for evolution reports
- [ ] Consider grammar checker (language-tool-python as A7)
- [ ] Phase 5c: Full VSX Extension 升級

## 更新時間

2026-02-27
