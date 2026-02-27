# Active Context

## User Preferences

- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點 (2026-02-27)

v0.3.12 released — Self-Evolution Infrastructure + Pipeline Flexibility + Deep Review。

### v0.3.12 Release Summary

| 項目                   | 數量/狀態                                          |
| ---------------------- | -------------------------------------------------- |
| MCP Tools              | **81**                                             |
| Skills                 | **26**                                             |
| Hooks                  | **56 checks** (14 Code-Enforced / 42 Agent-Driven) |
| Infrastructure classes | **8** core                                         |
| Python unit tests      | **694 passed** (+ 1 skipped)                       |
| Test files             | **42**                                             |
| Ruff errors            | **0**                                              |
| Mypy                   | ✅                                                 |

### 三層演進架構實作狀態

| 層級                         | 狀態                   | 說明                                                 |
| ---------------------------- | ---------------------- | ---------------------------------------------------- |
| L1 Event-Driven Hooks        | ⚠️ 14/56 Code-Enforced | 42 個 Agent-Driven 僅靠 SKILL.md                     |
| L2 Code-Level Enforcement    | ✅ 完整                | 5 元件全部上線                                       |
| L3 Autonomous Self-Evolution | ⚠️ Phase C 完成        | Git post-commit / EvolutionVerifier / Auto-PR 未實作 |

### 已知問題

- `application/__init__.py` 的 import chain 壞掉（missing pubmed, search_literature modules）— 測試用 sys.modules mock 繞過

## 下一步

- [ ] Run actual project pipeline to generate evolution data
- [ ] Dashboard integration for evolution reports
- [ ] Consider grammar checker (language-tool-python as A7)
- [ ] Phase 5c: Full VSX Extension 升級

## 更新時間

2026-02-27 (v0.3.12 tagged, VSX synced, README updated)
