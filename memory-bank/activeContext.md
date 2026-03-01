# Active Context

## User Preferences

- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點 (2026-02-28)

v0.4.0 準備中 — Dynamic count sync script + 全文檔更新 + Hook 架構擴展完成。

### 當前狀態

| 項目                   | 數量/狀態                                          |
| ---------------------- | -------------------------------------------------- |
| MCP Tools              | **85** (project/17, reference/12, draft/13, validation/3, analysis/9, review/21, export/10) |
| Skills                 | **26**                                             |
| Hooks                  | **76 checks** (34 Code-Enforced / 42 Agent-Driven) |
| Prompts                | **15**                                             |
| Agents                 | **9**                                              |
| Infrastructure classes | **8** core                                         |
| Python unit tests      | **698 passed** (excl. external-dep tests)          |
| Ruff errors            | **0**                                              |

### 三層演進架構實作狀態

| 層級                         | 狀態                   | 說明                                                 |
| ---------------------------- | ---------------------- | ---------------------------------------------------- |
| L1 Event-Driven Hooks        | ⚠️ 34/76 Code-Enforced | 42 個 Agent-Driven 僅靠 SKILL.md                     |
| L2 Code-Level Enforcement    | ✅ 完整                | 5 元件全部上線                                       |
| L3 Autonomous Self-Evolution | ⚠️ Phase C 完成        | Git post-commit / EvolutionVerifier / Auto-PR 未實作 |

### 最近變更

- **Dynamic Count Sync Script** (`scripts/sync_repo_counts.py`): AST-based counting, 43 counts auto-fixed across 7 docs
- **ReviewHooksEngine**: R1-R6 hooks, added to persistence/__init__.py exports
- **EXPECTED_HOOKS**: 40→58 (added B9-B16, C10-C13, R1-R6)
- **HOOK_CATEGORIES**: Added "R": "review-hooks"
- **check_consistency.py**: Updated to 76 hooks, UTF-8 encoding, fixed regex
- **VSX Extension**: Hook table, skills (26), tools (85), phases (11) synced
- **Pending Evolutions**: 16 items batch dismissed (all same-draft duplicates)

### 已知問題

- `application/__init__.py` 的 import chain 壞掉（missing pubmed, search_literature modules）— 測試用 sys.modules mock 繞過
- 7 test files skipped due to missing external modules (pubmed_search, citeproc)

## 下一步

- [ ] Segmented Git commits + tag 0.4.0 + marketplace publish
- [ ] Run actual project pipeline to generate evolution data
- [ ] Dashboard integration for evolution reports
- [ ] Consider grammar checker (language-tool-python as A7)

2026-02-28
