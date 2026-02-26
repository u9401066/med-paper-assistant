# Active Context

## User Preferences

- **Git Identity**: u9401066 <u9401066@gap.kmu.edu.tw>

## 當前焦點 (2026-02-26)

DRY 重構完成 + PDF 修復 + Review Loop Round 1 通過。準備提交。

### v0.3.10 變更摘要

| 變更                                           | 狀態           |
| ---------------------------------------------- | -------------- |
| Data Artifact Provenance (DataArtifactTracker) | ✅             |
| Author Info (Author VO + MCP tools)            | ✅             |
| CONSTITUTION v1.5.0 §23.2                      | ✅             |
| Hook F1-F4 data-artifacts                      | ✅ (52 checks) |
| Full project ruff lint cleanup (60→0)          | ✅             |
| Version 0.3.10                                 | ✅             |

### 關鍵數字

- MCP Tools: **56+** (+2: update_authors, validate_data_artifacts)
- Skills: **26**
- Hooks: **52 checks** (A1-4 + B1-7 + C1-8 + D1-8 + E1-5 + F1-4 + P1-8 + G1-8)
- Python unit tests: **366 passed** (integration tests excluded by default)
- Ruff errors: **0**

### 已知問題

- `application/__init__.py` 的 import chain 壞掉（missing pubmed, search_literature modules）— 測試用 sys.modules mock 繞過

## 下一步

- [ ] Git commit (refactor + fixes + review loop)
- [ ] Phase 5c: Full VSX Extension 升級
- [ ] Citation Intelligence MVP

## 更新時間

2026-02-26
